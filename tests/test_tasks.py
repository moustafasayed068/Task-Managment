"""
test_tasks.py
=============
Tests for the v2 role-gated task endpoints:
  POST   /api/v1/v2/tasks/
  GET    /api/v1/v2/tasks/          (with filtering)
  GET    /api/v1/v2/tasks/{id}
  PATCH  /api/v1/v2/tasks/{id}
  DELETE /api/v1/v2/tasks/{id}

Also covers:
  - Task status lifecycle FSM (valid and invalid transitions)
  - Employee field restrictions
  - Filtering by status, priority, assignee_id
"""

import pytest

BASE = "/api/v1/v2/tasks"
PROJ_BASE = "/api/v1/v2/projects"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_task(client, headers, project_id, assignee_id,
               title="Task", status="todo", priority="medium"):
    return client.post(
        BASE + "/",
        json={
            "title": title,
            "description": "desc",
            "status": status,
            "priority": priority,
            "project_id": project_id,
            "assignee_id": assignee_id,
        },
        headers=headers,
    )


# ---------------------------------------------------------------------------
# POST /v2/tasks/
# ---------------------------------------------------------------------------

class TestCreateTask:

    def test_admin_can_create(self, client, admin_headers, sample_project, employee_id):
        r = _make_task(client, admin_headers, sample_project["id"], employee_id)
        assert r.status_code == 201
        assert r.json()["status"] == "todo"

    def test_pm_can_create(self, client, pm_headers, employee_id):
        proj = client.post("/api/v1/v2/projects/", json={"name": "PM Proj", "description": "PM"}, headers=pm_headers).json()
        r = _make_task(client, pm_headers, proj["id"], employee_id)
        assert r.status_code == 201

    def test_employee_cannot_create(self, client, employee_headers, sample_project, employee_id):
        r = _make_task(client, employee_headers, sample_project["id"], employee_id)
        assert r.status_code == 403

    def test_unauthenticated_cannot_create(self, client, sample_project, employee_id):
        r = _make_task(client, {}, sample_project["id"], employee_id)
        assert r.status_code == 401

    def test_nonexistent_project_rejected(self, client, admin_headers, employee_id):
        r = _make_task(client, admin_headers, project_id=9999, assignee_id=employee_id)
        assert r.status_code == 404

    def test_nonexistent_assignee_rejected(self, client, admin_headers, sample_project):
        r = _make_task(client, admin_headers, sample_project["id"], assignee_id=9999)
        assert r.status_code == 404

    def test_new_task_must_start_as_todo(self, client, admin_headers, sample_project, employee_id):
        """Creating a task with status='in_progress' should be rejected."""
        r = _make_task(client, admin_headers, sample_project["id"], employee_id,
                       status="in_progress")
        assert r.status_code == 422

    def test_invalid_priority_rejected(self, client, admin_headers, sample_project, employee_id):
        r = _make_task(client, admin_headers, sample_project["id"], employee_id,
                       priority="ultra")
        assert r.status_code == 422

    def test_missing_title_rejected(self, client, admin_headers, sample_project, employee_id):
        r = client.post(
            BASE + "/",
            json={"project_id": sample_project["id"], "assignee_id": employee_id},
            headers=admin_headers,
        )
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /v2/tasks/  — listing and filtering
# ---------------------------------------------------------------------------

class TestListTasks:

    def test_admin_sees_all_tasks(self, client, admin_headers, sample_task):
        r = client.get(BASE + "/", headers=admin_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_employee_only_sees_own_tasks(
        self, client, admin_headers, employee_headers, other_employee_headers,
        sample_project, employee_id
    ):
        """Create task for employee, another for other_employee; employee should only see theirs."""
        other_resp = client.get("/api/v1/auth/me", headers=other_employee_headers)
        other_id = other_resp.json()["id"]

        _make_task(client, admin_headers, sample_project["id"], employee_id, title="Mine")
        _make_task(client, admin_headers, sample_project["id"], other_id, title="Theirs")

        r = client.get(BASE + "/", headers=employee_headers)
        assert r.status_code == 200
        tasks = r.json()
        for t in tasks:
            assert t["assignee_id"] == employee_id

    def test_filter_by_status(self, client, admin_headers, sample_task):
        r = client.get(BASE + "/?status=todo", headers=admin_headers)
        assert r.status_code == 200
        for t in r.json():
            assert t["status"] == "todo"

    def test_filter_by_invalid_status_rejected(self, client, admin_headers):
        r = client.get(BASE + "/?status=flying", headers=admin_headers)
        assert r.status_code == 422

    def test_filter_by_priority(self, client, admin_headers, sample_project, employee_id):
        _make_task(client, admin_headers, sample_project["id"], employee_id,
                   title="High", priority="high")
        r = client.get(BASE + "/?priority=high", headers=admin_headers)
        assert r.status_code == 200
        for t in r.json():
            assert t["priority"] == "high"

    def test_filter_by_assignee_id(self, client, admin_headers, sample_project, employee_id):
        _make_task(client, admin_headers, sample_project["id"], employee_id)
        r = client.get(f"{BASE}/?assignee_id={employee_id}", headers=admin_headers)
        assert r.status_code == 200
        for t in r.json():
            assert t["assignee_id"] == employee_id

    def test_unauthenticated_cannot_list(self, client):
        r = client.get(BASE + "/")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /v2/tasks/{id}
# ---------------------------------------------------------------------------

class TestGetTask:

    def test_admin_can_get_any_task(self, client, admin_headers, sample_task):
        r = client.get(f"{BASE}/{sample_task['id']}", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["id"] == sample_task["id"]

    def test_employee_can_get_own_task(self, client, employee_headers, sample_task):
        r = client.get(f"{BASE}/{sample_task['id']}", headers=employee_headers)
        assert r.status_code == 200

    def test_employee_cannot_get_others_task(
        self, client, admin_headers, other_employee_headers, sample_project, employee_id
    ):
        """other_employee tries to read a task assigned to employee."""
        task = _make_task(client, admin_headers, sample_project["id"],
                          employee_id, title="Private").json()
        r = client.get(f"{BASE}/{task['id']}", headers=other_employee_headers)
        assert r.status_code == 403

    def test_get_nonexistent_task(self, client, admin_headers):
        r = client.get(f"{BASE}/9999", headers=admin_headers)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /v2/tasks/{id}  — status workflow + field restrictions
# ---------------------------------------------------------------------------

class TestUpdateTask:

    # ── Valid transitions ──────────────────────────────────────────────────

    def test_admin_todo_to_in_progress(self, client, admin_headers, sample_task):
        r = client.patch(
            f"{BASE}/{sample_task['id']}",
            json={"status": "in_progress"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_admin_in_progress_to_done(self, client, admin_headers, sample_task):
        tid = sample_task["id"]
        client.patch(f"{BASE}/{tid}", json={"status": "in_progress"}, headers=admin_headers)
        r = client.patch(f"{BASE}/{tid}", json={"status": "done"}, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "done"

    def test_rollback_done_to_in_progress(self, client, admin_headers, sample_task):
        tid = sample_task["id"]
        client.patch(f"{BASE}/{tid}", json={"status": "in_progress"}, headers=admin_headers)
        client.patch(f"{BASE}/{tid}", json={"status": "done"}, headers=admin_headers)
        r = client.patch(f"{BASE}/{tid}", json={"status": "in_progress"}, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_rollback_in_progress_to_todo(self, client, admin_headers, sample_task):
        tid = sample_task["id"]
        client.patch(f"{BASE}/{tid}", json={"status": "in_progress"}, headers=admin_headers)
        r = client.patch(f"{BASE}/{tid}", json={"status": "todo"}, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "todo"

    # ── Invalid transitions ────────────────────────────────────────────────

    def test_invalid_todo_to_done_directly(self, client, admin_headers, sample_task):
        """Cannot jump from todo directly to done."""
        r = client.patch(
            f"{BASE}/{sample_task['id']}",
            json={"status": "done"},
            headers=admin_headers,
        )
        assert r.status_code == 422

    def test_invalid_done_to_todo_directly(self, client, admin_headers, sample_task):
        """Cannot jump from done back to todo directly."""
        tid = sample_task["id"]
        client.patch(f"{BASE}/{tid}", json={"status": "in_progress"}, headers=admin_headers)
        client.patch(f"{BASE}/{tid}", json={"status": "done"}, headers=admin_headers)
        r = client.patch(f"{BASE}/{tid}", json={"status": "todo"}, headers=admin_headers)
        assert r.status_code == 422

    def test_invalid_status_value(self, client, admin_headers, sample_task):
        r = client.patch(
            f"{BASE}/{sample_task['id']}",
            json={"status": "flying"},
            headers=admin_headers,
        )
        assert r.status_code == 422

    # ── Employee restrictions ──────────────────────────────────────────────

    def test_employee_can_update_own_task_status(self, client, employee_headers, sample_task):
        r = client.patch(
            f"{BASE}/{sample_task['id']}",
            json={"status": "in_progress"},
            headers=employee_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_employee_cannot_change_title(self, client, employee_headers, sample_task):
        r = client.patch(
            f"{BASE}/{sample_task['id']}",
            json={"title": "Hacked Title"},
            headers=employee_headers,
        )
        assert r.status_code == 403

    def test_employee_cannot_change_priority(self, client, employee_headers, sample_task):
        r = client.patch(
            f"{BASE}/{sample_task['id']}",
            json={"priority": "high"},
            headers=employee_headers,
        )
        assert r.status_code == 403

    def test_employee_cannot_reassign_task(
        self, client, employee_headers, other_employee_headers, sample_task
    ):
        other_id = client.get(
            "/api/v1/auth/me", headers=other_employee_headers
        ).json()["id"]
        r = client.patch(
            f"{BASE}/{sample_task['id']}",
            json={"assignee_id": other_id},
            headers=employee_headers,
        )
        assert r.status_code == 403

    def test_employee_cannot_update_others_task(
        self, client, other_employee_headers, sample_task
    ):
        r = client.patch(
            f"{BASE}/{sample_task['id']}",
            json={"status": "in_progress"},
            headers=other_employee_headers,
        )
        assert r.status_code == 403

    # ── Admin / PM full update ─────────────────────────────────────────────

    def test_admin_can_change_title(self, client, admin_headers, sample_task):
        r = client.patch(
            f"{BASE}/{sample_task['id']}",
            json={"title": "New Title"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["title"] == "New Title"

    def test_admin_can_change_priority(self, client, admin_headers, sample_task):
        r = client.patch(
            f"{BASE}/{sample_task['id']}",
            json={"priority": "high"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["priority"] == "high"

    def test_pm_can_reassign_task(
        self, client, pm_headers, employee_id, other_employee_headers
    ):
        proj = client.post("/api/v1/v2/projects/", json={"name": "PM Proj", "description": "PM"}, headers=pm_headers).json()
        task = _make_task(
            client, pm_headers, proj["id"], employee_id, title="Reassign"
        ).json()
        other_id = client.get(
            "/api/v1/auth/me", headers=other_employee_headers
        ).json()["id"]
        r = client.patch(
            f"{BASE}/{task['id']}",
            json={"assignee_id": other_id},
            headers=pm_headers,
        )
        assert r.status_code == 200
        assert r.json()["assignee_id"] == other_id

    def test_update_nonexistent_task(self, client, admin_headers):
        r = client.patch(
            f"{BASE}/9999",
            json={"status": "in_progress"},
            headers=admin_headers,
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /v2/tasks/{id}
# ---------------------------------------------------------------------------

class TestDeleteTask:

    def test_admin_can_delete(self, client, admin_headers, sample_task):
        r = client.delete(f"{BASE}/{sample_task['id']}", headers=admin_headers)
        assert r.status_code == 200
        assert "deleted" in r.json()["message"].lower()

    def test_deleted_task_is_gone(self, client, admin_headers, sample_task):
        tid = sample_task["id"]
        client.delete(f"{BASE}/{tid}", headers=admin_headers)
        r = client.get(f"{BASE}/{tid}", headers=admin_headers)
        assert r.status_code == 404

    def test_pm_cannot_delete(self, client, pm_headers, sample_task):
        r = client.delete(f"{BASE}/{sample_task['id']}", headers=pm_headers)
        assert r.status_code == 403

    def test_employee_cannot_delete(self, client, employee_headers, sample_task):
        r = client.delete(f"{BASE}/{sample_task['id']}", headers=employee_headers)
        assert r.status_code == 403

    def test_delete_nonexistent_task(self, client, admin_headers):
        r = client.delete(f"{BASE}/9999", headers=admin_headers)
        assert r.status_code == 404
