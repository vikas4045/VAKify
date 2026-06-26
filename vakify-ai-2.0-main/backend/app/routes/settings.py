from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import UserSettings


settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")


def _ensure_settings(user_id: int) -> UserSettings:
    row = db.session.get(UserSettings, user_id)
    if not row:
        row = UserSettings(
            user_id=user_id,
            theme="light",
            language="en",
            notifications_json={
                "daily_tasks": True,
                "weekly_quiz": True,
                "achievements": True,
                "streak_alerts": True,
            },
        )
        db.session.add(row)
    return row


@settings_bp.get("/me")
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    row = _ensure_settings(user_id)
    db.session.commit()
    return jsonify(
        {
            "theme": row.theme,
            "language": row.language,
            "notifications": row.notifications_json or {},
        }
    )


@settings_bp.put("/me")
@jwt_required()
def update_me():
    user_id = int(get_jwt_identity())
    row = _ensure_settings(user_id)
    payload = request.get_json() or {}

    if "theme" in payload:
        theme = str(payload.get("theme", "")).strip().lower()
        if theme in {"light", "dark", "system"}:
            row.theme = theme

    if "language" in payload:
        language = str(payload.get("language", "")).strip()
        if language:
            row.language = language

    if "notifications" in payload and isinstance(payload.get("notifications"), dict):
        row.notifications_json = payload.get("notifications")

    db.session.commit()
    return jsonify(
        {
            "message": "settings saved",
            "theme": row.theme,
            "language": row.language,
            "notifications": row.notifications_json or {},
        }
    )
