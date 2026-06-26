import json
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db
from app.models import (
    LearningStyle,
    ChatHistory,
    ChatThread,
    ChatThreadMessage,
    Download,
    ChatFeedback,
    CodeLabTask,
    LabWorkspaceState,
    ModerationItem,
    UserProfile,
)
from app.services.chatbot_service import generate_chat_response, get_quick_prompts
from app.services.download_service import create_download_file
from app.services.practice_task_service import generate_practice_tasks_from_topic
from app.services.openai_service import generate_image_data_url


chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


def _truncate(text: str, limit: int) -> str:
    return (text or "").strip()[:limit]


def _topic_title(question: str) -> str:
    clean = _truncate(question.replace("\n", " "), 80)
    return clean if len(clean) <= 60 else clean[:57].rstrip() + "..."


def _latest_thread_for_user(user_id: int) -> ChatThread | None:
    return (
        ChatThread.query.filter_by(user_id=user_id, is_archived=False)
        .order_by(ChatThread.last_message_at.desc().nullslast(), ChatThread.created_at.desc())
        .first()
    )


def _resolve_thread(user_id: int, thread_id: int | None, title_hint: str | None = None, create_if_missing: bool = True) -> ChatThread | None:
    if thread_id is not None:
        thread = ChatThread.query.filter_by(thread_id=thread_id, user_id=user_id).first()
        if thread:
            return thread
        return None

    thread = _latest_thread_for_user(user_id)
    if thread:
        return thread
    if not create_if_missing:
        return None

    thread = ChatThread(user_id=user_id, title=title_hint or "New Chat")
    db.session.add(thread)
    db.session.flush()
    return thread


def _thread_payload(thread: ChatThread) -> dict:
    return {
        "thread_id": thread.thread_id,
        "title": thread.title,
        "preview": thread.preview,
        "message_count": thread.message_count,
        "is_archived": thread.is_archived,
        "last_message_at": thread.last_message_at.isoformat() if thread.last_message_at else None,
        "created_at": thread.created_at.isoformat(),
        "updated_at": thread.updated_at.isoformat(),
    }


def _thread_history(thread_id: int, user_id: int, limit: int = 30) -> list[ChatHistory]:
    linked_ids = [
        row.chat_id
        for row in (
            ChatThreadMessage.query.filter_by(thread_id=thread_id, user_id=user_id)
            .order_by(ChatThreadMessage.created_at.desc())
            .limit(limit)
            .all()
        )
    ]
    if not linked_ids:
        return []
    rows = ChatHistory.query.filter(ChatHistory.chat_id.in_(linked_ids)).all()
    rows.sort(key=lambda row: row.timestamp, reverse=True)
    return rows


def _auto_generate_resources(user_id: int, style: str, topic: str, base_content: str) -> list[dict]:
    resources = []
    # Keep this lightweight to avoid chatbot timeouts.
    content_types = ["task_sheet", "solution"]
    for ctype in content_types:
        if ctype == "task_sheet":
            asset_text = (
                f"Topic: {topic}\n"
                f"Learning style: {style}\n"
                "Resource type: task_sheet\n\n"
                "Practice Task Sheet\n"
                "- Objective\n"
                "- Steps to implement\n"
                "- Test cases to run\n"
                "- Submission checklist\n\n"
                f"{base_content[:2800]}"
            )
        elif ctype == "solution":
            asset_text = (
                f"Topic: {topic}\n"
                f"Learning style: {style}\n"
                "Resource type: solution\n\n"
                "Worked Solution\n"
                "- Final code\n"
                "- Why this works\n"
                "- Expected output\n"
                "- Common mistakes avoided\n\n"
                f"{base_content[:2800]}"
            )

        file_path = create_download_file(user_id, ctype, asset_text)
        row = Download(user_id=user_id, content_type=ctype, file_path=file_path)
        db.session.add(row)
        db.session.flush()
        resources.append(
            {
                "download_id": row.download_id,
                "content_type": ctype,
                "download_url": f"/api/downloads/file/{row.download_id}",
            }
        )
    return resources


@chat_bp.route("", methods=["POST"], strict_slashes=False)
@jwt_required()
def ask_chatbot():
    user_id = int(get_jwt_identity())
    payload = request.get_json() or {}
    question = payload.get("question", "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400

    requested_thread_id = payload.get("thread_id")
    try:
        requested_thread_id = int(requested_thread_id) if requested_thread_id not in {None, "", 0} else None
    except (TypeError, ValueError):
        return jsonify({"error": "thread_id must be a number"}), 400

    style_row = LearningStyle.query.get(user_id)
    if not style_row:
        return jsonify({"error": "learning style not found"}), 400
    profile = db.session.get(UserProfile, user_id)
    preferred_language = "python"
    if profile and isinstance(profile.preferred_languages, list) and profile.preferred_languages:
        preferred_language = str(profile.preferred_languages[0]).strip().lower() or "python"

    requested_style = str(payload.get("style_override", "")).strip().lower()
    effective_style = requested_style if requested_style in {"visual", "auditory", "kinesthetic"} else style_row.learning_style
    mode = str(payload.get("mode", "detailed")).strip().lower() or "detailed"

    thread = _resolve_thread(user_id, requested_thread_id, title_hint=_topic_title(question))
    if not thread:
        return jsonify({"error": "thread not found"}), 404

    recent_history = _thread_history(thread.thread_id, user_id, limit=8)
    history_context = []
    for row in reversed(recent_history):
        history_context.append({"role": "user", "content": row.question})
        parsed = _safe_parse_response(row.response)
        history_context.append(
            {
                "role": "assistant",
                "content": str((parsed or {}).get("answer") or row.response or "")[:500],
            }
        )

    result = generate_chat_response(question, effective_style, mode, history_context)
    if result.get("error"):
        return jsonify(result), int(result.get("status") or 503)
    practice_tasks, practice_source = generate_practice_tasks_from_topic(
        question,
        language=preferred_language,
        count=3,
        allow_ai=True,
    )
    audio_download_id = None
    try:
        auto_resources = _auto_generate_resources(
            user_id=user_id,
            style=effective_style,
            topic=question,
            base_content=result["text"],
        )

        if effective_style == "auditory":
            audio_text = result.get("assets", {}).get("audio_script") or result.get("text", "")
            audio_path = create_download_file(user_id, "audio", audio_text)
            audio_row = Download(user_id=user_id, content_type="audio", file_path=audio_path)
            db.session.add(audio_row)
            db.session.flush()
            audio_download_id = audio_row.download_id

        stored_payload = dict(result)
        stored_payload.setdefault("text", result.get("answer", ""))
        history = ChatHistory(
            user_id=user_id,
            question=question,
            response=json.dumps(stored_payload, ensure_ascii=False),
            response_type=result["response_type"],
            learning_style_used=effective_style,
        )
        db.session.add(history)
        db.session.flush()
        db.session.add(ChatThreadMessage(thread_id=thread.thread_id, chat_id=history.chat_id, user_id=user_id))
        thread.message_count = (thread.message_count or 0) + 1
        thread.last_message_at = history.timestamp
        thread.preview = _truncate(question, 280)
        if not thread.title or thread.title == "New Chat":
            thread.title = _topic_title(question)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"error": "temporary database issue. please retry"}), 503

    result["auto_resources"] = auto_resources
    result["chat_id"] = history.chat_id
    if audio_download_id:
        result["audio_download_id"] = audio_download_id
    if practice_tasks:
        result["practice"] = {
            "topic": question,
            "language": preferred_language,
            "source": practice_source,
            "tasks": practice_tasks,
        }
    result["thread_id"] = thread.thread_id
    result["thread_title"] = thread.title
    return jsonify(result)


@chat_bp.post("/image")
@jwt_required()
def generate_chat_image():
    user_id = int(get_jwt_identity())
    payload = request.get_json(silent=True) or {}
    prompt = str(payload.get("prompt", "")).strip()

    requested_thread_id = payload.get("thread_id")
    try:
        requested_thread_id = int(requested_thread_id) if requested_thread_id not in {None, "", 0} else None
    except (TypeError, ValueError):
        return jsonify({"error": "thread_id must be a number"}), 400

    requested_chat_id = payload.get("chat_id")
    try:
        requested_chat_id = int(requested_chat_id) if requested_chat_id not in {None, "", 0} else None
    except (TypeError, ValueError):
        return jsonify({"error": "chat_id must be a number"}), 400

    source_row = None
    if requested_chat_id is not None:
        source_row = ChatHistory.query.filter_by(chat_id=requested_chat_id, user_id=user_id).first()
        if not source_row:
            return jsonify({"error": "chat not found"}), 404
        source_payload = _safe_parse_response(source_row.response) or {}
        prompt = prompt or str(
            source_payload.get("image_prompt")
            or source_payload.get("question")
            or source_row.question
            or source_payload.get("title")
            or source_row.question
            or ""
        ).strip()
        source_thread = ChatThreadMessage.query.filter_by(chat_id=source_row.chat_id, user_id=user_id).first()
        if source_thread and requested_thread_id is None:
            requested_thread_id = source_thread.thread_id

    thread = _resolve_thread(user_id, requested_thread_id, title_hint=_topic_title(prompt))
    if not thread:
        return jsonify({"error": "thread not found"}), 404

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    image_url = generate_image_data_url(prompt, size=str(payload.get("size", "1024x1024")))
    if not image_url:
        return jsonify({"error": "Image generation is temporarily unavailable"}), 503

    image_title = str(payload.get("title") or "Generated Image").strip() or "Generated Image"
    response_payload = {
        "title": image_title,
        "image_url": image_url,
        "image_prompt": prompt,
        "attached_to_text": source_row is not None,
        "summary": f"Generated an image for: {prompt[:180]}",
        "confidence": "High",
        "response_type": "visual",
        "mode": "image",
        "style": "visual",
        "follow_up_prompts": [
            "Generate another variation",
            "Make it more detailed",
            "Turn this into a diagram",
        ],
    }

    try:
        if source_row is not None:
            _update_chat_history_response(source_row, **response_payload)
            history = source_row
        else:
            response_payload["answer"] = "Image generated successfully. Use the preview below or open the attachment."
            history = ChatHistory(
                user_id=user_id,
                question=prompt,
                response=json.dumps(
                    {
                        **response_payload,
                        "summary": f"Generated an image for: {prompt[:180]}",
                        "answer": "Image generated successfully. Use the preview below or open the attachment.",
                    },
                    ensure_ascii=False,
                ),
                response_type="visual",
                learning_style_used="visual",
            )
            db.session.add(history)
            db.session.flush()
            db.session.add(ChatThreadMessage(thread_id=thread.thread_id, chat_id=history.chat_id, user_id=user_id))
            thread.message_count = (thread.message_count or 0) + 1
            thread.last_message_at = history.timestamp
            thread.preview = _truncate(prompt, 280)
            if not thread.title or thread.title == "New Chat":
                thread.title = _topic_title(prompt)
        thread.preview = _truncate(prompt, 280)
        if not thread.title or thread.title == "New Chat":
            thread.title = _topic_title(prompt)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"error": "temporary database issue. please retry"}), 503

    response_payload["chat_id"] = history.chat_id
    response_payload["thread_id"] = thread.thread_id
    response_payload["thread_title"] = thread.title
    if source_row is not None:
        response_payload["summary"] = f"Generated an image for: {prompt[:180]}"
    return jsonify(response_payload)


@chat_bp.post("/audio")
@jwt_required()
def generate_chat_audio():
    user_id = int(get_jwt_identity())
    payload = request.get_json(silent=True) or {}

    requested_chat_id = payload.get("chat_id")
    try:
        requested_chat_id = int(requested_chat_id) if requested_chat_id not in {None, "", 0} else None
    except (TypeError, ValueError):
        return jsonify({"error": "chat_id must be a number"}), 400

    if requested_chat_id is None:
        return jsonify({"error": "chat_id is required"}), 400

    row = ChatHistory.query.filter_by(chat_id=requested_chat_id, user_id=user_id).first()
    if not row:
        return jsonify({"error": "chat not found"}), 404

    parsed = _safe_parse_response(row.response) or {}
    audio_text = str(
        payload.get("text")
        or parsed.get("answer")
        or parsed.get("summary")
        or row.question
        or ""
    ).strip()
    if not audio_text:
        return jsonify({"error": "audio text is required"}), 400

    try:
        audio_path = create_download_file(user_id, "audio", audio_text)
        audio_row = Download(user_id=user_id, content_type="audio", file_path=audio_path)
        db.session.add(audio_row)
        db.session.flush()
        parsed["audio_download_id"] = audio_row.download_id
        parsed["audio_download_url"] = f"/api/downloads/file/{audio_row.download_id}"
        row.response = json.dumps(parsed, ensure_ascii=False)
        row.response_type = row.response_type or "auditory"
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"error": "temporary database issue. please retry"}), 503

    parsed["chat_id"] = row.chat_id
    thread_message = ChatThreadMessage.query.filter_by(chat_id=row.chat_id, user_id=user_id).first()
    parsed["thread_id"] = thread_message.thread_id if thread_message else None
    return jsonify(parsed)


@chat_bp.get("/threads")
@jwt_required()
def chat_threads():
    user_id = int(get_jwt_identity())
    threads = (
        ChatThread.query.filter_by(user_id=user_id)
        .order_by(ChatThread.last_message_at.desc().nullslast(), ChatThread.created_at.desc())
        .all()
    )
    return jsonify(
        {
            "threads": [_thread_payload(thread) for thread in threads],
            "active_thread_id": threads[0].thread_id if threads else None,
        }
    )


@chat_bp.post("/threads")
@jwt_required()
def create_chat_thread():
    user_id = int(get_jwt_identity())
    payload = request.get_json(silent=True) or {}
    title = _truncate(str(payload.get("title", "")).strip(), 200) or "New Chat"
    thread = ChatThread(user_id=user_id, title=title)
    db.session.add(thread)
    db.session.commit()
    return jsonify(_thread_payload(thread)), 201


@chat_bp.delete("/threads/<int:thread_id>")
@jwt_required()
def delete_chat_thread(thread_id: int):
    user_id = int(get_jwt_identity())
    thread = ChatThread.query.filter_by(thread_id=thread_id, user_id=user_id).first()
    if not thread:
        return jsonify({"error": "thread not found"}), 404

    try:
        linked_chat_ids = [row.chat_id for row in ChatThreadMessage.query.filter_by(thread_id=thread_id, user_id=user_id).all()]
        if linked_chat_ids:
            CodeLabTask.query.filter(
                CodeLabTask.user_id == user_id,
                or_(
                    CodeLabTask.source_chat_id.in_(linked_chat_ids),
                    CodeLabTask.source_thread_id == thread_id,
                ),
            ).delete(synchronize_session=False)
            LabWorkspaceState.query.filter(
                LabWorkspaceState.user_id == user_id,
                or_(
                    LabWorkspaceState.chat_id.in_(linked_chat_ids),
                    LabWorkspaceState.thread_id == thread_id,
                ),
            ).delete(synchronize_session=False)
            ChatFeedback.query.filter(
                ChatFeedback.user_id == user_id,
                ChatFeedback.chat_id.in_(linked_chat_ids),
            ).delete(synchronize_session=False)
            ChatThreadMessage.query.filter_by(thread_id=thread_id, user_id=user_id).delete(synchronize_session=False)
            ChatHistory.query.filter(
                ChatHistory.user_id == user_id,
                ChatHistory.chat_id.in_(linked_chat_ids),
            ).delete(synchronize_session=False)
        db.session.delete(thread)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"error": "failed to delete chat thread"}), 500

    threads = (
        ChatThread.query.filter_by(user_id=user_id)
        .order_by(ChatThread.last_message_at.desc().nullslast(), ChatThread.created_at.desc())
        .all()
    )
    return jsonify(
        {
            "message": "thread deleted",
            "thread_id": thread_id,
            "threads": [_thread_payload(item) for item in threads],
            "active_thread_id": threads[0].thread_id if threads else None,
        }
    )


@chat_bp.get("/threads/<int:thread_id>/history")
@jwt_required()
def thread_history(thread_id: int):
    user_id = int(get_jwt_identity())
    thread = ChatThread.query.filter_by(thread_id=thread_id, user_id=user_id).first()
    if not thread:
        return jsonify({"error": "thread not found"}), 404
    rows = _thread_history(thread_id, user_id, limit=60)
    feedback_rows = []
    if rows:
        feedback_rows = ChatFeedback.query.filter(
            ChatFeedback.user_id == user_id,
            ChatFeedback.chat_id.in_([r.chat_id for r in rows]),
        ).all()
    feedback_map = {f.chat_id: {"rating": f.rating, "comment": f.comment} for f in feedback_rows}
    return jsonify(
        {
            "thread": _thread_payload(thread),
            "messages": [
                {
                    "chat_id": r.chat_id,
                    "question": r.question,
                    "response": r.response,
                    "response_json": _safe_parse_response(r.response),
                    "response_type": r.response_type,
                    "learning_style_used": r.learning_style_used,
                    "timestamp": r.timestamp.isoformat(),
                    "feedback": feedback_map.get(r.chat_id),
                    "thread_id": thread.thread_id,
                }
                for r in rows
            ],
        }
    )


@chat_bp.get("/history")
@jwt_required()
def chat_history():
    user_id = int(get_jwt_identity())
    thread_id = request.args.get("thread_id", type=int)
    thread = _resolve_thread(user_id, thread_id, create_if_missing=False)
    if not thread:
        return jsonify([])
    rows = _thread_history(thread.thread_id, user_id, limit=30)
    feedback_rows = []
    if rows:
        feedback_rows = ChatFeedback.query.filter(
            ChatFeedback.user_id == user_id,
            ChatFeedback.chat_id.in_([r.chat_id for r in rows]),
        ).all()
    feedback_map = {f.chat_id: {"rating": f.rating, "comment": f.comment} for f in feedback_rows}

    return jsonify(
        [
            {
                "chat_id": r.chat_id,
                "question": r.question,
                "response": r.response,
                "response_json": _safe_parse_response(r.response),
                "response_type": r.response_type,
                "learning_style_used": r.learning_style_used,
                "timestamp": r.timestamp.isoformat(),
                "feedback": feedback_map.get(r.chat_id),
                "thread_id": thread.thread_id,
                "thread_title": thread.title,
            }
            for r in rows
        ]
    )


def _safe_parse_response(raw: str):
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _update_chat_history_response(row: ChatHistory, **updates):
    payload = _safe_parse_response(row.response) or {}
    for key, value in updates.items():
        if value is not None:
            payload[key] = value
    row.response = json.dumps(payload, ensure_ascii=False)
    return payload


@chat_bp.get("/suggestions")
@jwt_required()
def chat_suggestions():
    user_id = int(get_jwt_identity())
    topic = (request.args.get("topic") or "").strip()
    requested_style = (request.args.get("style_override") or "").strip().lower()
    style_row = LearningStyle.query.get(user_id)
    style = requested_style if requested_style in {"visual", "auditory", "kinesthetic"} else (style_row.learning_style if style_row else "visual")
    prompts = get_quick_prompts(topic or "Java basics", style)
    return jsonify({"topic": topic or "Java basics", "prompts": prompts})


@chat_bp.delete("/history/<int:chat_id>")
@jwt_required()
def delete_chat_item(chat_id: int):
    user_id = int(get_jwt_identity())
    row = ChatHistory.query.filter_by(chat_id=chat_id, user_id=user_id).first()
    if not row:
        return jsonify({"error": "chat not found"}), 404
    ChatFeedback.query.filter_by(chat_id=chat_id, user_id=user_id).delete()
    db.session.delete(row)
    db.session.commit()
    return jsonify({"message": "chat deleted", "chat_id": chat_id})


@chat_bp.delete("/history")
@jwt_required()
def clear_history():
    user_id = int(get_jwt_identity())
    try:
        thread_ids = [r.thread_id for r in ChatThread.query.filter_by(user_id=user_id).all()]
        if thread_ids:
            ChatThreadMessage.query.filter(
                ChatThreadMessage.user_id == user_id,
                ChatThreadMessage.thread_id.in_(thread_ids),
            ).delete(synchronize_session=False)
            ChatThread.query.filter(ChatThread.thread_id.in_(thread_ids)).delete(synchronize_session=False)
        chat_ids = [r.chat_id for r in ChatHistory.query.filter_by(user_id=user_id).all()]
        if chat_ids:
            ChatFeedback.query.filter(
                ChatFeedback.user_id == user_id,
                ChatFeedback.chat_id.in_(chat_ids),
            ).delete(synchronize_session=False)
        ChatHistory.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        return jsonify({"message": "chat history cleared"})
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"error": "failed to clear chat history"}), 500


@chat_bp.post("/feedback")
@jwt_required()
def chat_feedback():
    user_id = int(get_jwt_identity())
    payload = request.get_json() or {}
    try:
        chat_id = int(payload.get("chat_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "chat_id is required"}), 400

    try:
        rating = int(payload.get("rating"))
    except (TypeError, ValueError):
        return jsonify({"error": "rating must be 1 or -1"}), 400
    if rating not in {1, -1}:
        return jsonify({"error": "rating must be 1 or -1"}), 400

    comment = str(payload.get("comment", "")).strip()[:600]
    chat_row = ChatHistory.query.filter_by(chat_id=chat_id, user_id=user_id).first()
    if not chat_row:
        return jsonify({"error": "chat not found"}), 404

    row = ChatFeedback.query.filter_by(chat_id=chat_id, user_id=user_id).first()
    if not row:
        row = ChatFeedback(chat_id=chat_id, user_id=user_id, rating=rating, comment=comment or None)
        db.session.add(row)
    else:
        row.rating = rating
        row.comment = comment or None

    moderation_row = ModerationItem.query.filter_by(item_type="feedback", source_id=chat_id, user_id=user_id).first()
    if rating == -1:
        if not moderation_row:
            chat_row = ChatHistory.query.filter_by(chat_id=chat_id, user_id=user_id).first()
            content = comment or (chat_row.response if chat_row else "")
            moderation_row = ModerationItem(
                item_type="feedback",
                source_id=chat_id,
                user_id=user_id,
                content=content or "Feedback flagged for review.",
                reason="Negative feedback",
                confidence="Medium",
                status="pending",
            )
            db.session.add(moderation_row)
        else:
            moderation_row.status = "pending"
            moderation_row.reason = "Negative feedback"
            moderation_row.reviewed_by = None
            moderation_row.reviewed_at = None
    elif moderation_row and moderation_row.status == "pending":
        moderation_row.status = "reviewed"
        moderation_row.reviewed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "feedback saved", "chat_id": chat_id, "rating": rating})
