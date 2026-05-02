"""
test_auth.py
============
Tests for:
  POST /api/v1/auth/register
  POST /api/v1/auth/login
  GET  /api/v1/auth/me
"""

import pytest


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegister:

    def test_register_success(self, client):
        r = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@test.com",
                "password": "secret123",
                "role": "employee",
            },
        )
        assert r.status_code == 201
        assert "message" in r.json()

    def test_register_default_role_is_user(self, client):
        """Registering without a role should default to 'user'."""
        r = client.post(
            "/api/v1/auth/register",
            json={"username": "norole", "email": "norole@test.com", "password": "pass"},
        )
        assert r.status_code == 201

    def test_register_duplicate_username(self, client):
        payload = {"username": "dup", "email": "dup@test.com", "password": "pass"}
        client.post("/api/v1/auth/register", json=payload)
        # Second registration with same username
        r = client.post(
            "/api/v1/auth/register",
            json={"username": "dup", "email": "dup2@test.com", "password": "pass"},
        )
        # Should be HTTP 400 Bad Request
        assert r.status_code == 400
        assert "already registered" in r.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        r = client.post(
            "/api/v1/auth/register",
            json={"username": "bademail", "email": "not-an-email", "password": "pass"},
        )
        assert r.status_code == 422  # Pydantic validation error


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLogin:

    def test_login_success(self, client):
        client.post(
            "/api/v1/auth/register",
            json={"username": "loginuser", "email": "login@test.com",
                  "password": "pass123", "role": "employee"},
        )
        r = client.post(
            "/api/v1/auth/login",
            data={"username": "loginuser", "password": "pass123"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        client.post(
            "/api/v1/auth/register",
            json={"username": "loginuser2", "email": "login2@test.com",
                  "password": "pass123", "role": "employee"},
        )
        r = client.post(
            "/api/v1/auth/login",
            data={"username": "loginuser2", "password": "wrongpass"},
        )
        assert r.status_code == 401

    def test_login_nonexistent_user(self, client):
        r = client.post(
            "/api/v1/auth/login",
            data={"username": "ghost", "password": "nopass"},
        )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# /me endpoint
# ---------------------------------------------------------------------------

class TestMe:

    def test_get_me_authenticated(self, client, employee_headers):
        r = client.get("/api/v1/auth/me", headers=employee_headers)
        assert r.status_code == 200
        body = r.json()
        assert "id" in body
        assert "username" in body
        assert "role" in body

    def test_get_me_unauthenticated(self, client):
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 401

    def test_get_me_bad_token(self, client):
        r = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer this.is.garbage"},
        )
        assert r.status_code == 401
