from collections import Counter
from typing import Any

from app.extensions import db
from app.models import (
    ChatHistory,
    DailyTask,
    LearningStyle,
    PracticeActivity,
    RewardWallet,
    User,
    UserProfile,
    UserStreak,
    WeeklyQuizAttempt,
)
from app.services.openai_service import openai_json_schema


STUDY_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "learning_style": {
            "type": "string",
            "enum": ["visual", "auditory", "kinesthetic", "blended"],
        },
        "overview": {"type": "string"},
        "focus_area": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "gaps": {"type": "array", "items": {"type": "string"}},
        "today_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "minutes": {"type": "integer"},
                    "action": {"type": "string"},
                    "success_criteria": {"type": "string"},
                },
                "required": ["title", "minutes", "action", "success_criteria"],
                "additionalProperties": False,
            },
        },
        "weekly_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day": {"type": "string"},
                    "focus": {"type": "string"},
                    "task": {"type": "string"},
                },
                "required": ["day", "focus", "task"],
                "additionalProperties": False,
            },
        },
        "quick_wins": {"type": "array", "items": {"type": "string"}},
        "next_action": {"type": "string"},
        "motivation": {"type": "string"},
    },
    "required": [
        "title",
        "learning_style",
        "overview",
        "focus_area",
        "strengths",
        "gaps",
        "today_plan",
        "weekly_plan",
        "quick_wins",
        "next_action",
        "motivation",
    ],
    "additionalProperties": False,
}


def _recent_topics(user_id: int) -> list[str]:
    rows = (
        ChatHistory.query.filter_by(user_id=user_id)
        .order_by(ChatHistory.timestamp.desc())
        .limit(20)
        .all()
    )
    counter = Counter()
    for row in rows:
        tokens = [token.strip(".,!?()[]{}:;\"'").lower() for token in row.question.split()]
        for token in tokens:
            if len(token) < 4 or token in {"what", "when", "this", "that", "with", "from", "java"}:
                continue
            counter[token] += 1
    return [item for item, _ in counter.most_common(8)]


def _fallback_plan(context: dict[str, Any]) -> dict[str, Any]:
    weak_topics = context.get("weak_topics") or []
    recent_topics = context.get("recent_topics") or []
    style = context.get("learning_style") or "blended"
    focus = weak_topics[0] if weak_topics else (recent_topics[0].title() if recent_topics else "Core fundamentals")
    today_plan = [
        {
            "title": "Warm-up review",
            "minutes": 10,
            "action": f"Review the key idea behind {focus} with one notebook summary.",
            "success_criteria": "You can explain the concept in one sentence.",
        },
        {
            "title": "Active practice",
            "minutes": 25,
            "action": f"Solve one coding or concept exercise on {focus} and check your answer.",
            "success_criteria": "You complete one focused practice loop without getting stuck.",
        },
        {
            "title": "Reflection",
            "minutes": 10,
            "action": "Write down the 2 mistakes you made and the fix for each one.",
            "success_criteria": "You leave with a clear next improvement step.",
        },
    ]
    weekly_plan = [
        {"day": "Mon", "focus": focus, "task": "Build the core mental model"},
        {"day": "Tue", "focus": "guided practice", "task": "Solve 2 medium problems"},
        {"day": "Wed", "focus": "review", "task": "Revisit mistakes and rewrite notes"},
        {"day": "Thu", "focus": "application", "task": "Use the topic in a new problem"},
        {"day": "Fri", "focus": "quiz", "task": "Run a short self-test"},
        {"day": "Sat", "focus": "project", "task": "Apply the topic in a mini project"},
        {"day": "Sun", "focus": "rest + recap", "task": "Light review and next-week planning"},
    ]
    return {
        "title": f"{style.title()} growth plan",
        "learning_style": style,
        "overview": f"Focus on one measurable improvement area each day so you keep momentum without overwhelming yourself.",
        "focus_area": focus,
        "strengths": context.get("strengths") or ["Consistency", "Willingness to practice"],
        "gaps": weak_topics or ["A clearer weekly structure", "More deliberate practice"],
        "today_plan": today_plan,
        "weekly_plan": weekly_plan,
        "quick_wins": [
            "Finish one 10-minute review block",
            "Complete one practice problem",
            "Write a 3-line summary of what you learned",
        ],
        "next_action": f"Start with a 10-minute review of {focus} and then do one practice round.",
        "motivation": "Small wins stack fast. One focused session today is enough to move the needle.",
        "source": "fallback",
    }


def _allow_ai_fallback() -> bool:
    return os.getenv("ALLOW_AI_FALLBACK", "0").strip().lower() in {"1", "true", "yes", "on"}


def build_ai_study_plan(user_id: int) -> dict[str, Any]:
    user = db.session.get(User, user_id)
    if not user:
        return {"error": "user not found"}

    profile = db.session.get(UserProfile, user_id)
    style_row = db.session.get(LearningStyle, user_id)
    wallet = db.session.get(RewardWallet, user_id)
    streak = db.session.get(UserStreak, user_id)
    tasks = DailyTask.query.filter_by(user_id=user_id).order_by(DailyTask.updated_at.desc()).limit(5).all()
    practices = PracticeActivity.query.filter_by(user_id=user_id).order_by(PracticeActivity.updated_at.desc()).limit(10).all()
    attempts = WeeklyQuizAttempt.query.filter_by(user_id=user_id).order_by(WeeklyQuizAttempt.created_at.desc()).limit(5).all()
    recent_topics = _recent_topics(user_id)

    strengths: list[str] = []
    if wallet and wallet.current_xp >= 500:
        strengths.append("You are already building strong momentum")
    if streak and streak.current_streak >= 3:
        strengths.append(f"Your {streak.current_streak}-day streak is a real asset")
    if attempts and max((a.percentage for a in attempts), default=0) >= 70:
        strengths.append("You can hold onto quiz knowledge well")
    if practices and any((p.status or "").lower() == "completed" for p in practices):
        strengths.append("You convert practice into action")
    if not strengths:
        strengths = ["You are still early in the journey, which makes improvement easy to measure"]

    weak_topics = []
    if profile and isinstance(profile.topic_mastery_json, dict):
        raw = profile.topic_mastery_json.get("weak_topics", [])
        if isinstance(raw, list):
            weak_topics = [str(item) for item in raw if str(item).strip()]
    if not weak_topics:
        weak_topics = [row.task_name for row in practices[:2] if row.task_name]

    learning_style = (style_row.learning_style if style_row else "blended").strip().lower()
    if learning_style not in {"visual", "auditory", "kinesthetic"}:
        learning_style = "blended"

    context = {
        "name": user.name,
        "learning_style": learning_style,
        "level": wallet.level if wallet else 1,
        "xp": wallet.current_xp if wallet else 0,
        "streak": streak.current_streak if streak else 0,
        "weak_topics": weak_topics[:6],
        "recent_topics": recent_topics,
        "strengths": strengths[:5],
        "latest_tasks": [task.title for task in tasks if task.title][:5],
        "latest_practices": [practice.task_name for practice in practices if practice.task_name][:5],
        "latest_quiz_scores": [round(attempt.percentage, 1) for attempt in attempts if attempt.percentage is not None][:5],
    }

    system_prompt = (
        "You are an expert learning coach for an adaptive AI study app. "
        "Generate a practical study plan that is encouraging, specific, and easy to follow. "
        "Do not mention internal policy. Keep the response concise but useful."
    )
    user_prompt = (
        f"User profile:\n{context}\n\n"
        "Create a personalized weekly study plan that helps this learner make progress today and this week. "
        "Use the provided learning style and recent activity to choose the most useful focus area. "
        "Return a structured JSON object with actionable steps."
    )

    ai_plan = openai_json_schema(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema=STUDY_PLAN_SCHEMA,
        name="study_plan",
        temperature=0.25,
    )
    if not ai_plan:
        if not _allow_ai_fallback():
            return {"error": "OpenAI study plan unavailable", "status": 503}
        fallback = _fallback_plan(context)
        fallback["context"] = context
        return fallback

    ai_plan["source"] = "openai"
    ai_plan["context"] = context
    return ai_plan
