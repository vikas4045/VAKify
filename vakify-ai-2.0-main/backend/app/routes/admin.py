from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from app.extensions import db
from app.models import (
    ChatFeedback,
    ChatHistory,
    Download,
    LearningStyle,
    PracticeActivity,
    RewardWallet,
    User,
    UserRoleOverride,
    XPEvent,
)
from app.services.admin_auth import get_role_for_email, is_admin_email
from app.services.admin_workspace import (
    get_chatbot_config,
    leaderboard_management_payload,
    rebuild_leaderboard_snapshots,
    serialize_chatbot_config,
    update_chatbot_config,
)
from app.services.user_cleanup import delete_user_with_related_data


admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _require_admin():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return None, (jsonify({"error": "user not found"}), 404)
    if get_role_for_email(user.email) != "admin":
        return None, (jsonify({"error": "admin access required"}), 403)
    return user, None


@admin_bp.get("/summary")
@jwt_required()
def summary():
    _, err = _require_admin()
    if err:
        return err

    users_count = db.session.query(func.count(User.user_id)).scalar() or 0
    style_count = db.session.query(func.count(LearningStyle.user_id)).scalar() or 0
    chats_count = db.session.query(func.count(ChatHistory.chat_id)).scalar() or 0
    practice_count = db.session.query(func.count(PracticeActivity.activity_id)).scalar() or 0
    downloads_count = db.session.query(func.count(Download.download_id)).scalar() or 0

    latest_users = (
        User.query.order_by(User.created_at.desc()).limit(8).all()
    )
    latest_chats = (
        ChatHistory.query.order_by(ChatHistory.timestamp.desc()).limit(8).all()
    )
    return jsonify(
        {
            "metrics": {
                "users": users_count,
                "learning_styles": style_count,
                "chat_messages": chats_count,
                "practice_submissions": practice_count,
                "downloads": downloads_count,
            },
            "latest_users": [
                {
                    "user_id": u.user_id,
                    "name": u.name,
                    "email": u.email,
                    "created_at": u.created_at.isoformat(),
                    "is_admin": is_admin_email(u.email),
                }
                for u in latest_users
            ],
            "latest_chats": [
                {
                    "chat_id": c.chat_id,
                    "user_id": c.user_id,
                    "question": c.question,
                    "response_type": c.response_type,
                    "timestamp": c.timestamp.isoformat(),
                }
                for c in latest_chats
            ],
        }
    )


@admin_bp.get("/users")
@jwt_required()
def users():
    _, err = _require_admin()
    if err:
        return err

    query = User.query
    q = (request.args.get("q") or "").strip().lower()
    if q:
        pattern = f"%{q}%"
        query = query.filter((User.name.ilike(pattern)) | (User.email.ilike(pattern)))

    rows = query.order_by(User.created_at.desc()).limit(200).all()
    result = []
    for u in rows:
        style = LearningStyle.query.get(u.user_id)
        chats = db.session.query(func.count(ChatHistory.chat_id)).filter(ChatHistory.user_id == u.user_id).scalar() or 0
        downloads = db.session.query(func.count(Download.download_id)).filter(Download.user_id == u.user_id).scalar() or 0
        practice = db.session.query(func.count(PracticeActivity.activity_id)).filter(PracticeActivity.user_id == u.user_id).scalar() or 0
        result.append(
            {
                "user_id": u.user_id,
                "name": u.name,
                "email": u.email,
                "role": get_role_for_email(u.email),
                "is_admin": is_admin_email(u.email),
                "learning_style": style.learning_style if style else None,
                "created_at": u.created_at.isoformat(),
                "stats": {
                    "chats": chats,
                    "downloads": downloads,
                    "practice": practice,
                },
            }
        )
    return jsonify(result)


@admin_bp.put("/users/<int:user_id>/role")
@jwt_required()
def update_role(user_id: int):
    admin_user, err = _require_admin()
    if err:
        return err
    if admin_user.user_id == user_id:
        return jsonify({"error": "cannot change your own admin role"}), 400

    target = User.query.get(user_id)
    if not target:
        return jsonify({"error": "user not found"}), 404

    payload = request.get_json() or {}
    role = str(payload.get("role", "")).strip().lower()
    if role not in {"learner", "moderator", "admin"}:
        return jsonify({"error": "role must be learner, moderator, or admin"}), 400

    reason = str(payload.get("reason", "")).strip() or None
    override = db.session.get(UserRoleOverride, user_id)
    if not override:
        override = UserRoleOverride(user_id=user_id, role=role, reason=reason, updated_by=admin_user.user_id)
        db.session.add(override)
    else:
        override.role = role
        override.reason = reason
        override.updated_by = admin_user.user_id
    db.session.commit()

    return jsonify(
        {
            "message": "role updated",
            "user_id": user_id,
            "role": role,
            "reason": reason,
        }
    )


@admin_bp.post("/users/<int:user_id>/grant-points")
@jwt_required()
def grant_points(user_id: int):
    admin_user, err = _require_admin()
    if err:
        return err

    target = User.query.get(user_id)
    if not target:
        return jsonify({"error": "user not found"}), 404

    payload = request.get_json() or {}
    points = int(payload.get("points", 0))
    if points <= 0:
        return jsonify({"error": "points must be greater than zero"}), 400

    reason = str(payload.get("reason", "")).strip() or "admin grant"
    wallet = db.session.get(RewardWallet, user_id)
    if not wallet:
        wallet = RewardWallet(user_id=user_id, current_xp=0, level=1, reward_points=0)
        db.session.add(wallet)
        db.session.flush()

    wallet.current_xp += points
    wallet.reward_points += points
    wallet.level = max(1, (wallet.current_xp // 200) + 1)
    db.session.add(
        XPEvent(
            user_id=user_id,
            source="admin_grant",
            source_id=admin_user.user_id,
            points=points,
            meta={"reason": reason, "granted_by": admin_user.email},
        )
    )
    db.session.commit()

    return jsonify(
        {
            "message": "points granted",
            "user_id": user_id,
            "points": points,
            "reason": reason,
        }
    )


@admin_bp.delete("/users/<int:user_id>")
@jwt_required()
def delete_user(user_id: int):
    admin_user, err = _require_admin()
    if err:
        return err
    if admin_user.user_id == user_id:
        return jsonify({"error": "cannot delete own admin account"}), 400

    target = User.query.get(user_id)
    if not target:
        return jsonify({"error": "user not found"}), 404

    delete_user_with_related_data(user_id)
    return jsonify({"message": "user deleted", "user_id": user_id})


@admin_bp.get("/analytics")
@jwt_required()
def analytics():
    _, err = _require_admin()
    if err:
        return err

    # style distribution
    style_rows = (
        db.session.query(LearningStyle.learning_style, func.count(LearningStyle.user_id))
        .group_by(LearningStyle.learning_style)
        .all()
    )
    style_dist = {row[0]: row[1] for row in style_rows}

    # last 7-day trends
    today = datetime.utcnow().date()
    labels = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    signup_map = {k: 0 for k in labels}
    chat_map = {k: 0 for k in labels}
    feedback_map = {k: 0 for k in labels}

    for row in User.query.filter(User.created_at >= datetime.utcnow() - timedelta(days=7)).all():
        key = row.created_at.strftime("%Y-%m-%d")
        if key in signup_map:
            signup_map[key] += 1
    for row in ChatHistory.query.filter(ChatHistory.timestamp >= datetime.utcnow() - timedelta(days=7)).all():
        key = row.timestamp.strftime("%Y-%m-%d")
        if key in chat_map:
            chat_map[key] += 1
    for row in ChatFeedback.query.filter(ChatFeedback.created_at >= datetime.utcnow() - timedelta(days=7)).all():
        key = row.created_at.strftime("%Y-%m-%d")
        if key in feedback_map:
            feedback_map[key] += 1

    feedback_total = db.session.query(func.count(ChatFeedback.feedback_id)).scalar() or 0
    helpful = db.session.query(func.count(ChatFeedback.feedback_id)).filter(ChatFeedback.rating == 1).scalar() or 0
    needs_work = db.session.query(func.count(ChatFeedback.feedback_id)).filter(ChatFeedback.rating == -1).scalar() or 0
    avg_rating = 0
    if feedback_total:
        avg_rating = round(((helpful - needs_work) / feedback_total), 2)

    return jsonify(
        {
            "style_distribution": style_dist,
            "daily_signups": [{"date": d, "count": signup_map[d]} for d in labels],
            "daily_chats": [{"date": d, "count": chat_map[d]} for d in labels],
            "daily_feedback": [{"date": d, "count": feedback_map[d]} for d in labels],
            "feedback_summary": {
                "total": feedback_total,
                "helpful": helpful,
                "needs_work": needs_work,
                "avg_rating": avg_rating,
            },
        }
    )


@admin_bp.get("/chatbot-config")
@jwt_required()
def chatbot_config():
    _, err = _require_admin()
    if err:
        return err

    config = get_chatbot_config()
    return jsonify(serialize_chatbot_config(config))


@admin_bp.put("/chatbot-config")
@jwt_required()
def update_chatbot_config_route():
    admin_user, err = _require_admin()
    if err:
        return err

    payload = request.get_json() or {}
    config = update_chatbot_config(payload, updated_by=admin_user.user_id)
    return jsonify(
        {
            "message": "chatbot config updated",
            "config": serialize_chatbot_config(config),
        }
    )


@admin_bp.get("/leaderboard")
@jwt_required()
def leaderboard_management():
    _, err = _require_admin()
    if err:
        return err

    return jsonify(leaderboard_management_payload())


@admin_bp.post("/leaderboard/refresh")
@jwt_required()
def refresh_leaderboard():
    _, err = _require_admin()
    if err:
        return err

    leaderboard = rebuild_leaderboard_snapshots()
    return jsonify({"message": "leaderboard refreshed", "leaderboard": leaderboard})
