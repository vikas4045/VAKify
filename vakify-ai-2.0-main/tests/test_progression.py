from app import create_app
from app.extensions import db
from app.models import DailyTask, WeeklyQuiz


def _client(tmp_path, monkeypatch):
    db_path = tmp_path / "progression-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("MODERATOR_EMAILS", "moderator@example.com")
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
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


def test_language_aware_daily_and_weekly_progression(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    token = _register(client, "progression@example.com", "Progression Learner")

    profile_update = client.put(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "preferred_language": "python",
            "learning_level": "beginner",
        },
    )
    assert profile_update.status_code == 200

    seeded_me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert seeded_me.status_code == 200

    today = client.get(
        "/api/tasks/today",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert today.status_code == 200
    today_data = today.get_json()
    assert today_data["preferred_language"] == "python"
    assert len(today_data["tasks"]) == 2

    code_task = next(task for task in today_data["tasks"] if task["task_type"] == "code")
    quiz_task = next(task for task in today_data["tasks"] if task["task_type"] == "quiz")
    assert code_task["content"]["mode"] == "code"
    assert quiz_task["content"]["mode"] == "quiz"
    assert len(quiz_task["content"]["questions"]) == 5

    second_today = client.get(
        "/api/tasks/today",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second_today.status_code == 200
    second_today_data = second_today.get_json()
    assert [task["task_id"] for task in second_today_data["tasks"]] == [task["task_id"] for task in today_data["tasks"]]
    assert second_today_data["tasks"][0]["content"] == today_data["tasks"][0]["content"]

    quiz_answers = {
        str(question["id"]): question["answer"]
        for question in quiz_task["content"]["questions"]
    }
    quiz_submit = client.post(
        f"/api/tasks/{quiz_task['task_id']}/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": quiz_answers},
    )
    assert quiz_submit.status_code == 200
    quiz_result = quiz_submit.get_json()
    assert quiz_result["passed"] is True
    assert quiz_result["xp_awarded"] > 0

    code_submit = client.post(
        f"/api/tasks/{code_task['task_id']}/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "submission": code_task["content"]["starter_code"],
            "score": 90,
        },
    )
    assert code_submit.status_code == 200
    code_result = code_submit.get_json()
    assert code_result["passed"] is True
    assert code_result["xp_awarded"] > 0

    weekly = client.get(
        "/api/quiz/weekly",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert weekly.status_code == 200
    weekly_data = weekly.get_json()
    assert weekly_data["quiz"]["language"] == "python"
    assert len(weekly_data["quiz"]["questions"]) == 7
    assert all("answer" in question for question in weekly_data["quiz"]["questions"])

    second_weekly = client.get(
        "/api/quiz/weekly",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second_weekly.status_code == 200
    second_weekly_data = second_weekly.get_json()
    assert second_weekly_data["quiz"]["quiz_id"] == weekly_data["quiz"]["quiz_id"]
    assert second_weekly_data["quiz"]["questions"] == weekly_data["quiz"]["questions"]

    weekly_answers = {
        str(question["id"]): question["answer"]
        for question in weekly_data["quiz"]["questions"]
    }
    weekly_submit = client.post(
        f"/api/quiz/{weekly_data['quiz']['quiz_id']}/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": weekly_answers},
    )
    assert weekly_submit.status_code == 200
    weekly_result = weekly_submit.get_json()
    assert weekly_result["percentage"] == 100
    assert weekly_result["xp_awarded"] > 0

    rewards = client.get(
        "/api/rewards/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rewards.status_code == 200
    rewards_data = rewards.get_json()
    assert rewards_data["earned_badges"]
    assert rewards_data["reward_vault"]
    assert rewards_data["reward_redemptions"] == []
    assert rewards_data["wallet"]["reward_points"] >= quiz_result["xp_awarded"] + code_result["xp_awarded"] + weekly_result["xp_awarded"]

    insights = client.get(
        "/api/dashboard/insights",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert insights.status_code == 200
    insights_data = insights.get_json()
    assert insights_data["topic_confidence"]
    assert insights_data["learning_style_breakdown"]
    assert insights_data["weak_topics"]
    assert insights_data["performance_over_time"]
    assert insights_data["skill_distribution"]


def test_progression_backfills_stale_saved_rows(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    token = _register(client, "backfill@example.com", "Backfill Learner")

    client.put(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "preferred_language": "python",
            "learning_level": "beginner",
        },
    )

    first_today = client.get(
        "/api/tasks/today",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first_today.status_code == 200
    today_data = first_today.get_json()
    quiz_task = next(task for task in today_data["tasks"] if task["task_type"] == "quiz")
    assert len(quiz_task["content"]["questions"]) == 5

    with client.application.app_context():
        for task in DailyTask.query.filter_by(user_id=1).all():
            task.content_json = None
            task.task_type = "conceptual"
            task.title = "Broken Task"
            task.description = "Broken"
        quiz = WeeklyQuiz.query.filter_by(user_id=1).first()
        if quiz:
            quiz.question_payload = []
            quiz.title = "Broken Weekly Quiz"
        db.session.commit()

    healed_today = client.get(
        "/api/tasks/today",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert healed_today.status_code == 200
    healed_data = healed_today.get_json()
    healed_quiz = next(task for task in healed_data["tasks"] if task["task_type"] == "quiz")
    healed_code = next(task for task in healed_data["tasks"] if task["task_type"] == "code")
    assert len(healed_quiz["content"]["questions"]) == 5
    assert healed_code["content"]["mode"] == "code"

    weekly = client.get(
        "/api/quiz/weekly",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert weekly.status_code == 200
    weekly_data = weekly.get_json()
    assert len(weekly_data["quiz"]["questions"]) == 7


def test_training_workspace_persists_draft_and_run_state(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    token = _register(client, "workspace@example.com", "Workspace Learner")

    saved = client.put(
        "/api/lab/workspace",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "workspace_type": "training",
            "language": "python",
            "code": "print('hello from db')",
            "stdin": "12\n",
            "last_status": "draft",
        },
    )
    assert saved.status_code == 200

    loaded = client.get(
        "/api/lab/workspace?workspace_type=training&language=python",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert loaded.status_code == 200
    loaded_data = loaded.get_json()["workspace"]
    assert loaded_data["code"] == "print('hello from db')"
    assert loaded_data["stdin"] == "12\n"

    run = client.post(
        "/api/lab/run",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "language": "python",
            "source_code": "print('hello from db')",
            "stdin": "12\n",
        },
    )
    assert run.status_code == 200
    run_data = run.get_json()
    assert "stdout" in run_data

    persisted = client.get(
        "/api/lab/workspace?workspace_type=training&language=python",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert persisted.status_code == 200
    persisted_data = persisted.get_json()["workspace"]
    assert persisted_data["code"] == "print('hello from db')"
    assert persisted_data["stdin"] == "12\n"
    assert persisted_data["last_output"] != ""


def test_admin_role_override_and_reward_redemption(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    admin_token = _register(client, "admin@example.com", "Admin User")
    learner_token = _register(client, "role@example.com", "Role Learner")

    role_update = client.put(
        "/api/admin/users/2/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "moderator", "reason": "needs moderation access"},
    )
    assert role_update.status_code == 200

    learner_me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert learner_me.status_code == 200
    assert learner_me.get_json()["role"] == "moderator"

    grant = client.post(
        "/api/admin/users/2/grant-points",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"points": 600, "reason": "reward points for testing"},
    )
    assert grant.status_code == 200

    rewards_before = client.get(
        "/api/rewards/summary",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert rewards_before.status_code == 200
    before_data = rewards_before.get_json()
    redeemable = next(item for item in before_data["reward_vault"] if item["available"])
    redeem = client.post(
        "/api/rewards/redeem",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"reward_key": redeemable["reward_key"]},
    )
    assert redeem.status_code == 200
    redeem_data = redeem.get_json()
    assert redeem_data["reward"]["reward_key"] == redeemable["reward_key"]

    rewards_after = client.get(
        "/api/rewards/summary",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert rewards_after.status_code == 200
    after_data = rewards_after.get_json()
    assert after_data["reward_redemptions"]
    assert after_data["wallet"]["reward_points"] < before_data["wallet"]["reward_points"]
