from datetime import datetime
import secrets
import os

from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import requests
from app.extensions import db
from app.models import LearningStyle, PracticeActivity, RewardWallet, User, UserProfile, UserRoleOverride, UserStreak, WeeklyQuizAttempt
from app.services.admin_auth import get_role_for_email, is_admin_email
from app.services.progression_content_service import ensure_daily_and_weekly_progression
from app.services.user_cleanup import delete_user_with_related_data


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/google/callback").strip()


def _google_client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "").strip()


def _google_client_secret() -> str:
    return os.getenv("GOOGLE_CLIENT_SECRET", "").strip()


def _google_config() -> dict:
    return {
        "client_id": _google_client_id(),
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "auth_url": GOOGLE_AUTH_URL,
    }


def _ensure_wallet(user_id: int) -> RewardWallet:
    wallet = db.session.get(RewardWallet, user_id)
    if not wallet:
        wallet = RewardWallet(user_id=user_id, current_xp=0, level=1, reward_points=0)
        db.session.add(wallet)
    return wallet


def _ensure_streak(user_id: int) -> UserStreak:
    streak = db.session.get(UserStreak, user_id)
    if not streak:
        streak = UserStreak(user_id=user_id, current_streak=0, longest_streak=0, last_active_date=None)
        db.session.add(streak)
    return streak


def _ensure_profile(user_id: int) -> UserProfile:
    profile = db.session.get(UserProfile, user_id)
    if not profile:
        profile = UserProfile(
            user_id=user_id,
            difficulty_level="beginner",
            topic_mastery_json={},
            preferred_languages=[],
        )
        db.session.add(profile)
    return profile


def _sync_progression_if_ready(user_id: int, profile: UserProfile) -> None:
    preferred_languages = profile.preferred_languages if isinstance(profile.preferred_languages, list) else []
    if preferred_languages:
        ensure_daily_and_weekly_progression(user_id, profile, datetime.utcnow().date())


def _progress_summary(user_id: int) -> dict:
    wallet = _ensure_wallet(user_id)
    streak = _ensure_streak(user_id)
    profile = db.session.get(UserProfile, user_id)
    style = db.session.get(LearningStyle, user_id)

    attempts = WeeklyQuizAttempt.query.filter_by(user_id=user_id).all()
    practice_rows = PracticeActivity.query.filter_by(user_id=user_id).all()
    completed_practice = [row for row in practice_rows if (row.status or "").lower() == "completed"]

    quiz_accuracy = 0.0
    if attempts:
        quiz_accuracy = sum(float(row.percentage or 0) for row in attempts) / len(attempts)
    practice_accuracy = 0.0
    if practice_rows:
        practice_accuracy = (len(completed_practice) / len(practice_rows)) * 100

    accuracy = round(min(100.0, max(quiz_accuracy, practice_accuracy)), 2)
    onboarded = False
    if profile and profile.onboarding_completed_at:
        onboarded = True
    elif profile and style and isinstance(profile.preferred_languages, list) and profile.preferred_languages:
        onboarded = True

    preferred_language = None
    learning_style = None
    weak_topics = []
    learning_level = "beginner"
    phone_number = None
    other_details = None
    if profile:
        learning_level = profile.difficulty_level or "beginner"
        preferred_languages = profile.preferred_languages or []
        if isinstance(preferred_languages, list) and preferred_languages:
            preferred_language = preferred_languages[0]
        mastery = profile.topic_mastery_json or {}
        raw_topics = mastery.get("weak_topics") if isinstance(mastery, dict) else None
        if isinstance(raw_topics, list):
            weak_topics = [str(item) for item in raw_topics if str(item).strip()][:12]
        phone_number = profile.phone_number
        other_details = profile.other_details_json
    if style:
        learning_style = style.learning_style

    return {
        "xp": wallet.current_xp,
        "level": wallet.level,
        "reward_points": wallet.reward_points,
        "streak": streak.current_streak,
        "accuracy": accuracy,
        "onboarded": onboarded,
        "learningLevel": learning_level.capitalize() if learning_level else "Beginner",
        "learningStyle": learning_style,
        "preferredLanguage": preferred_language,
        "weakTopics": weak_topics,
        "phoneNumber": phone_number,
        "otherDetails": other_details,
    }


def _serialize_user(user: User) -> dict:
    summary = _progress_summary(user.user_id)
    return {
        "id": str(user.user_id),
        "email": user.email,
        "displayName": user.name,
        "avatar": None,
        "role": get_role_for_email(user.email),
        "xp": summary["xp"],
        "level": summary["level"],
        "streak": summary["streak"],
        "accuracy": summary["accuracy"],
        "learningLevel": summary["learningLevel"],
        "learningStyle": summary["learningStyle"],
        "preferredLanguage": summary["preferredLanguage"],
        "weakTopics": summary["weakTopics"],
        "phoneNumber": summary["phoneNumber"],
        "otherDetails": summary["otherDetails"],
        "onboarded": summary["onboarded"],
    }


def _touch_profile(user_id: int, data: dict) -> None:
    profile = _ensure_profile(user_id)

    if "learning_level" in data:
        learning_level = str(data.get("learning_level", "")).strip().lower()
        if learning_level:
            profile.difficulty_level = learning_level

    if "preferred_language" in data:
        preferred_language = str(data.get("preferred_language", "")).strip()
        if preferred_language:
            profile.preferred_languages = [preferred_language]

    weight_fields = ("visual_weight", "auditory_weight", "kinesthetic_weight")
    if any(field in data for field in weight_fields):
        for field in weight_fields:
            if field in data:
                try:
                    setattr(profile, field, float(data.get(field, getattr(profile, field))))
                except (TypeError, ValueError):
                    pass

    if "weak_topics" in data:
        weak_topics = data.get("weak_topics", [])
        if isinstance(weak_topics, list):
            clean_topics = [str(item).strip() for item in weak_topics if str(item).strip()]
            profile.topic_mastery_json = {"weak_topics": clean_topics}

    if "phone_number" in data:
        phone_number = str(data.get("phone_number", "")).strip()
        profile.phone_number = phone_number or None

    if "other_details" in data:
        other_details = data.get("other_details")
        if isinstance(other_details, dict):
            profile.other_details_json = other_details
        elif isinstance(other_details, str):
            cleaned = other_details.strip()
            profile.other_details_json = {"notes": cleaned} if cleaned else {}
    if "other_details_json" in data and isinstance(data.get("other_details_json"), dict):
        profile.other_details_json = data.get("other_details_json")

    db.session.commit()


def _issue_token(user: User) -> str:
    return create_access_token(identity=str(user.user_id))


def _find_or_create_user(email: str, name: str, password: str | None) -> User:
    user = User.query.filter_by(email=email).first()
    if not user:
        if password is None:
            password = secrets.token_urlsafe(32)
        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.flush()
        _ensure_wallet(user.user_id)
        _ensure_streak(user.user_id)
        _ensure_profile(user.user_id)
        db.session.commit()
        return user
    return user


def _ensure_admin_override(user: User, reason: str) -> None:
    override = db.session.get(UserRoleOverride, user.user_id)
    if not override:
        override = UserRoleOverride(
            user_id=user.user_id,
            role="admin",
            reason=reason,
            updated_by=None,
        )
        db.session.add(override)
    else:
        override.role = "admin"
        override.reason = reason
        override.updated_by = None


@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    name = str(data.get("display_name", "")).strip() or str(data.get("name", "")).strip() or "Learner"

    if not email:
        return jsonify({"error": "email is required"}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "password must be at least 6 characters"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already exists"}), 409

    user = _find_or_create_user(email=email, name=name, password=password)
    profile = _ensure_profile(user.user_id)
    db.session.commit()
    token = _issue_token(user)
    return jsonify({"access_token": token, "user": _serialize_user(user)})


@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    profile = _ensure_profile(user_id)
    _sync_progression_if_ready(user_id, profile)
    db.session.commit()

    payload = _serialize_user(user)
    payload["user_id"] = user.user_id
    payload["name"] = user.name
    payload["is_admin"] = is_admin_email(user.email)
    return jsonify(payload)


@auth_bp.get("/google/config")
def google_config():
    config = _google_config()
    if not config["client_id"]:
        return jsonify({"error": "google oauth is not configured"}), 503
    return jsonify(config)


def _login_with_password(email: str, password: str):
    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "invalid credentials"}), 401

    token = _issue_token(user)
    return jsonify({"access_token": token, "user": _serialize_user(user)})


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    return _login_with_password(email, password)


@auth_bp.post("/login-user")
def login_user():
    data = request.get_json() or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    return _login_with_password(email, password)


@auth_bp.post("/login-admin")
def login_admin():
    data = request.get_json() or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    return _login_with_password(email, password)


@auth_bp.post("/dev-login-admin")
def dev_login_admin():
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env == "production":
        return jsonify({"error": "dev admin login is disabled in production"}), 403

    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or os.getenv("DEV_ADMIN_EMAIL") or "nravikant123@gmail.com").strip().lower()
    name = str(data.get("display_name") or "Admin").strip() or "Admin"

    if not email:
        return jsonify({"error": "email is required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(secrets.token_urlsafe(32)),
        )
        db.session.add(user)
        db.session.flush()
        _ensure_wallet(user.user_id)
        _ensure_streak(user.user_id)
        _ensure_profile(user.user_id)
    elif name and user.name != name:
        user.name = name

    _ensure_admin_override(user, "local development admin login")
    profile = _ensure_profile(user.user_id)
    db.session.commit()

    token = _issue_token(user)
    return jsonify({"access_token": token, "user": _serialize_user(user)})


@auth_bp.post("/google/exchange")
def google_exchange():
    data = request.get_json(silent=True) or {}
    code = str(data.get("code", "")).strip()
    redirect_uri = str(data.get("redirect_uri", "")).strip() or GOOGLE_REDIRECT_URI

    if not code:
        return jsonify({"error": "code is required"}), 400

    config = _google_config()
    if not config["client_id"] or not _google_client_secret():
        return jsonify({"error": "google oauth is not configured"}), 503

    if redirect_uri != config["redirect_uri"]:
        return jsonify({"error": "redirect_uri mismatch"}), 400

    token_response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": config["client_id"],
            "client_secret": _google_client_secret(),
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=20,
    )
    if token_response.status_code != 200:
        return jsonify({"error": "google token exchange failed"}), 400

    token_payload = token_response.json() or {}
    id_token = str(token_payload.get("id_token", "")).strip()
    if not id_token:
        return jsonify({"error": "google id_token missing"}), 400

    info_response = requests.get(GOOGLE_TOKENINFO_URL, params={"id_token": id_token}, timeout=20)
    if info_response.status_code != 200:
        return jsonify({"error": "google token verification failed"}), 400

    profile = info_response.json() or {}
    email = str(profile.get("email", "")).strip().lower()
    name = str(profile.get("name", "")).strip() or profile.get("given_name") or "Learner"
    audience = str(profile.get("aud", "")).strip()
    if not email:
        return jsonify({"error": "google email missing"}), 400
    if audience and audience != config["client_id"]:
        return jsonify({"error": "google audience mismatch"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(secrets.token_urlsafe(32)),
        )
        db.session.add(user)
        db.session.flush()
        _ensure_wallet(user.user_id)
        _ensure_streak(user.user_id)
        _ensure_profile(user.user_id)
    elif name and user.name != name:
        user.name = name

    db.session.commit()
    token = _issue_token(user)
    return jsonify({"access_token": token, "user": _serialize_user(user)})


@auth_bp.put("/me")
@jwt_required()
def update_me():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    data = request.get_json() or {}
    if "name" in data:
        name = str(data.get("name", "")).strip()
        if not name:
            return jsonify({"error": "name cannot be empty"}), 400
        user.name = name

    if "email" in data:
        email = str(data.get("email", "")).strip().lower()
        if not email:
            return jsonify({"error": "email cannot be empty"}), 400
        existing = User.query.filter(User.email == email, User.user_id != user_id).first()
        if existing:
            return jsonify({"error": "email already exists"}), 409
        user.email = email

    if "password" in data:
        password = str(data.get("password", ""))
        if len(password) < 6:
            return jsonify({"error": "password must be at least 6 characters"}), 400
        user.password_hash = generate_password_hash(password)

    profile_updates = {}
    for field in (
        "learning_level",
        "preferred_language",
        "visual_weight",
        "auditory_weight",
        "kinesthetic_weight",
        "weak_topics",
        "phone_number",
        "other_details",
        "other_details_json",
    ):
        if field in data:
            profile_updates[field] = data[field]
    if profile_updates:
        _touch_profile(user_id, profile_updates)
        profile = _ensure_profile(user_id)
        _sync_progression_if_ready(user_id, profile)

    db.session.commit()
    return jsonify(
        {
            "message": "profile updated",
            "user": _serialize_user(user),
        }
    )


@auth_bp.post("/onboarding/complete")
@jwt_required()
def complete_onboarding():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    data = request.get_json() or {}
    name = str(data.get("name", user.name)).strip()
    email = str(data.get("email", user.email)).strip().lower()
    if not name:
        return jsonify({"error": "name is required"}), 400
    if not email:
        return jsonify({"error": "email is required"}), 400

    existing = User.query.filter(User.email == email, User.user_id != user_id).first()
    if existing:
        return jsonify({"error": "email already exists"}), 409
    user.name = name
    user.email = email

    profile = _ensure_profile(user_id)
    language = str(data.get("preferred_language", "")).strip()
    if not language:
        return jsonify({"error": "preferred_language is required"}), 400

    profile_updates = {
        "preferred_language": data.get("preferred_language"),
        "phone_number": data.get("phone_number"),
        "other_details": data.get("other_details"),
        "visual_weight": data.get("visual_weight"),
        "auditory_weight": data.get("auditory_weight"),
        "kinesthetic_weight": data.get("kinesthetic_weight"),
    }
    _touch_profile(user_id, profile_updates)

    profile.preferred_languages = [language]

    profile.onboarding_completed_at = datetime.utcnow()
    if not profile.difficulty_level:
        profile.difficulty_level = "beginner"

    _sync_progression_if_ready(user_id, profile)
    db.session.commit()
    return jsonify({"message": "onboarding completed", "user": _serialize_user(user)})


@auth_bp.post("/logout")
@jwt_required()
def logout():
    return jsonify({"message": "logout successful on client token removal"})


@auth_bp.delete("/me")
@jwt_required()
def delete_me():
    user_id = int(get_jwt_identity())
    deleted = delete_user_with_related_data(user_id)
    if not deleted:
        return jsonify({"error": "user not found"}), 404
    return jsonify({"message": "account deleted"})


@auth_bp.post("/forgot-password")
def forgot_password():
    return jsonify({"error": "password reset moved to Clerk."}), 410


@auth_bp.post("/reset-password")
def reset_password():
    return jsonify({"error": "password reset moved to Clerk."}), 410
