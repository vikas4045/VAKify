from collections import Counter
from datetime import datetime, timedelta

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import ChatHistory, Download, LearningStyle, PracticeActivity, UserProfile, WeeklyQuizAttempt


dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


def _date_key(dt):
    return dt.strftime("%Y-%m-%d")


def _build_daily_series(items, date_attr: str, days: int = 7):
    today = datetime.utcnow().date()
    labels = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]
    count_map = {k: 0 for k in labels}
    for item in items:
        value = getattr(item, date_attr, None)
        if not value:
            continue
        key = _date_key(value)
        if key in count_map:
            count_map[key] += 1
    return [{"date": day, "count": count_map[day]} for day in labels]


def _normalize_token(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace()).strip()


def _topic_confidence(user_id: int) -> list[dict]:
    chats = ChatHistory.query.filter_by(user_id=user_id).order_by(ChatHistory.timestamp.desc()).limit(40).all()
    practices = PracticeActivity.query.filter_by(user_id=user_id).order_by(PracticeActivity.updated_at.desc()).limit(25).all()
    downloads = Download.query.filter_by(user_id=user_id).order_by(Download.timestamp.desc()).limit(25).all()
    quizzes = WeeklyQuizAttempt.query.filter_by(user_id=user_id).order_by(WeeklyQuizAttempt.created_at.desc()).limit(12).all()

    counter: Counter[str] = Counter()
    for row in chats:
        for token in _normalize_token(row.question).split():
            if len(token) >= 4:
                counter[token] += 2
    for row in practices:
        for token in _normalize_token(row.task_name).split():
            if len(token) >= 4:
                counter[token] += 3 if (row.status or "").lower() == "completed" else 1
    for row in downloads:
        for token in _normalize_token(row.content_type).split():
            if len(token) >= 4:
                counter[token] += 1
    for row in quizzes:
        if row.percentage is not None:
            counter["quiz mastery"] += int(max(0, min(100, row.percentage)) / 10)

    rows = []
    for topic, score in counter.most_common(5):
        confidence = max(20, min(100, 35 + score * 5))
        rows.append(
            {
                "topic": topic.title(),
                "confidence": confidence,
                "trend": "up" if confidence >= 70 else "neutral" if confidence >= 50 else "down",
            }
        )
    return rows


def _learning_style_breakdown(user_id: int) -> list[dict]:
    profile = db.session.get(UserProfile, user_id)
    style_row = db.session.get(LearningStyle, user_id)
    if style_row:
        total = max(1, style_row.visual_score + style_row.auditory_score + style_row.kinesthetic_score)
        return [
            {"subject": "Visual", "value": round((style_row.visual_score / total) * 100)},
            {"subject": "Audio", "value": round((style_row.auditory_score / total) * 100)},
            {"subject": "Kinetic", "value": round((style_row.kinesthetic_score / total) * 100)},
            {"subject": "Reading", "value": max(0, 100 - round(((style_row.visual_score + style_row.auditory_score + style_row.kinesthetic_score) / total) * 100))},
        ]
    if profile:
        total = max(0.01, float(profile.visual_weight + profile.auditory_weight + profile.kinesthetic_weight))
        return [
            {"subject": "Visual", "value": round((profile.visual_weight / total) * 100)},
            {"subject": "Audio", "value": round((profile.auditory_weight / total) * 100)},
            {"subject": "Kinetic", "value": round((profile.kinesthetic_weight / total) * 100)},
            {"subject": "Reading", "value": 100 - round(((profile.visual_weight + profile.auditory_weight + profile.kinesthetic_weight) / total) * 100)},
        ]
    return []


def _weak_topics(user_id: int, topic_rows: list[dict]) -> list[dict]:
    profile = db.session.get(UserProfile, user_id)
    weak_topics = []
    if profile and isinstance(profile.topic_mastery_json, dict):
        raw = profile.topic_mastery_json.get("weak_topics", [])
        if isinstance(raw, list):
            weak_topics = [str(item) for item in raw if str(item).strip()]

    if weak_topics:
        return [
            {
                "name": item,
                "score": max(10, 55 - idx * 8),
                "priority": "High" if max(10, 55 - idx * 8) < 50 else "Medium",
                "color": "#E76F51" if max(10, 55 - idx * 8) < 50 else "#F4A261",
            }
            for idx, item in enumerate(weak_topics[:3])
        ]

    return [
        {
            "name": item["topic"],
            "score": max(20, min(90, item["confidence"] - 20)),
            "priority": "High" if max(20, min(90, item["confidence"] - 20)) < 50 else "Medium",
            "color": "#E76F51" if max(20, min(90, item["confidence"] - 20)) < 50 else "#F4A261",
        }
        for item in topic_rows[-3:]
    ]


def _performance_over_time(user_id: int) -> list[dict]:
    today = datetime.utcnow().date()
    rows = []
    for idx in range(3, -1, -1):
        week_start = today - timedelta(days=today.weekday() + idx * 7)
        week_end = week_start + timedelta(days=6)
        practices = PracticeActivity.query.filter(
            PracticeActivity.user_id == user_id,
            PracticeActivity.updated_at >= datetime.combine(week_start, datetime.min.time()),
            PracticeActivity.updated_at < datetime.combine(week_end + timedelta(days=1), datetime.min.time()),
        ).all()
        quizzes = WeeklyQuizAttempt.query.filter(
            WeeklyQuizAttempt.user_id == user_id,
            WeeklyQuizAttempt.created_at >= datetime.combine(week_start, datetime.min.time()),
            WeeklyQuizAttempt.created_at < datetime.combine(week_end + timedelta(days=1), datetime.min.time()),
        ).all()
        completed = sum(1 for row in practices if (row.status or "").lower() == "completed")
        quiz_avg = sum((row.percentage or 0) for row in quizzes) / len(quizzes) if quizzes else 0
        rows.append({"week": f"Week {4 - idx}", "score": min(100, int(completed * 20 + quiz_avg * 0.6))})
    return rows


def _skill_distribution(user_id: int) -> list[dict]:
    chats = ChatHistory.query.filter_by(user_id=user_id).count()
    practices = PracticeActivity.query.filter_by(user_id=user_id).count()
    downloads = Download.query.filter_by(user_id=user_id).count()
    quizzes = WeeklyQuizAttempt.query.filter_by(user_id=user_id).count()
    return [
        {"name": "Chats", "value": max(1, chats)},
        {"name": "Practice", "value": max(1, practices)},
        {"name": "Downloads", "value": max(1, downloads)},
        {"name": "Quizzes", "value": max(1, quizzes)},
    ]


@dashboard_bp.get("/insights")
@jwt_required()
def insights():
    user_id = int(get_jwt_identity())
    chats = (
        ChatHistory.query.filter_by(user_id=user_id)
        .order_by(ChatHistory.timestamp.desc())
        .limit(120)
        .all()
    )
    downloads = (
        Download.query.filter_by(user_id=user_id)
        .order_by(Download.timestamp.desc())
        .limit(120)
        .all()
    )
    practices = (
        PracticeActivity.query.filter_by(user_id=user_id)
        .order_by(PracticeActivity.updated_at.desc())
        .limit(120)
        .all()
    )

    completed = [p for p in practices if (p.status or "").lower() == "completed"]
    total_time = sum((p.time_spent or 0) for p in practices)
    mastery_score = min(100, int(len(completed) * 12 + min(total_time / 45, 45)))

    # simple recommendation from most frequent recent topic keywords
    topic_counter = Counter()
    for row in chats[:25]:
        for token in row.question.lower().split():
            clean = "".join(ch for ch in token if ch.isalnum())
            if len(clean) < 4:
                continue
            if clean in {"explain", "about", "what", "does", "java", "with", "from", "into"}:
                continue
            topic_counter[clean] += 1
    top = topic_counter.most_common(1)
    recommended = f"Advanced {top[0][0].capitalize()} in Java" if top else "Object-oriented programming fundamentals"
    topic_rows = _topic_confidence(user_id)

    # streak = consecutive days with any activity ending today
    activity_days = set()
    for row in chats:
        activity_days.add(_date_key(row.timestamp))
    for row in downloads:
        activity_days.add(_date_key(row.timestamp))
    for row in practices:
        activity_days.add(_date_key(row.updated_at))
    streak = 0
    cursor = datetime.utcnow().date()
    while cursor.strftime("%Y-%m-%d") in activity_days:
        streak += 1
        cursor -= timedelta(days=1)

    return jsonify(
        {
            "mastery_score": mastery_score,
            "streak_days": streak,
            "recommended_topic": recommended,
            "daily_chat": _build_daily_series(chats, "timestamp", days=7),
            "daily_practice": _build_daily_series(practices, "updated_at", days=7),
            "daily_downloads": _build_daily_series(downloads, "timestamp", days=7),
            "topic_confidence": topic_rows,
            "learning_style_breakdown": _learning_style_breakdown(user_id),
            "weak_topics": _weak_topics(user_id, topic_rows),
            "performance_over_time": _performance_over_time(user_id),
            "skill_distribution": _skill_distribution(user_id),
        }
    )
