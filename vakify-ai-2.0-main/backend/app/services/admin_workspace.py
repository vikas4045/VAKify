from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import desc, func

from app.extensions import db
from app.models import ChatbotConfig, LeaderboardSnapshot, XPEvent, User

DEFAULT_CHATBOT_PROMPT = (
    "You are Vakify's admin-managed AI tutor. "
    "Answer naturally, clearly, and help learners make progress. "
    "Stay concise unless the question needs depth."
)


def _default_chatbot_values() -> dict:
    return {
        "enabled": True,
        "assistant_name": "Vakify AI",
        "response_style": "friendly",
        "max_response_chars": 1200,
        "system_prompt": DEFAULT_CHATBOT_PROMPT,
    }


def get_chatbot_config() -> ChatbotConfig:
    config = db.session.get(ChatbotConfig, 1)
    if not config:
        defaults = _default_chatbot_values()
        config = ChatbotConfig(config_id=1, **defaults)
        db.session.add(config)
        db.session.commit()
    return config


def serialize_chatbot_config(config: ChatbotConfig) -> dict:
    return {
        "enabled": bool(config.enabled),
        "assistant_name": config.assistant_name,
        "response_style": config.response_style,
        "max_response_chars": int(config.max_response_chars or 1200),
        "system_prompt": config.system_prompt or DEFAULT_CHATBOT_PROMPT,
        "updated_by": config.updated_by,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


def update_chatbot_config(payload: dict, updated_by: int | None = None) -> ChatbotConfig:
    config = get_chatbot_config()
    if "enabled" in payload:
        config.enabled = bool(payload.get("enabled"))
    if "assistant_name" in payload:
        config.assistant_name = str(payload.get("assistant_name") or "").strip() or "Vakify AI"
    if "response_style" in payload:
        response_style = str(payload.get("response_style") or "friendly").strip().lower()
        config.response_style = response_style if response_style in {"friendly", "direct", "coach", "concise"} else "friendly"
    if "max_response_chars" in payload:
        try:
            config.max_response_chars = max(400, min(4000, int(payload.get("max_response_chars") or 1200)))
        except (TypeError, ValueError):
            config.max_response_chars = 1200
    if "system_prompt" in payload:
        prompt = str(payload.get("system_prompt") or "").strip()
        config.system_prompt = prompt or DEFAULT_CHATBOT_PROMPT
    config.updated_by = updated_by
    db.session.commit()
    return config


def _week_bounds(reference_date):
    start = reference_date - timedelta(days=reference_date.weekday())
    end = start + timedelta(days=6)
    return start, end


def _leaderboard_rows(scope: str, limit: int = 10) -> list[dict]:
    query = db.session.query(
        XPEvent.user_id,
        func.sum(XPEvent.points).label("score"),
    )
    if scope == "weekly":
        week_start, _ = _week_bounds(datetime.utcnow().date())
        query = query.filter(XPEvent.created_at >= datetime.combine(week_start, datetime.min.time()))

    rows = (
        query.group_by(XPEvent.user_id)
        .order_by(desc("score"), XPEvent.user_id.asc())
        .limit(limit)
        .all()
    )

    payload: list[dict] = []
    for idx, row in enumerate(rows, start=1):
        user = User.query.get(row.user_id)
        payload.append(
            {
                "rank": idx,
                "user_id": row.user_id,
                "name": user.name if user else f"User {row.user_id}",
                "score": int(row.score or 0),
            }
        )
    return payload


def rebuild_leaderboard_snapshots() -> dict:
    today = datetime.utcnow().date()
    week_start, week_end = _week_bounds(today)
    week_key = f"{week_start.strftime('%Y-W%V')}"

    scopes = {
        "weekly": week_key,
        "all_time": None,
    }
    results: dict[str, dict] = {}

    for scope, current_week_key in scopes.items():
        rows = _leaderboard_rows(scope, limit=50)
        query = LeaderboardSnapshot.query.filter(LeaderboardSnapshot.scope == scope)
        if current_week_key is None:
            query = query.filter(LeaderboardSnapshot.week_key.is_(None))
        else:
            query = query.filter(LeaderboardSnapshot.week_key == current_week_key)
        query.delete(synchronize_session=False)
        db.session.flush()

        for item in rows:
            db.session.add(
                LeaderboardSnapshot(
                    user_id=item["user_id"],
                    scope=scope,
                    week_key=current_week_key,
                    rank=item["rank"],
                    score=item["score"],
                )
            )

        results[scope] = {
            "scope": scope,
            "week_key": current_week_key,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "rows": rows,
            "snapshot_count": len(rows),
            "updated_at": datetime.utcnow().isoformat(),
        }

    db.session.commit()
    return results


def leaderboard_management_payload() -> dict:
    weekly = _leaderboard_rows("weekly", limit=10)
    all_time = _leaderboard_rows("all_time", limit=10)
    current_week_start, current_week_end = _week_bounds(datetime.utcnow().date())
    weekly_snapshot_count = (
        db.session.query(func.count(LeaderboardSnapshot.snapshot_id))
        .filter(
            LeaderboardSnapshot.scope == "weekly",
            LeaderboardSnapshot.week_key == f"{current_week_start.strftime('%Y-W%V')}",
        )
        .scalar()
        or 0
    )
    all_time_snapshot_count = (
        db.session.query(func.count(LeaderboardSnapshot.snapshot_id))
        .filter(LeaderboardSnapshot.scope == "all_time")
        .scalar()
        or 0
    )
    return {
        "weekly": {
            "scope": "weekly",
            "week_key": f"{current_week_start.strftime('%Y-W%V')}",
            "week_start": current_week_start.isoformat(),
            "week_end": current_week_end.isoformat(),
            "rows": weekly,
            "snapshot_count": weekly_snapshot_count,
        },
        "all_time": {
            "scope": "all_time",
            "week_key": None,
            "rows": all_time,
            "snapshot_count": all_time_snapshot_count,
        },
    }
