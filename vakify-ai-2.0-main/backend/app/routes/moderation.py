from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import ChatFeedback, ChatHistory, ModerationItem, User
from app.services.admin_auth import get_role_for_email


moderation_bp = Blueprint("moderation", __name__, url_prefix="/api/moderation")


def _require_moderator():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return None, (jsonify({"error": "user not found"}), 404)
    if get_role_for_email(user.email) not in {"admin", "moderator"}:
        return None, (jsonify({"error": "moderator access required"}), 403)
    return user, None


def _seed_moderation_items() -> None:
    flagged_feedback = ChatFeedback.query.filter(ChatFeedback.rating == -1).all()
    for feedback in flagged_feedback:
        chat = ChatHistory.query.filter_by(chat_id=feedback.chat_id, user_id=feedback.user_id).first()
        content = feedback.comment or (chat.response if chat else "")
        reason = "Negative feedback"
        existing = ModerationItem.query.filter_by(item_type="feedback", source_id=feedback.chat_id, user_id=feedback.user_id).first()
        if existing:
            if existing.content != content:
                existing.content = content
            continue
        db.session.add(
            ModerationItem(
                item_type="feedback",
                source_id=feedback.chat_id,
                user_id=feedback.user_id,
                content=content or "User requested a review of this response.",
                reason=reason,
                confidence="Medium",
                status="pending",
            )
        )
    db.session.commit()


@moderation_bp.get("/queue")
@jwt_required()
def queue():
    _, err = _require_moderator()
    if err:
        return err

    _seed_moderation_items()
    rows = ModerationItem.query.order_by(ModerationItem.status.asc(), ModerationItem.created_at.desc()).all()
    return jsonify(
        {
            "items": [
                {
                    "moderation_id": row.moderation_id,
                    "item_type": row.item_type,
                    "source_id": row.source_id,
                    "user_id": row.user_id,
                    "content": row.content,
                    "reason": row.reason,
                    "confidence": row.confidence,
                    "status": row.status,
                    "reviewed_by": row.reviewed_by,
                    "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
        }
    )


@moderation_bp.post("/items/<int:moderation_id>/resolve")
@jwt_required()
def resolve_item(moderation_id: int):
    moderator, err = _require_moderator()
    if err:
        return err

    payload = request.get_json() or {}
    action = str(payload.get("action", "")).strip().lower()
    if action not in {"approve", "reject"}:
        return jsonify({"error": "action must be approve or reject"}), 400

    row = ModerationItem.query.get(moderation_id)
    if not row:
        return jsonify({"error": "moderation item not found"}), 404

    row.status = "reviewed" if action == "approve" else "rejected"
    row.reviewed_by = moderator.user_id
    row.reviewed_at = datetime.utcnow()
    db.session.commit()

    return jsonify(
        {
            "message": "moderation item updated",
            "moderation_id": row.moderation_id,
            "status": row.status,
        }
    )
