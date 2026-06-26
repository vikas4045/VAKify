from app.routes.admin import admin_bp
from app.routes.assessment import assessment_bp
from app.routes.ai import ai_bp
from app.routes.auth import auth_bp
from app.routes.chat import chat_bp
from app.routes.dashboard import dashboard_bp
from app.routes.download import download_bp
from app.routes.lab import lab_bp
from app.routes.moderation import moderation_bp
from app.routes.progression import progression_bp
from app.routes.practice import practice_bp
from app.routes.settings import settings_bp
from app.routes.style import style_bp


def register_blueprints(app):
    # Public/auth and learner flows
    app.register_blueprint(auth_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(style_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(practice_bp)
    app.register_blueprint(download_bp)
    app.register_blueprint(lab_bp)
    app.register_blueprint(moderation_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(progression_bp)
    app.register_blueprint(assessment_bp)
    # Admin only
    app.register_blueprint(admin_bp)
