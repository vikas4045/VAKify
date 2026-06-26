from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request

from app.extensions import db
from app.models import LearningStyle, UserProfile
from app.services.assessment_service import get_assessment_questions, score_assessment


assessment_bp = Blueprint("assessment", __name__, url_prefix="/api/assessment")


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
        db.session.flush()
    return profile


@assessment_bp.get("/questions")
def assessment_questions():
    user_id = None
    try:
        verify_jwt_in_request(optional=True)
        raw_identity = get_jwt_identity()
        user_id = int(raw_identity) if raw_identity is not None else None
    except Exception:
        user_id = None

    if user_id is not None:
        style = db.session.get(LearningStyle, user_id)
        if style:
            questions = get_assessment_questions(None)
            return jsonify(
                {
                    "questions": questions,
                    "total_questions": len(questions),
                    "saved": True,
                    "assessment": {
                        "learning_style": style.learning_style,
                        "visual_score": style.visual_score,
                        "auditory_score": style.auditory_score,
                        "kinesthetic_score": style.kinesthetic_score,
                    },
                }
            )

    questions = get_assessment_questions(None)
    return jsonify(
        {
            "questions": questions,
            "total_questions": len(questions),
            "saved": False,
        }
    )


@assessment_bp.post("/submit")
@jwt_required()
def submit_assessment():
    user_id = int(get_jwt_identity())
    payload = request.get_json() or {}
    answers = payload.get("answers", {})
    if not isinstance(answers, dict):
        return jsonify({"error": "answers must be an object"}), 400

    scoring = score_assessment(None, answers)
    profile = _ensure_profile(user_id)
    profile.difficulty_level = "beginner"
    profile.visual_weight = max(0.05, scoring["visual_score"] / max(1, scoring["total"]))
    profile.auditory_weight = max(0.05, scoring["auditory_score"] / max(1, scoring["total"]))
    profile.kinesthetic_weight = max(0.05, scoring["kinesthetic_score"] / max(1, scoring["total"]))
    profile.topic_mastery_json = {
        "weak_topics": [
            f"{topic.title()} Learning Practice"
            for topic in scoring["weak_topics"]
        ],
        "assessment": {
            "learning_style": scoring["learning_style"],
            "percentage": scoring["percentage"],
            "visual_score": scoring["visual_score"],
            "auditory_score": scoring["auditory_score"],
            "kinesthetic_score": scoring["kinesthetic_score"],
            "total": scoring["total"],
        },
    }

    style = db.session.get(LearningStyle, user_id)
    if style and not style.learning_style:
        style.learning_style = scoring["learning_style"]
    if not style:
        style = LearningStyle(
            user_id=user_id,
            learning_style=scoring["learning_style"],
            visual_score=scoring["visual_score"],
            auditory_score=scoring["auditory_score"],
            kinesthetic_score=scoring["kinesthetic_score"],
        )
        db.session.add(style)
    else:
        style.learning_style = scoring["learning_style"]
        style.visual_score = scoring["visual_score"]
        style.auditory_score = scoring["auditory_score"]
        style.kinesthetic_score = scoring["kinesthetic_score"]

    db.session.commit()

    return jsonify(
        {
            "message": "assessment saved",
            "assessment": {
                "learning_style": scoring["learning_style"],
                "visual_score": scoring["visual_score"],
                "auditory_score": scoring["auditory_score"],
                "kinesthetic_score": scoring["kinesthetic_score"],
                "total": scoring["total"],
                "percentage": scoring["percentage"],
                "recommended_level": scoring["recommended_level"],
                "weak_topics": scoring["weak_topics"],
            },
        }
    )
