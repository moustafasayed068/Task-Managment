"""
task_service.py
===============
Business-logic layer for Tasks.

Responsibilities
----------------
- Create a task (admin / project_manager only)
- Retrieve tasks with optional filtering by status, priority, and assignee_id
- Retrieve a single task
- Update a task
    • Admin / project_manager → can change any field (title, description,
      status, priority, assignee)
    • Employee               → can ONLY update the status of their OWN task,
                               and only along valid transitions
- Delete a task (admin only)

Status Lifecycle (enforced for all roles)
------------------------------------------
    todo  ──►  in_progress  ──►  done
                              ◄──  (rollback allowed: done → in_progress)

Invalid transitions raise HTTP 422.
"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project_models import ProjectModel
from app.models.task_models import TaskModel
from app.models.user_models import UserModel
from app.schemas.task_schemas import TaskCreate, TaskUpdate


# ---------------------------------------------------------------------------
# Allowed status values and transition map
# ---------------------------------------------------------------------------

VALID_STATUSES = {"todo", "in_progress", "done"}

# Maps current_status → set of statuses it may transition TO
VALID_TRANSITIONS: dict[str, set[str]] = {
    "todo":        {"in_progress"},
    "in_progress": {"done", "todo"},   # can roll back to todo as well
    "done":        {"in_progress"},    # can reopen
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_task_or_404(db: Session, task_id: int) -> TaskModel:
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id={task_id} not found.",
        )
    return task


def _validate_status(value: str) -> None:
    if value not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid status '{value}'. "
                f"Allowed values: {sorted(VALID_STATUSES)}."
            ),
        )


def _validate_transition(current: str, requested: str) -> None:
    """Raise 422 when the requested transition is not allowed."""
    allowed = VALID_TRANSITIONS.get(current, set())
    if requested not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid status transition: '{current}' → '{requested}'. "
                f"Allowed next statuses from '{current}': {sorted(allowed) or 'none'}."
            ),
        )


def _validate_priority(value: str) -> None:
    valid = {"low", "medium", "high"}
    if value not in valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid priority '{value}'. Allowed: {sorted(valid)}.",
        )


def _assert_project_exists(db: Session, project_id: int) -> None:
    if not db.query(ProjectModel).filter(ProjectModel.id == project_id).first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id={project_id} not found.",
        )


def _assert_user_exists(db: Session, user_id: int) -> None:
    if not db.query(UserModel).filter(UserModel.id == user_id).first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={user_id} not found.",
        )


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

def create_task(
    db: Session,
    payload: TaskCreate,
    current_user: UserModel,
) -> TaskModel:
    """Only admin and project_manager can create tasks."""
    if current_user.role not in ("admin", "project_manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and project managers can create tasks.",
        )

    _assert_project_exists(db, payload.project_id)

    if current_user.role == "project_manager":
        project = db.query(ProjectModel).filter(ProjectModel.id == payload.project_id).first()
        if project and project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Project managers can only create tasks in projects they own.",
            )

    _assert_user_exists(db, payload.assignee_id)

    initial_status = payload.status or "todo"
    _validate_status(initial_status)
    # New tasks must start from "todo"
    if initial_status != "todo":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New tasks must start with status 'todo'.",
        )

    _validate_priority(payload.priority or "medium")

    task = TaskModel(
        title=payload.title,
        description=payload.description,
        status=initial_status,
        priority=payload.priority or "medium",
        project_id=payload.project_id,
        assignee_id=payload.assignee_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_all_tasks(
    db: Session,
    current_user: UserModel,
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    assignee_id_filter: Optional[int] = None,
) -> list[TaskModel]:
    """
    Returns tasks with optional filters.

    Employees only see tasks assigned to them.
    Admins / project_managers see all tasks (then filter if requested).
    """
    query = db.query(TaskModel)

    # ── Role-based scope ──────────────────────────────────────────────────
    if current_user.role == "employee":
        # Employees are scoped to their own tasks regardless of other filters
        query = query.filter(TaskModel.assignee_id == current_user.id)
    elif current_user.role == "project_manager":
        # Project managers only see tasks in their own projects
        query = query.join(ProjectModel).filter(ProjectModel.owner_id == current_user.id)
        if assignee_id_filter is not None:
            _assert_user_exists(db, assignee_id_filter)
            query = query.filter(TaskModel.assignee_id == assignee_id_filter)
    else:
        # Admins: honour optional assignee filter
        if assignee_id_filter is not None:
            _assert_user_exists(db, assignee_id_filter)
            query = query.filter(TaskModel.assignee_id == assignee_id_filter)

    # ── Optional filters ──────────────────────────────────────────────────
    if status_filter is not None:
        _validate_status(status_filter)
        query = query.filter(TaskModel.status == status_filter)

    if priority_filter is not None:
        _validate_priority(priority_filter)
        query = query.filter(TaskModel.priority == priority_filter)

    return query.all()


def get_task_by_id(
    db: Session,
    task_id: int,
    current_user: UserModel,
) -> TaskModel:
    task = _get_task_or_404(db, task_id)

    # Employees can only view tasks assigned to them
    if current_user.role == "employee" and task.assignee_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees can only view their own assigned tasks.",
        )

    # Project managers can only view tasks in their own projects
    if current_user.role == "project_manager":
        project = db.query(ProjectModel).filter(ProjectModel.id == task.project_id).first()
        if project and project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Project managers can only view tasks in projects they own.",
            )

    return task


def update_task(
    db: Session,
    task_id: int,
    payload: TaskUpdate,
    current_user: UserModel,
) -> TaskModel:
    """
    Update logic by role:
    • admin / project_manager → can update all fields + any valid transition
    • employee                → can ONLY change status of their own task,
                                along valid transitions
    """
    task = _get_task_or_404(db, task_id)

    # ── Employee branch ───────────────────────────────────────────────────
    if current_user.role == "employee":
        if task.assignee_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees can only update tasks assigned to them.",
            )
        # Employees are restricted to status changes only
        if any([
            payload.title is not None,
            payload.description is not None,
            payload.priority is not None,
            payload.assignee_id is not None,
        ]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Employees can only change the 'status' field of their tasks. "
                    "Title, description, priority, and assignee changes are restricted."
                ),
            )
        if payload.status is not None:
            _validate_status(payload.status)
            _validate_transition(task.status, payload.status)
            task.status = payload.status

        db.commit()
        db.refresh(task)
        return task

    # ── Admin / project_manager branch ───────────────────────────────────
    if current_user.role == "project_manager":
        project = db.query(ProjectModel).filter(ProjectModel.id == task.project_id).first()
        if project and project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Project managers can only update tasks in projects they own.",
            )

    if payload.status is not None:
        _validate_status(payload.status)
        if payload.status != task.status:
            _validate_transition(task.status, payload.status)
        task.status = payload.status

    if payload.title is not None:
        task.title = payload.title

    if payload.description is not None:
        task.description = payload.description

    if payload.priority is not None:
        _validate_priority(payload.priority)
        task.priority = payload.priority

    if payload.assignee_id is not None:
        _assert_user_exists(db, payload.assignee_id)
        task.assignee_id = payload.assignee_id

    db.commit()
    db.refresh(task)
    return task


def delete_task(
    db: Session,
    task_id: int,
    current_user: UserModel,
) -> dict:
    """Hard delete — admin only (second guard after route-level check)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete tasks.",
        )
    task = _get_task_or_404(db, task_id)
    db.delete(task)
    db.commit()
    return {"message": f"Task '{task.title}' (id={task_id}) deleted successfully."}
