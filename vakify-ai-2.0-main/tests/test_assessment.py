from app import create_app
from app.models import LearningStyle, UserProfile


def _client(tmp_path, monkeypatch):
    db_path = tmp_path / "assessment-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "google-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/google/callback")
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _register(client, email, name="Learner"):
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "secret123",
            "display_name": name,
        },
    )
    assert response.status_code == 200
    return response.get_json()["access_token"]


def test_assessment_questions_and_submission(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    token = _register(client, "assessment@example.com", "Assessment Learner")

    public_questions = client.get("/api/assessment/questions")
    assert public_questions.status_code == 200
    public_questions_data = public_questions.get_json()
    assert len(public_questions_data["questions"]) == 20

    questions = client.get(
        "/api/assessment/questions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert questions.status_code == 200
    questions_data = questions.get_json()
    assert len(questions_data["questions"]) == 20
    assert questions_data["saved"] is False

    answers = {question["id"]: 0 for question in questions_data["questions"]}
    submit = client.post(
        "/api/assessment/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "answers": answers,
        },
    )
    assert submit.status_code == 200
    submit_data = submit.get_json()
    assert submit_data["assessment"]["learning_style"] == "visual"
    assert submit_data["assessment"]["visual_score"] == 20
    assert submit_data["assessment"]["auditory_score"] == 0
    assert submit_data["assessment"]["kinesthetic_score"] == 0

    complete = client.post(
        "/api/auth/onboarding/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Assessment Learner",
            "email": "assessment@example.com",
            "preferred_language": "python",
            "phone_number": "555-0101",
            "other_details": {"goal": "build apps"},
        },
    )
    assert complete.status_code == 200
    complete_data = complete.get_json()
    assert complete_data["user"]["onboarded"] is True
    assert complete_data["user"]["preferredLanguage"] == "python"
    assert complete_data["user"]["phoneNumber"] == "555-0101"

    app = client.application
    with app.app_context():
        style = LearningStyle.query.first()
        profile = UserProfile.query.first()
        assert style is not None
        assert style.learning_style == "visual"
        assert profile is not None
        assert profile.preferred_languages == ["python"]
        assert profile.onboarding_completed_at is not None
