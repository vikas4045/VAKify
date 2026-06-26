from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.ai_learning_service import build_ai_study_plan


ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


@ai_bp.get("/study-plan")
@jwt_required()
def study_plan():
    user_id = int(get_jwt_identity())
    plan = build_ai_study_plan(user_id)
    if plan.get("error"):
        return jsonify(plan), int(plan.get("status") or 503)
    return jsonify(plan)
