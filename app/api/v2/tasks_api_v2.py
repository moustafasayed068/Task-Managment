"""
tasks_api_v2.py
===============
Task routes with full role-based authorization + workflow validation,
delegated to app.services.task_service.

Role matrix
-----------
Endpoint                     | admin | project_manager | employee
-----------------------------+-------+-----------------+-----------------------------
POST   /v2/tasks/            |  ✓    |  ✓              |  ✗
GET    /v2/tasks/            |  ✓    |  ✓ (all tasks)  |  ✓ (own tasks only)
GET    /v2/tasks/{id}        |  ✓    |  ✓              |  ✓ (own task only)
PATCH  /v2/tasks/{id}        |  ✓    |  ✓ (any field)  |  ✓ (status of own task)
DELETE /v2/tasks/{id}        |  ✓    |  ✗              |  ✗

Filtering (GET /v2/tasks/)
--------------------------
  ?status=todo|in_progress|done
  ?priority=low|medium|high
  ?assignee_id=<int>          (ignored for employees — always scoped to self)

Workflow Validation (all roles)
--------------------------------
  todo  ──►  in_progress  ──►  done
                            ◄──  (rollback: done → in_progress or in_progress → todo)
  Invalid transitions → HTTP 422
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import require_admin, require_admin_or_pm, require_any_authenticated
from app.core.dependencies import get_current_user
from app.db.session_db import get_db
from app.models.user_models import UserModel
from app.schemas.task_schemas import TaskCreate, TaskResponse, TaskUpdate
from app.services import task_service

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /v2/tasks/  — admin or project_manager
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task (Admin / Project Manager only)",
)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_admin_or_pm()),
):
    """
    Create a new task. The task is placed in the **'todo'** status by default
    (any other initial status is rejected).

    - **Admin / Project Manager**: can create tasks in any project.
    - **Employee**: forbidden (HTTP 403).
    """
    return task_service.create_task(db, payload, current_user)


# ---------------------------------------------------------------------------
# GET /v2/tasks/  — all authenticated users (with filtering)
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=list[TaskResponse],
    summary="List tasks with optional filters (role-scoped)",
)
def get_tasks(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_any_authenticated()),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by task status: todo | in_progress | done",
    ),
    priority_filter: Optional[str] = Query(
        default=None,
        alias="priority",
        description="Filter by priority: low | medium | high",
    ),
    assignee_id: Optional[int] = Query(
        default=None,
        description="Filter by assignee user ID (Admin/PM only; ignored for employees)",
    ),
):
    """
    Return tasks with optional filters.

    - **Employee**: always scoped to their own tasks; `assignee_id` param is ignored.
    - **Admin / Project Manager**: see all tasks; optional `assignee_id` filter applies.
    """
    return task_service.get_all_tasks(
        db,
        current_user,
        status_filter=status_filter,
        priority_filter=priority_filter,
        assignee_id_filter=assignee_id,
    )


# ---------------------------------------------------------------------------
# GET /v2/tasks/{task_id}  — all authenticated users (role-scoped)
# ---------------------------------------------------------------------------
@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a single task by ID (role-scoped)",
)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_any_authenticated()),
):
    """
    Retrieve a task by ID.

    - **Employee**: can only view tasks assigned to them (HTTP 403 otherwise).
    - **Admin / Project Manager**: can view any task.
    """
    return task_service.get_task_by_id(db, task_id, current_user)


# ---------------------------------------------------------------------------
# PATCH /v2/tasks/{task_id}  — all authenticated users (field-restricted by role)
# ---------------------------------------------------------------------------
@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update a task (field restrictions apply per role)",
)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_any_authenticated()),
):
    """
    Update a task. The allowed fields depend on the caller's role:

    | Field       | Admin | Project Manager | Employee          |
    |-------------|-------|-----------------|-------------------|
    | title       | ✓     | ✓               | ✗ (403)           |
    | description | ✓     | ✓               | ✗ (403)           |
    | priority    | ✓     | ✓               | ✗ (403)           |
    | assignee_id | ✓     | ✓               | ✗ (403)           |
    | status      | ✓     | ✓               | ✓ (own task only) |

    Status transitions are validated for **all roles**:
    `todo → in_progress → done` (rollbacks also allowed).
    Invalid transitions return HTTP 422.
    """
    return task_service.update_task(db, task_id, payload, current_user)


# ---------------------------------------------------------------------------
# DELETE /v2/tasks/{task_id}  — admin only
# ---------------------------------------------------------------------------
@router.delete(
    "/{task_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a task (Admin only)",
)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_admin()),
):
    """
    Permanently delete a task.

    - **Admin**: can delete any task.
    - **Project Manager / Employee**: forbidden (HTTP 403).
    """
    return task_service.delete_task(db, task_id, current_user)
