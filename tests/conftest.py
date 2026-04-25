"""
conftest.py
===========
Shared pytest fixtures for the entire test suite.

Strategy
--------
- Each test session uses an **in-memory SQLite** database (never touches
  the real task_management.db).
- A fresh database is created per test function via function-scoped fixtures.
- Four ready-to-use authenticated headers are provided:
    admin_headers, pm_headers, employee_headers, other_employee_headers

Usage in tests
--------------
    def test_something(client, admin_headers):
        r = client.get("/api/v1/v2/projects/", headers=admin_headers)
        assert r.status_code == 200
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.base_db import Base
from app.db.session_db import get_db
from app.main import app
from app.core.security import hash_password
from app.models.user_models import UserModel

# ---------------------------------------------------------------------------
# In-memory test database
# ---------------------------------------------------------------------------
TEST_DB_URL = "sqlite:///./test_task_management.db"


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(
        TEST_DB_URL, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=db_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """TestClient with the test DB injected via dependency override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper: register a user and return JWT headers
# ---------------------------------------------------------------------------

def _register_and_login(client: TestClient, db_session: Session, username: str, password: str, role: str) -> dict:
    user = UserModel(
        username=username,
        email=f"{username}@test.com",
        password_hash=hash_password(password),
        role=role
    )
    db_session.add(user)
    db_session.commit()

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Role-based header fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin_headers(client, db_session):
    return _register_and_login(client, db_session, "admin_user", "adminpass", "admin")


@pytest.fixture()
def pm_headers(client, db_session):
    return _register_and_login(client, db_session, "pm_user", "pmpass", "project_manager")


@pytest.fixture()
def employee_headers(client, db_session):
    return _register_and_login(client, db_session, "emp_user", "emppass", "employee")


@pytest.fixture()
def other_employee_headers(client, db_session):
    return _register_and_login(client, db_session, "emp_other", "emppass2", "employee")


# ---------------------------------------------------------------------------
# Convenience: a created project and task
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_project(client, admin_headers):
    """Returns the JSON dict of a newly created project."""
    r = client.post(
        "/api/v1/v2/projects/",
        json={"name": "Alpha Project", "description": "Test project"},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture()
def employee_id(client, employee_headers):
    """Returns the integer user-id of the employee fixture user."""
    r = client.get("/api/v1/auth/me", headers=employee_headers)
    return r.json()["id"]


@pytest.fixture()
def sample_task(client, admin_headers, sample_project, employee_id):
    """Returns the JSON dict of a newly created task assigned to the employee."""
    r = client.post(
        "/api/v1/v2/tasks/",
        json={
            "title": "Alpha Task",
            "description": "Test task",
            "status": "todo",
            "priority": "medium",
            "project_id": sample_project["id"],
            "assignee_id": employee_id,
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()
