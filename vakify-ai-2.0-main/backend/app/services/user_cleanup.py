from pathlib import Path

from app.extensions import db
from app.models import (
    ChatFeedback,
    ChatHistory,
    ChatThread,
    ChatThreadMessage,
    CodeLabSubmission,
    CodeLabTask,
    LabWorkspaceState,
    DailyTask,
    DailyTaskAttempt,
    Download,
    LearningStyle,
    PasswordResetToken,
    PracticeActivity,
    RewardRedemption,
    RewardWallet,
    User,
    UserRoleOverride,
    UserProfile,
    UserStreak,
    WeeklyQuiz,
    WeeklyQuizAttempt,
    XPEvent,
)


def delete_user_with_related_data(user_id: int) -> bool:
    user = User.query.get(user_id)
    if not user:
        return False

    download_rows = Download.query.filter_by(user_id=user_id).all()
    for row in download_rows:
        p = Path(row.file_path)
        if p.exists() and p.is_file():
            try:
                p.unlink()
            except OSError:
                pass

    thread_ids = [row.thread_id for row in ChatThread.query.filter_by(user_id=user_id).all()]
    if thread_ids:
        ChatThreadMessage.query.filter(ChatThreadMessage.thread_id.in_(thread_ids)).delete(synchronize_session=False)
        ChatThread.query.filter(ChatThread.thread_id.in_(thread_ids)).delete(synchronize_session=False)
    ChatHistory.query.filter_by(user_id=user_id).delete()
    ChatFeedback.query.filter_by(user_id=user_id).delete()
    CodeLabSubmission.query.filter_by(user_id=user_id).delete()
    CodeLabTask.query.filter_by(user_id=user_id).delete()
    LabWorkspaceState.query.filter_by(user_id=user_id).delete()
    DailyTask.query.filter_by(user_id=user_id).delete()
    DailyTaskAttempt.query.filter_by(user_id=user_id).delete()
    WeeklyQuiz.query.filter_by(user_id=user_id).delete()
    WeeklyQuizAttempt.query.filter_by(user_id=user_id).delete()
    XPEvent.query.filter_by(user_id=user_id).delete()
    RewardWallet.query.filter_by(user_id=user_id).delete()
    RewardRedemption.query.filter_by(user_id=user_id).delete()
    UserRoleOverride.query.filter_by(user_id=user_id).delete()
    UserProfile.query.filter_by(user_id=user_id).delete()
    UserStreak.query.filter_by(user_id=user_id).delete()
    PracticeActivity.query.filter_by(user_id=user_id).delete()
    Download.query.filter_by(user_id=user_id).delete()
    LearningStyle.query.filter_by(user_id=user_id).delete()
    PasswordResetToken.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    return True
