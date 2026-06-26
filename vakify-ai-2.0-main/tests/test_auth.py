from app import create_app


def _client(tmp_path, monkeypatch):
    db_path = tmp_path / "auth-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "google-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/google/callback")
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_register_login_and_me(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    register = client.post(
        "/api/auth/register",
        json={
            "email": "learner@example.com",
            "password": "secret123",
            "display_name": "Learner",
        },
    )
    assert register.status_code == 200
    register_data = register.get_json()
    assert register_data["user"]["email"] == "learner@example.com"
    assert register_data["user"]["onboarded"] is False

    login = client.post(
        "/api/auth/login",
        json={
            "email": "learner@example.com",
            "password": "secret123",
        },
    )
    assert login.status_code == 200
    token = login.get_json()["access_token"]

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    me_data = me.get_json()
    assert me_data["email"] == "learner@example.com"
    assert me_data["displayName"] == "Learner"


def test_login_rejects_bad_password(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    client.post(
        "/api/auth/register",
        json={
            "email": "learner@example.com",
            "password": "secret123",
            "display_name": "Learner",
        },
    )

    login = client.post(
        "/api/auth/login",
        json={
            "email": "learner@example.com",
            "password": "wrongpass",
        },
    )
    assert login.status_code == 401


def test_google_config_and_exchange(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    config = client.get("/api/auth/google/config")
    assert config.status_code == 200
    assert config.get_json()["client_id"] == "google-client-id"

    from app.routes import auth as auth_routes

    class FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    def fake_post(url, data=None, timeout=None):
        assert url == auth_routes.GOOGLE_TOKEN_URL
        return FakeResponse(200, {"id_token": "google-id-token"})

    def fake_get(url, params=None, timeout=None):
        assert url == auth_routes.GOOGLE_TOKENINFO_URL
        return FakeResponse(
            200,
            {
                "email": "google@example.com",
                "name": "Google Learner",
                "aud": "google-client-id",
            },
        )

    monkeypatch.setattr(auth_routes.requests, "post", fake_post)
    monkeypatch.setattr(auth_routes.requests, "get", fake_get)

    exchange = client.post(
        "/api/auth/google/exchange",
        json={
            "code": "fake-code",
            "redirect_uri": "http://localhost:5173/auth/google/callback",
        },
    )
    assert exchange.status_code == 200
    data = exchange.get_json()
    assert data["user"]["email"] == "google@example.com"
    assert data["user"]["displayName"] == "Google Learner"
