"""
test_projects.py
================
Tests for the v2 role-gated project endpoints:
  POST   /api/v1/v2/projects/
  GET    /api/v1/v2/projects/
  GET    /api/v1/v2/projects/{id}
  PUT    /api/v1/v2/projects/{id}
  DELETE /api/v1/v2/projects/{id}

Role matrix tested:
  Create  → admin ✓ | pm ✓ | employee ✗
  Read    → admin ✓ | pm ✓ | employee ✓
  Update  → admin ✓ | pm (owner) ✓ | pm (non-owner) ✗ | employee ✗
  Delete  → admin ✓ | pm ✗ | employee ✗
"""

import pytest

BASE = "/api/v1/v2/projects"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_project(client, headers, name="Test Project"):
    return client.post(BASE + "/", json={"name": name, "description": "desc"}, headers=headers)


# ---------------------------------------------------------------------------
# POST /v2/projects/
# ---------------------------------------------------------------------------

class TestCreateProject:

    def test_admin_can_create(self, client, admin_headers):
        r = create_project(client, admin_headers)
        assert r.status_code == 201
        assert r.json()["name"] == "Test Project"

    def test_pm_can_create(self, client, pm_headers):
        r = create_project(client, pm_headers, name="PM Project")
        assert r.status_code == 201

    def test_employee_cannot_create(self, client, employee_headers):
        r = create_project(client, employee_headers)
        assert r.status_code == 403

    def test_unauthenticated_cannot_create(self, client):
        r = client.post(BASE + "/", json={"name": "No Auth"})
        assert r.status_code == 401

    def test_missing_name_is_rejected(self, client, admin_headers):
        r = client.post(BASE + "/", json={"description": "no name"}, headers=admin_headers)
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /v2/projects/
# ---------------------------------------------------------------------------

class TestListProjects:

    def test_admin_can_list(self, client, admin_headers):
        create_project(client, admin_headers, "P1")
        create_project(client, admin_headers, "P2")
        r = client.get(BASE + "/", headers=admin_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 2

    def test_pm_can_list(self, client, pm_headers):
        r = client.get(BASE + "/", headers=pm_headers)
        assert r.status_code == 200

    def test_employee_can_list(self, client, employee_headers):
        r = client.get(BASE + "/", headers=employee_headers)
        assert r.status_code == 200

    def test_unauthenticated_cannot_list(self, client):
        r = client.get(BASE + "/")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /v2/projects/{id}
# ---------------------------------------------------------------------------

class TestGetProject:

    def test_get_existing_project(self, client, admin_headers, sample_project):
        pid = sample_project["id"]
        r = client.get(f"{BASE}/{pid}", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["id"] == pid

    def test_get_nonexistent_project(self, client, admin_headers):
        r = client.get(f"{BASE}/9999", headers=admin_headers)
        assert r.status_code == 404

    def test_employee_can_read(self, client, employee_headers, sample_project):
        r = client.get(f"{BASE}/{sample_project['id']}", headers=employee_headers)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# PUT /v2/projects/{id}
# ---------------------------------------------------------------------------

class TestUpdateProject:

    def test_admin_can_update_any_project(self, client, admin_headers, sample_project):
        r = client.put(
            f"{BASE}/{sample_project['id']}",
            json={"name": "Updated Name", "description": "updated"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Name"

    def test_pm_can_update_own_project(self, client, pm_headers):
        proj = create_project(client, pm_headers, "PM Owned").json()
        r = client.put(
            f"{BASE}/{proj['id']}",
            json={"name": "PM Updated", "description": "x"},
            headers=pm_headers,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "PM Updated"

    def test_pm_cannot_update_others_project(self, client, admin_headers, pm_headers, sample_project):
        """PM tries to update a project owned by admin."""
        r = client.put(
            f"{BASE}/{sample_project['id']}",
            json={"name": "Hijack", "description": "x"},
            headers=pm_headers,
        )
        assert r.status_code == 403

    def test_employee_cannot_update(self, client, employee_headers, sample_project):
        r = client.put(
            f"{BASE}/{sample_project['id']}",
            json={"name": "Hack", "description": "x"},
            headers=employee_headers,
        )
        assert r.status_code == 403

    def test_update_nonexistent_project(self, client, admin_headers):
        r = client.put(
            f"{BASE}/9999",
            json={"name": "Ghost", "description": "x"},
            headers=admin_headers,
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /v2/projects/{id}
# ---------------------------------------------------------------------------

class TestDeleteProject:

    def test_admin_can_delete(self, client, admin_headers):
        proj = create_project(client, admin_headers, "To Delete").json()
        r = client.delete(f"{BASE}/{proj['id']}", headers=admin_headers)
        assert r.status_code == 200
        assert "deleted" in r.json()["message"].lower()

    def test_deleted_project_is_gone(self, client, admin_headers):
        proj = create_project(client, admin_headers, "Gone").json()
        client.delete(f"{BASE}/{proj['id']}", headers=admin_headers)
        r = client.get(f"{BASE}/{proj['id']}", headers=admin_headers)
        assert r.status_code == 404

    def test_pm_cannot_delete(self, client, pm_headers):
        proj = create_project(client, pm_headers, "PM No Delete").json()
        r = client.delete(f"{BASE}/{proj['id']}", headers=pm_headers)
        assert r.status_code == 403

    def test_employee_cannot_delete(self, client, admin_headers, employee_headers, sample_project):
        r = client.delete(f"{BASE}/{sample_project['id']}", headers=employee_headers)
        assert r.status_code == 403

    def test_delete_nonexistent_project(self, client, admin_headers):
        r = client.delete(f"{BASE}/9999", headers=admin_headers)
        assert r.status_code == 404
