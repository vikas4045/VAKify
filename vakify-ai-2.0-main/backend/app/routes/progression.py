from datetime import date, datetime, timedelta
from copy import deepcopy
from collections import Counter

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import desc, func

from app.extensions import db
from app.models import (
    ChatHistory,
    CodeLabSubmission,
    DailyTask,
    DailyTaskAttempt,
    Download,
    LearningStyle,
    PracticeActivity,
    RewardWallet,
    User,
    UserProfile,
    UserStreak,
    RewardRedemption,
    WeeklyQuiz,
    WeeklyQuizAttempt,
    XPEvent,
)
from app.services.progression_content_service import (
    build_daily_task_bundle,
    build_weekly_quiz_bundle,
    normalize_language,
)


progression_bp = Blueprint("progression", __name__, url_prefix="/api")


def _week_bounds(today: date) -> tuple[date, date]:
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


def _week_key(day: date) -> str:
    y, w, _ = day.isocalendar()
    return f"{y}-W{w:02d}"


def _ensure_profile(user_id: int) -> UserProfile:
    with db.session.no_autoflush:
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


def _ensure_wallet(user_id: int) -> RewardWallet:
    with db.session.no_autoflush:
        wallet = db.session.get(RewardWallet, user_id)
        if not wallet:
            wallet = RewardWallet(user_id=user_id, current_xp=0, level=1, reward_points=0)
            db.session.add(wallet)
    return wallet


def _ensure_streak(user_id: int) -> UserStreak:
    with db.session.no_autoflush:
        streak = db.session.get(UserStreak, user_id)
        if not streak:
            streak = UserStreak(user_id=user_id, current_streak=0, longest_streak=0, last_active_date=None)
            db.session.add(streak)
    return streak


def _preferred_language(profile: UserProfile | None) -> str | None:
    if profile and isinstance(profile.preferred_languages, list) and profile.preferred_languages:
        return normalize_language(profile.preferred_languages[0])
    return None


def _touch_streak(streak: UserStreak, active_day: date) -> None:
    if streak.last_active_date == active_day:
        return
    if streak.last_active_date == (active_day - timedelta(days=1)):
        streak.current_streak += 1
    else:
        streak.current_streak = 1
    streak.last_active_date = active_day
    if streak.current_streak > streak.longest_streak:
        streak.longest_streak = streak.current_streak


def _award_xp(user_id: int, points: int, source: str, source_id: int | None = None, meta: dict | None = None) -> RewardWallet:
    wallet = _ensure_wallet(user_id)
    wallet.current_xp += max(0, points)
    wallet.reward_points += max(0, points)
    wallet.level = max(1, (wallet.current_xp // 200) + 1)
    row = XPEvent(
        user_id=user_id,
        source=source,
        source_id=source_id,
        points=max(0, points),
        meta=meta or {},
    )
    db.session.add(row)
    return wallet


REWARD_CATALOG = [
    {
        "reward_key": "avatar_frame",
        "name": "Custom Avatar Frame",
        "cost": 500,
        "description": "Add a premium frame to your profile card.",
        "icon": "Crown",
    },
    {
        "reward_key": "xp_boost_24h",
        "name": "XP Boost (24h)",
        "cost": 300,
        "description": "Earn bonus XP for the next 24 hours.",
        "icon": "Zap",
    },
    {
        "reward_key": "priority_support",
        "name": "Priority Support",
        "cost": 750,
        "description": "Move your support requests to the front of the queue.",
        "icon": "Trophy",
    },
    {
        "reward_key": "exclusive_course",
        "name": "Unlock Exclusive Course",
        "cost": 1000,
        "description": "Unlock a premium course module for deeper practice.",
        "icon": "Award",
    },
]

BADGE_CATALOG = [
    {
        "name": "First Steps",
        "description": "Complete your first task or send your first chat",
        "icon": "🎯",
        "threshold": "activity",
    },
    {
        "name": "Code Master",
        "description": "Complete 10 lab runs or practice submissions",
        "icon": "💻",
        "threshold": "code",
    },
    {
        "name": "Quiz Champion",
        "description": "Score 90%+ on a weekly quiz",
        "icon": "🏆",
        "threshold": "quiz",
    },
    {
        "name": "Streak Legend",
        "description": "Maintain a 7-day streak",
        "icon": "🔥",
        "threshold": "streak",
    },
    {
        "name": "Momentum Builder",
        "description": "Earn 500 XP",
        "icon": "⚡",
        "threshold": "xp",
    },
]


def _normalize_token(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace()).strip()


def _topic_scores(user_id: int) -> list[dict]:
    chat_rows = ChatHistory.query.filter_by(user_id=user_id).order_by(ChatHistory.timestamp.desc()).limit(30).all()
    practice_rows = PracticeActivity.query.filter_by(user_id=user_id).order_by(PracticeActivity.updated_at.desc()).limit(20).all()
    task_rows = DailyTask.query.filter_by(user_id=user_id).order_by(DailyTask.updated_at.desc()).limit(20).all()
    quiz_rows = WeeklyQuizAttempt.query.filter_by(user_id=user_id).order_by(WeeklyQuizAttempt.created_at.desc()).limit(12).all()

    counter: Counter[str] = Counter()
    for row in chat_rows:
        for token in _normalize_token(row.question).split():
            if len(token) >= 4:
                counter[token] += 2
    for row in practice_rows:
        for token in _normalize_token(row.task_name).split():
            if len(token) >= 4:
                counter[token] += 3 if (row.status or "").lower() == "completed" else 1
    for row in task_rows:
        for token in _normalize_token(row.title).split():
            if len(token) >= 4:
                counter[token] += 2 if (row.status or "").lower() == "completed" else 1
    for row in quiz_rows:
        if row.percentage is not None:
            counter["quiz mastery"] += int(max(0, min(100, row.percentage)) / 10)

    topic_rows = []
    for idx, (topic, score) in enumerate(counter.most_common(5)):
        confidence = max(20, min(100, 35 + score * 5))
        topic_rows.append(
            {
                "topic": topic.title(),
                "confidence": confidence,
                "trend": "up" if confidence >= 70 else "neutral" if confidence >= 50 else "down",
            }
        )
    return topic_rows


def _learning_style_breakdown(profile: UserProfile | None, style_row: LearningStyle | None) -> list[dict]:
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

    return [
        {"subject": "Visual", "value": 33},
        {"subject": "Audio", "value": 33},
        {"subject": "Kinetic", "value": 34},
        {"subject": "Reading", "value": 0},
    ]


def _weak_topics(profile: UserProfile | None, topic_rows: list[dict]) -> list[dict]:
    weak_topics: list[str] = []
    if profile and isinstance(profile.topic_mastery_json, dict):
        raw = profile.topic_mastery_json.get("weak_topics", [])
        if isinstance(raw, list):
            weak_topics = [str(item) for item in raw if str(item).strip()]

    if weak_topics:
        rows = []
        for idx, item in enumerate(weak_topics[:3]):
            score = max(10, 55 - idx * 8)
            rows.append(
                {
                    "name": item,
                    "score": score,
                    "priority": "High" if score < 50 else "Medium",
                    "color": "#E76F51" if score < 50 else "#F4A261",
                }
            )
        return rows

    rows = []
    for idx, item in enumerate(topic_rows[-3:]):
        score = max(20, min(90, item["confidence"] - 20))
        rows.append(
            {
                "name": item["topic"],
                "score": score,
                "priority": "High" if score < 50 else "Medium",
                "color": "#E76F51" if score < 50 else "#F4A261",
            }
        )
    return rows


def _performance_over_time(user_id: int) -> list[dict]:
    today = datetime.utcnow().date()
    weeks = []
    for idx in range(3, -1, -1):
        week_start = today - timedelta(days=today.weekday() + idx * 7)
        week_end = week_start + timedelta(days=6)
        task_attempts = DailyTaskAttempt.query.join(DailyTask, DailyTask.task_id == DailyTaskAttempt.task_id).filter(
            DailyTaskAttempt.user_id == user_id,
            DailyTask.due_date >= week_start,
            DailyTask.due_date <= week_end,
        ).all()
        quiz_attempts = WeeklyQuizAttempt.query.filter(
            WeeklyQuizAttempt.user_id == user_id,
            WeeklyQuizAttempt.created_at >= datetime.combine(week_start, datetime.min.time()),
            WeeklyQuizAttempt.created_at < datetime.combine(week_end + timedelta(days=1), datetime.min.time()),
        ).all()
        completed = sum(1 for attempt in task_attempts if (attempt.status or "").lower() == "completed")
        quiz_avg = sum((attempt.percentage or 0) for attempt in quiz_attempts) / len(quiz_attempts) if quiz_attempts else 0
        score = min(100, int(completed * 20 + quiz_avg * 0.6))
        weeks.append({"week": f"Week {4 - idx}", "score": score})
    return weeks


def _skill_distribution(user_id: int) -> list[dict]:
    chat_count = ChatHistory.query.filter_by(user_id=user_id).count()
    practice_count = PracticeActivity.query.filter_by(user_id=user_id).count()
    download_count = Download.query.filter_by(user_id=user_id).count()
    quiz_count = WeeklyQuizAttempt.query.filter_by(user_id=user_id).count()
    code_submissions = CodeLabSubmission.query.filter_by(user_id=user_id).count()

    return [
        {"name": "Chats", "value": max(1, chat_count)},
        {"name": "Lab Runs", "value": max(1, code_submissions)},
        {"name": "Practice", "value": max(1, practice_count)},
        {"name": "Quizzes", "value": max(1, quiz_count + download_count)},
    ]


def _earned_badges(user_id: int, wallet: RewardWallet, streak: UserStreak, topic_rows: list[dict]) -> list[dict]:
    chat_count = ChatHistory.query.filter_by(user_id=user_id).count()
    code_count = CodeLabSubmission.query.filter_by(user_id=user_id).count()
    practice_count = PracticeActivity.query.filter_by(user_id=user_id, status="completed").count()
    weekly_best = max(
        [attempt.percentage for attempt in WeeklyQuizAttempt.query.filter_by(user_id=user_id).all() if attempt.percentage is not None],
        default=0.0,
    )

    rules = [
        ("First Steps", "Complete your first task or send your first chat", chat_count + practice_count > 0, "🎯"),
        ("Code Master", "Complete 10 lab runs or practice submissions", code_count >= 10 or practice_count >= 10, "💻"),
        ("Quiz Champion", "Score 90%+ on a weekly quiz", weekly_best >= 90, "🏆"),
        ("Streak Legend", "Maintain a 7-day streak", streak.current_streak >= 7, "🔥"),
        ("Momentum Builder", "Earn 500 XP", wallet.current_xp >= 500, "⚡"),
    ]

    badges = []
    for name, description, earned, icon in rules:
        badges.append(
            {
                "name": name,
                "description": description,
                "earned": bool(earned),
                "icon": icon,
            }
        )
    # include one adaptive badge based on current strongest topic
    if topic_rows:
        badges.append(
            {
                "name": f"{topic_rows[0]['topic']} Explorer",
                "description": f"Show progress in {topic_rows[0]['topic'].lower()} through repeated practice",
                "earned": topic_rows[0]["confidence"] >= 70,
                "icon": "🧠",
            }
        )
    return badges


def _reward_history(user_id: int) -> list[dict]:
    rows = RewardRedemption.query.filter_by(user_id=user_id).order_by(RewardRedemption.created_at.desc()).limit(20).all()
    return [
        {
            "redemption_id": row.redemption_id,
            "reward_key": row.reward_key,
            "reward_name": row.reward_name,
            "cost": row.cost,
            "status": row.status,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


def _reward_catalog(wallet: RewardWallet) -> list[dict]:
    return [
        {
            **item,
            "available": wallet.reward_points >= item["cost"],
        }
        for item in REWARD_CATALOG
    ]


def _reward_redemptions(user_id: int) -> list[dict]:
    rows = RewardRedemption.query.filter_by(user_id=user_id).order_by(RewardRedemption.created_at.desc()).all()
    return [
        {
            "redemption_id": row.redemption_id,
            "reward_key": row.reward_key,
            "reward_name": row.reward_name,
            "cost": row.cost,
            "status": row.status,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


def _serialize_badges(user_id: int, wallet: RewardWallet, streak: UserStreak, topic_rows: list[dict]) -> list[dict]:
    chat_count = ChatHistory.query.filter_by(user_id=user_id).count()
    code_count = CodeLabSubmission.query.filter_by(user_id=user_id).count()
    practice_count = PracticeActivity.query.filter_by(user_id=user_id, status="completed").count()
    weekly_best = max(
        [attempt.percentage for attempt in WeeklyQuizAttempt.query.filter_by(user_id=user_id).all() if attempt.percentage is not None],
        default=0.0,
    )

    badge_map = {
        "activity": chat_count + practice_count > 0,
        "code": code_count >= 10 or practice_count >= 10,
        "quiz": weekly_best >= 90,
        "streak": streak.current_streak >= 7,
        "xp": wallet.current_xp >= 500,
    }

    badges = []
    for item in BADGE_CATALOG:
        badges.append(
            {
                "name": item["name"],
                "description": item["description"],
                "icon": item["icon"],
                "earned": bool(badge_map.get(item["threshold"], False)),
            }
        )

    if topic_rows:
        top_topic = topic_rows[0]["topic"]
        badges.append(
            {
                "name": f"{top_topic} Explorer",
                "description": f"Show progress in {top_topic.lower()} through repeated practice",
                "icon": "🧠",
                "earned": topic_rows[0]["confidence"] >= 70,
            }
        )

    return badges


def _serialize_task(task: DailyTask) -> dict:
    payload = task.content_json or {}
    return {
        "task_id": task.task_id,
        "user_id": task.user_id,
        "title": task.title,
        "description": task.description,
        "task_type": task.task_type,
        "difficulty": task.difficulty,
        "status": task.status,
        "points_reward": task.points_reward,
        "due_date": task.due_date.isoformat(),
        "content": payload,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


def _sync_daily_tasks(user_id: int, profile: UserProfile, today: date) -> list[DailyTask]:
    language = _preferred_language(profile)
    if not language:
        return []
    difficulty = profile.difficulty_level or "beginner"
    desired = build_daily_task_bundle(language, difficulty)
    rows = DailyTask.query.filter_by(user_id=user_id, due_date=today).order_by(DailyTask.task_id.asc()).all()

    if not rows:
        rows = []
        for item in desired:
            row = DailyTask(
                user_id=user_id,
                title=item["title"],
                description=item["description"],
                task_type=item["task_type"],
                difficulty=profile.difficulty_level or "beginner",
                status="assigned",
                points_reward=item["points_reward"],
                content_json=item["content_json"],
                due_date=today,
            )
            db.session.add(row)
            rows.append(row)
        db.session.commit()
        rows = DailyTask.query.filter_by(user_id=user_id, due_date=today).order_by(DailyTask.task_id.asc()).all()
    else:
        changed = False
        for index, row in enumerate(rows):
            if index >= len(desired):
                break
            item = desired[index]
            payload = row.content_json or {}
            should_backfill = (
                not isinstance(payload, dict)
                or payload.get("mode") != item["content_json"].get("mode")
                or not payload
                or row.task_type not in {"code", "quiz"}
            )
            if should_backfill:
                row.title = item["title"]
                row.description = item["description"]
                row.task_type = item["task_type"]
                row.difficulty = difficulty
                row.points_reward = item["points_reward"]
                row.content_json = deepcopy(item["content_json"])
                changed = True
        if changed:
            db.session.commit()
            rows = DailyTask.query.filter_by(user_id=user_id, due_date=today).order_by(DailyTask.task_id.asc()).all()

    # Keep today's tasks stable once created so users see the same set for the full day.
    return rows


@progression_bp.get("/tasks/today")
@jwt_required()
def get_today_tasks():
    user_id = int(get_jwt_identity())
    today = datetime.utcnow().date()

    profile = _ensure_profile(user_id)
    rows = _sync_daily_tasks(user_id, profile, today)

    return jsonify(
        {
            "date": today.isoformat(),
            "tasks": [
                _serialize_task(r)
                for r in rows
            ],
            "preferred_language": _preferred_language(profile),
        }
    )


@progression_bp.get("/tasks/<int:task_id>")
@jwt_required()
def get_daily_task(task_id: int):
    user_id = int(get_jwt_identity())
    row = DailyTask.query.filter_by(task_id=task_id, user_id=user_id).first()
    if not row:
        return jsonify({"error": "task not found"}), 404
    return jsonify(_serialize_task(row))


@progression_bp.post("/tasks/<int:task_id>/submit")
@jwt_required()
def submit_task(task_id: int):
    user_id = int(get_jwt_identity())
    payload = request.get_json() or {}
    submission_text = str(payload.get("submission", "")).strip()
    score = int(payload.get("score", 100))
    answers = payload.get("answers", {})

    row = DailyTask.query.filter_by(task_id=task_id, user_id=user_id).first()
    if not row:
        return jsonify({"error": "task not found"}), 404

    was_completed = row.status == "completed"
    content = row.content_json or {}
    scored_value = max(0, min(score, 100))
    passed = scored_value >= 70

    if row.task_type == "quiz":
        questions = content.get("questions") if isinstance(content, dict) else []
        if isinstance(questions, list) and questions:
            normalized_answers = answers if isinstance(answers, dict) else {}
            correct = 0
            for question in questions:
                qid = str(question.get("id"))
                expected = str(question.get("answer", "")).strip().lower()
                chosen = str(normalized_answers.get(qid, "")).strip().lower()
                if expected and chosen == expected:
                    correct += 1
            scored_value = round((correct / len(questions)) * 100)
            passed = scored_value >= 70
            submission_text = str(normalized_answers)
    row.status = "completed" if passed else "submitted"
    row.updated_at = datetime.utcnow()

    attempt = DailyTaskAttempt(
        task_id=row.task_id,
        user_id=user_id,
        submission_text=submission_text or None,
        score=scored_value,
        status="completed" if passed else "submitted",
    )
    db.session.add(attempt)

    wallet = _ensure_wallet(user_id)
    streak = _ensure_streak(user_id)

    awarded = 0
    if passed and not was_completed:
        awarded = row.points_reward or 20
        wallet = _award_xp(
            user_id=user_id,
            points=awarded,
            source="daily_task",
            source_id=row.task_id,
            meta={"task_type": row.task_type, "difficulty": row.difficulty, "score": scored_value},
        )

    _touch_streak(streak, datetime.utcnow().date())
    db.session.commit()

    return jsonify(
        {
            "message": "task submitted",
            "task_id": row.task_id,
            "status": row.status,
            "passed": passed,
            "score": scored_value,
            "xp_awarded": awarded,
            "wallet": {
                "current_xp": wallet.current_xp,
                "level": wallet.level,
                "reward_points": wallet.reward_points,
            },
            "streak": {
                "current_streak": streak.current_streak,
                "longest_streak": streak.longest_streak,
            },
        }
    )


@progression_bp.get("/quiz/weekly")
@jwt_required()
def get_weekly_quiz():
    user_id = int(get_jwt_identity())
    today = datetime.utcnow().date()
    week_start, week_end = _week_bounds(today)

    profile = _ensure_profile(user_id)
    language = _preferred_language(profile)
    if not language:
        return jsonify({"quiz": None, "attempts": 0, "best_score": 0.0, "message": "preferred language not set"}), 200
    bundle = build_weekly_quiz_bundle(language, profile.difficulty_level or "beginner")
    with db.session.no_autoflush:
        quiz = WeeklyQuiz.query.filter_by(user_id=user_id, week_start=week_start).first()
        if not quiz:
            quiz = WeeklyQuiz(
                user_id=user_id,
                title=f"{bundle['title']} ({_week_key(week_start)})",
                week_start=week_start,
                week_end=week_end,
                difficulty=bundle["difficulty"],
                question_payload=bundle["questions"],
            )
            db.session.add(quiz)
        else:
            payload = quiz.question_payload or []
            if (
                not isinstance(payload, list)
                or len(payload) < len(bundle["questions"])
                or quiz.title != f"{bundle['title']} ({week_start.isocalendar()[0]}-W{week_start.isocalendar()[1]:02d})"
            ):
                quiz.title = f"{bundle['title']} ({week_start.isocalendar()[0]}-W{week_start.isocalendar()[1]:02d})"
                quiz.week_end = week_end
                quiz.difficulty = bundle["difficulty"]
                quiz.question_payload = deepcopy(bundle["questions"])

    db.session.commit()

    attempts = WeeklyQuizAttempt.query.filter_by(user_id=user_id, quiz_id=quiz.quiz_id).order_by(WeeklyQuizAttempt.created_at.desc()).all()
    best_score = max([a.percentage for a in attempts], default=0.0)

    return jsonify(
        {
            "quiz": {
                "quiz_id": quiz.quiz_id,
                "title": quiz.title,
                "week_start": quiz.week_start.isoformat(),
                "week_end": quiz.week_end.isoformat(),
                "difficulty": quiz.difficulty,
                "questions": quiz.question_payload,
                "language": language,
            },
            "attempts": len(attempts),
            "best_score": round(best_score, 2),
        }
    )


@progression_bp.post("/quiz/<int:quiz_id>/submit")
@jwt_required()
def submit_weekly_quiz(quiz_id: int):
    user_id = int(get_jwt_identity())
    payload = request.get_json() or {}
    answers = payload.get("answers", {})

    quiz = WeeklyQuiz.query.filter_by(quiz_id=quiz_id, user_id=user_id).first()
    if not quiz:
        return jsonify({"error": "quiz not found"}), 404

    questions = quiz.question_payload or []
    total = len(questions)
    if total == 0:
        return jsonify({"error": "quiz has no questions"}), 400

    score = 0
    normalized_answers = answers if isinstance(answers, dict) else {}

    for q in questions:
        qid = str(q.get("id"))
        correct = q.get("answer")
        user_answer = str(normalized_answers.get(qid, "")).strip()
        if correct == "open":
            if user_answer:
                score += 1
        elif user_answer.lower() == str(correct).strip().lower():
            score += 1

    percentage = (score / total) * 100

    attempt = WeeklyQuizAttempt(
        quiz_id=quiz.quiz_id,
        user_id=user_id,
        answers_payload=normalized_answers,
        score=score,
        total=total,
        percentage=percentage,
    )
    db.session.add(attempt)

    wallet = _ensure_wallet(user_id)
    streak = _ensure_streak(user_id)

    xp_awarded = 50 if percentage >= 80 else 30 if percentage >= 60 else 15
    wallet = _award_xp(
        user_id=user_id,
        points=xp_awarded,
        source="weekly_quiz",
        source_id=quiz.quiz_id,
        meta={"percentage": round(percentage, 2)},
    )
    _touch_streak(streak, datetime.utcnow().date())

    db.session.commit()

    return jsonify(
        {
            "message": "quiz submitted",
            "quiz_id": quiz.quiz_id,
            "score": score,
            "total": total,
            "percentage": round(percentage, 2),
            "xp_awarded": xp_awarded,
            "wallet": {
                "current_xp": wallet.current_xp,
                "level": wallet.level,
                "reward_points": wallet.reward_points,
            },
            "streak": {
                "current_streak": streak.current_streak,
                "longest_streak": streak.longest_streak,
            },
        }
    )


@progression_bp.get("/rewards/summary")
@jwt_required()
def rewards_summary():
    user_id = int(get_jwt_identity())
    profile = _ensure_profile(user_id)
    wallet = _ensure_wallet(user_id)
    streak = _ensure_streak(user_id)
    topic_rows = _topic_scores(user_id)
    db.session.commit()

    recent_events = (
        XPEvent.query.filter_by(user_id=user_id)
        .order_by(desc(XPEvent.created_at))
        .limit(20)
        .all()
    )

    return jsonify(
        {
            "wallet": {
                "current_xp": wallet.current_xp,
                "level": wallet.level,
                "reward_points": wallet.reward_points,
            },
            "streak": {
                "current_streak": streak.current_streak,
                "longest_streak": streak.longest_streak,
                "last_active_date": streak.last_active_date.isoformat() if streak.last_active_date else None,
            },
            "earned_badges": _serialize_badges(user_id, wallet, streak, topic_rows),
            "reward_vault": _reward_catalog(wallet),
            "reward_redemptions": _reward_redemptions(user_id),
            "learning_style": profile.difficulty_level,
            "recent_xp_events": [
                {
                    "event_id": e.event_id,
                    "source": e.source,
                    "source_id": e.source_id,
                    "points": e.points,
                    "meta": e.meta,
                    "created_at": e.created_at.isoformat(),
                }
                for e in recent_events
            ],
        }
    )


@progression_bp.post("/rewards/redeem")
@jwt_required()
def redeem_reward():
    user_id = int(get_jwt_identity())
    payload = request.get_json() or {}
    reward_key = str(payload.get("reward_key", "")).strip()
    if not reward_key:
        return jsonify({"error": "reward_key is required"}), 400

    reward_item = next((item for item in REWARD_CATALOG if item["reward_key"] == reward_key), None)
    if not reward_item:
        return jsonify({"error": "reward not found"}), 404

    wallet = _ensure_wallet(user_id)
    if wallet.reward_points < reward_item["cost"]:
        return jsonify({"error": "not enough reward points"}), 400

    wallet.reward_points -= reward_item["cost"]
    redemption = RewardRedemption(
        user_id=user_id,
        reward_key=reward_item["reward_key"],
        reward_name=reward_item["name"],
        cost=reward_item["cost"],
        status="redeemed",
    )
    db.session.add(redemption)
    db.session.commit()

    return jsonify(
        {
            "message": "reward redeemed",
            "wallet": {
                "current_xp": wallet.current_xp,
                "level": wallet.level,
                "reward_points": wallet.reward_points,
            },
            "reward": {
                "reward_key": reward_item["reward_key"],
                "reward_name": reward_item["name"],
                "cost": reward_item["cost"],
            },
        }
    )


@progression_bp.get("/leaderboard")
@jwt_required()
def leaderboard():
    user_id = int(get_jwt_identity())
    scope = (request.args.get("scope") or "weekly").strip().lower()
    if scope not in {"weekly", "all_time"}:
        return jsonify({"error": "scope must be weekly or all_time"}), 400

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
        .limit(50)
        .all()
    )

    ranked = []
    my_rank = None
    my_score = 0

    for idx, row in enumerate(rows, start=1):
        user = User.query.get(row.user_id)
        score = int(row.score or 0)
        item = {
            "rank": idx,
            "user_id": row.user_id,
            "name": user.name if user else f"User {row.user_id}",
            "score": score,
        }
        ranked.append(item)
        if row.user_id == user_id:
            my_rank = idx
            my_score = score

    if my_rank is None:
        score_query = db.session.query(func.sum(XPEvent.points)).filter(XPEvent.user_id == user_id)
        if scope == "weekly":
            week_start, _ = _week_bounds(datetime.utcnow().date())
            score_query = score_query.filter(XPEvent.created_at >= datetime.combine(week_start, datetime.min.time()))
        my_score = int(score_query.scalar() or 0)

    return jsonify(
        {
            "scope": scope,
            "rows": ranked,
            "me": {
                "user_id": user_id,
                "rank": my_rank,
                "score": my_score,
            },
        }
    )
