import os

from app.extensions import db
from app.models import User, UserRoleOverride


def is_admin_email(email: str) -> bool:
    if not email:
        return False
    allowlist = [item.strip().lower() for item in os.getenv("ADMIN_EMAILS", "").split(",") if item.strip()]
    return email.strip().lower() in allowlist


def is_moderator_email(email: str) -> bool:
    if not email:
        return False
    allowlist = [item.strip().lower() for item in os.getenv("MODERATOR_EMAILS", "").split(",") if item.strip()]
    return email.strip().lower() in allowlist


def get_role_for_email(email: str) -> str:
    if not email:
        return "learner"

    user = User.query.filter(User.email == email.strip().lower()).first()
    if user:
        override = db.session.get(UserRoleOverride, user.user_id)
        if override and override.role in {"learner", "moderator", "admin"}:
            return override.role

    if is_admin_email(email):
        return "admin"
    if is_moderator_email(email):
        return "moderator"
    return "learner"
