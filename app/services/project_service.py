"""
project_service.py
==================
Business-logic layer for Projects.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project_models import ProjectModel
from app.models.task_models import TaskModel
from app.models.user_models import UserModel
from app.schemas.project_schemas import ProjectCreate


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_project_or_404(db: Session, project_id: int) -> ProjectModel:
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id={project_id} not found.",
        )
    return project


def _get_user_role(current_user):
    """Safely extract role whether current_user is model or dict"""
    if isinstance(current_user, dict):
        return current_user.get("role")
    return getattr(current_user, "role", None)


def _get_user_id(current_user):
    """Safely extract id whether current_user is model or dict"""
    if isinstance(current_user, dict):
        return current_user.get("id")
    return getattr(current_user, "id", None)


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

def create_project(db: Session, payload: ProjectCreate, current_user) -> ProjectModel:
    """Admin and project_manager can create projects."""
    user_role = _get_user_role(current_user)

    if user_role not in ("admin", "project_manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and project managers can create projects.",
        )

    project = ProjectModel(
        name=payload.name,
        description=payload.description,
        owner_id=_get_user_id(current_user),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_all_projects(db: Session):
    return db.query(ProjectModel).all()


def get_project_by_id(db: Session, project_id: int):
    return _get_project_or_404(db, project_id)


def update_project(db: Session, project_id: int, payload: ProjectCreate, current_user):
    project = _get_project_or_404(db, project_id)
    # Add ownership/permission logic here if needed
    project.name = payload.name
    project.description = payload.description
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int, current_user) -> dict:
    """Hard delete — admin only."""
    user_role = _get_user_role(current_user)

    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete projects.",
        )

    project = _get_project_or_404(db, project_id)

    # Check if project has tasks
    task_count = db.query(TaskModel).filter(TaskModel.project_id == project_id).count()
    if task_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete project. It still contains {task_count} task(s). Delete tasks first."
        )

    project_name = project.name
    db.delete(project)
    db.commit()

    return {"message": f"Project '{project_name}' (id={project_id}) deleted successfully."}