
"""
task_service.py
===============
Business-logic layer for Tasks.
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

VALID_TRANSITIONS: dict[str, set[str]] = {
    "todo": {"in_progress"},
    "in_progress": {"done", "todo"},
    "done": {"in_progress"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_user_info(current_user):
    """
    Supports both:
    - dict users
    - SQLAlchemy user objects
    """

    if isinstance(current_user, dict):
        return {
            "id": current_user.get("id"),
            "role": current_user.get("role"),
        }

    return {
        "id": getattr(current_user, "id", None),
        "role": getattr(current_user, "role", None),
    }


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
    allowed = VALID_TRANSITIONS.get(current, set())

    if requested not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid status transition: '{current}' → '{requested}'. "
                f"Allowed next statuses from '{current}': {sorted(allowed)}."
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
    project = (
        db.query(ProjectModel)
        .filter(ProjectModel.id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id={project_id} not found.",
        )


def _assert_user_exists(db: Session, user_id: int) -> None:
    user = (
        db.query(UserModel)
        .filter(UserModel.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={user_id} not found.",
        )


# ---------------------------------------------------------------------------
# Create Task
# ---------------------------------------------------------------------------

def create_task(
    db: Session,
    payload: TaskCreate,
    current_user,
):
    user = _extract_user_info(current_user)

    _assert_project_exists(db, payload.project_id)

    if payload.status:
        _validate_status(payload.status)

    if payload.priority:
        _validate_priority(payload.priority)

    if payload.assignee_id:
        _assert_user_exists(db, payload.assignee_id)

    task = TaskModel(
        title=payload.title,
        description=payload.description,
        status=payload.status or "todo",
        priority=payload.priority or "medium",
        project_id=payload.project_id,
        assignee_id=payload.assignee_id or user["id"],
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


# ---------------------------------------------------------------------------
# Get All Tasks
# ---------------------------------------------------------------------------

def get_all_tasks(
    db: Session,
    current_user,
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    assignee_id_filter: Optional[int] = None,
):
    user = _extract_user_info(current_user)

    query = db.query(TaskModel)

    # Employee
    if user["role"] == "employee":
        query = query.filter(
            TaskModel.assignee_id == user["id"]
        )

    # Project Manager
    elif user["role"] == "project_manager":
        query = (
            query.join(ProjectModel)
            .filter(ProjectModel.owner_id == user["id"])
        )

        if assignee_id_filter is not None:
            _assert_user_exists(db, assignee_id_filter)

            query = query.filter(
                TaskModel.assignee_id == assignee_id_filter
            )

    # Admin
    else:
        if assignee_id_filter is not None:
            _assert_user_exists(db, assignee_id_filter)

            query = query.filter(
                TaskModel.assignee_id == assignee_id_filter
            )

    # Optional filters
    if status_filter is not None:
        _validate_status(status_filter)

        query = query.filter(
            TaskModel.status == status_filter
        )

    if priority_filter is not None:
        _validate_priority(priority_filter)

        query = query.filter(
            TaskModel.priority == priority_filter
        )

    return query.all()


# ---------------------------------------------------------------------------
# Get Task By ID
# ---------------------------------------------------------------------------

def get_task_by_id(
    db: Session,
    task_id: int,
    current_user,
):
    user = _extract_user_info(current_user)

    task = _get_task_or_404(db, task_id)

    # Employee restriction
    if (
        user["role"] == "employee"
        and task.assignee_id != user["id"]
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees can only view their own tasks.",
        )

    # Project manager restriction
    if user["role"] == "project_manager":
        project = (
            db.query(ProjectModel)
            .filter(ProjectModel.id == task.project_id)
            .first()
        )

        if project and project.owner_id != user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access tasks in your projects.",
            )

    return task


# ---------------------------------------------------------------------------
# Update Task
# ---------------------------------------------------------------------------

def update_task(
    db: Session,
    task_id: int,
    payload: TaskUpdate,
    current_user,
):
    user = _extract_user_info(current_user)

    task = _get_task_or_404(db, task_id)

    # Employee restrictions
    if user["role"] == "employee":

        if task.assignee_id != user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees can only update their own tasks.",
            )

        # Employees can only update status
        restricted_fields = any([
            payload.title is not None,
            payload.description is not None,
            payload.priority is not None,
            payload.assignee_id is not None,
        ])

        if restricted_fields:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees can only update task status.",
            )

        if payload.status is not None:
            _validate_status(payload.status)

            if payload.status != task.status:
                _validate_transition(
                    task.status,
                    payload.status,
                )

            task.status = payload.status

        db.commit()
        db.refresh(task)

        return task

    # Project manager restriction
    if user["role"] == "project_manager":

        project = (
            db.query(ProjectModel)
            .filter(ProjectModel.id == task.project_id)
            .first()
        )

        if project and project.owner_id != user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update tasks in your projects.",
            )

    # Status
    if payload.status is not None:
        _validate_status(payload.status)

        if payload.status != task.status:
            _validate_transition(
                task.status,
                payload.status,
            )

        task.status = payload.status

    # Title
    if payload.title is not None:
        task.title = payload.title

    # Description
    if payload.description is not None:
        task.description = payload.description

    # Priority
    if payload.priority is not None:
        _validate_priority(payload.priority)

        task.priority = payload.priority

    # Assignee
    if payload.assignee_id is not None:
        _assert_user_exists(db, payload.assignee_id)

        task.assignee_id = payload.assignee_id

    db.commit()
    db.refresh(task)

    return task


# ---------------------------------------------------------------------------
# Delete Task
# ---------------------------------------------------------------------------

def delete_task(
    db: Session,
    task_id: int,
    current_user,
):
    user = _extract_user_info(current_user)

    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete tasks.",
        )

    task = _get_task_or_404(db, task_id)

    db.delete(task)
    db.commit()

    return {
        "message": (
            f"Task '{task.title}' "
            f"(id={task_id}) deleted successfully."
        )
    }
