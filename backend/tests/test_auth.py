"""
Integration tests for /api/auth routes.

- POST /api/auth/login
- GET  /api/auth/me
- POST /api/auth/change-password
"""

from app.models.models import User
from app.services.auth_service import hash_password

# ── Helpers ───────────────────────────────────────────────────────────────────


def _seed_user(db, username="alice", password="alicepass"):
    user = User(
        username=username,
        hashed_password=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── POST /api/auth/login ──────────────────────────────────────────────────────


class TestLogin:
    def test_login_success(self, client, db):
        _seed_user(db)
        resp = client.post("/api/auth/login", json={"username": "alice", "password": "alicepass"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "alice"
        assert data["is_active"] is True
        assert "pilotarr_token" in resp.cookies

    def test_login_wrong_password(self, client, db):
        _seed_user(db)
        resp = client.post("/api/auth/login", json={"username": "alice", "password": "wrongpass"})
        assert resp.status_code == 401

    def test_login_unknown_user(self, client, db):
        resp = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
        assert resp.status_code == 401

    def test_login_inactive_user(self, client, db):
        user = _seed_user(db)
        user.is_active = False
        db.commit()
        resp = client.post("/api/auth/login", json={"username": "alice", "password": "alicepass"})
        assert resp.status_code == 401


# ── GET /api/auth/me ──────────────────────────────────────────────────────────


class TestMe:
    def test_me_authenticated(self, auth_client):
        resp = auth_client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["is_active"] is True

    def test_me_unauthenticated(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401  # No cookie → 401 Unauthorized


# ── POST /api/auth/change-password ────────────────────────────────────────────


class TestChangePassword:
    def test_change_password_success(self, auth_client):
        resp = auth_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "testpass",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123",
            },
        )
        assert resp.status_code == 204

    def test_change_password_actually_persisted(self, client, auth_client):
        """New password must work on next login — old password must be rejected."""
        auth_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "testpass",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123",
            },
        )
        # Old password must no longer work
        resp_old = client.post("/api/auth/login", json={"username": "testuser", "password": "testpass"})
        assert resp_old.status_code == 401

        # New password must work
        resp_new = client.post("/api/auth/login", json={"username": "testuser", "password": "newpassword123"})
        assert resp_new.status_code == 200

    def test_change_password_wrong_current(self, auth_client):
        resp = auth_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "wrongpass",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123",
            },
        )
        assert resp.status_code == 400

    def test_change_password_too_short(self, auth_client):
        resp = auth_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "testpass",
                "new_password": "short",
                "confirm_password": "short",
            },
        )
        assert resp.status_code == 422

    def test_change_password_mismatch_confirm(self, auth_client):
        resp = auth_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "testpass",
                "new_password": "newpassword123",
                "confirm_password": "different123",
            },
        )
        assert resp.status_code == 422
