from app import create_app


def _client(tmp_path, monkeypatch):
    db_path = tmp_path / "admin-workspace-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "google-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/google/callback")
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _register(client, email, name):
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


def test_admin_chatbot_and_leaderboard_management(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    admin_token = _register(client, "admin@example.com", "Admin User")
    learner_token = _register(client, "learner@example.com", "Learner User")

    config = client.get(
        "/api/admin/chatbot-config",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert config.status_code == 200
    config_data = config.get_json()
    assert config_data["enabled"] is True
    assert config_data["assistant_name"]

    update = client.put(
        "/api/admin/chatbot-config",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "enabled": False,
            "assistant_name": "Vakify Control",
            "response_style": "direct",
            "max_response_chars": 800,
            "system_prompt": "You are the admin-managed Vakify chatbot.",
        },
    )
    assert update.status_code == 200
    updated_config = update.get_json()["config"]
    assert updated_config["enabled"] is False
    assert updated_config["assistant_name"] == "Vakify Control"

    forbidden = client.get(
        "/api/admin/chatbot-config",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert forbidden.status_code == 403

    leaderboard = client.get(
        "/api/admin/leaderboard",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert leaderboard.status_code == 200
    board_data = leaderboard.get_json()
    assert "weekly" in board_data and "all_time" in board_data

    grant = client.post(
        "/api/admin/users/2/grant-points",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"points": 120, "reason": "leaderboard boost"},
    )
    assert grant.status_code == 200

    refresh = client.post(
        "/api/admin/leaderboard/refresh",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert refresh.status_code == 200

    refreshed = client.get(
        "/api/admin/leaderboard",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert refreshed.status_code == 200
    refreshed_data = refreshed.get_json()
    assert refreshed_data["all_time"]["snapshot_count"] >= 1
    assert refreshed_data["weekly"]["snapshot_count"] >= 1
