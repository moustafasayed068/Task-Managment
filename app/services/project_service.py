"""
project_service.py
==================
Business-logic layer for Projects.

Responsibilities
----------------
- Create a project (owner = current user)
- Retrieve all projects / single project
- Update a project — only the owner, a project_manager, or an admin may do so
- Delete a project — admin-only (enforced at route level, but guard repeated here)
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project_models import ProjectModel
from app.models.user_models import UserModel
from app.schemas.project_schemas import ProjectCreate


# ---------------------------------------------------------------------------
# Internal guard helpers
# ---------------------------------------------------------------------------

def _get_project_or_404(db: Session, project_id: int) -> ProjectModel:
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id={project_id} not found.",
        )
    return project


def _assert_can_modify(project: ProjectModel, current_user: UserModel) -> None:
    """Admin and project_manager can always modify; employees cannot."""
    if current_user.role == "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees are not allowed to modify projects.",
        )
    # Owner check for project_manager (they must own the project)
    if current_user.role == "project_manager" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project managers can only modify projects they own.",
        )


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

def create_project(db: Session, payload: ProjectCreate, current_user: UserModel) -> ProjectModel:
    """Admin and project_manager can create projects."""
    if current_user.role not in ("admin", "project_manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and project managers can create projects.",
        )

    project = ProjectModel(
        name=payload.name,
        description=payload.description,
        owner_id=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_all_projects(db: Session) -> list[ProjectModel]:
    """All authenticated users can read projects."""
    return db.query(ProjectModel).all()


def get_project_by_id(db: Session, project_id: int) -> ProjectModel:
    """All authenticated users can read a single project."""
    return _get_project_or_404(db, project_id)


def update_project(
    db: Session,
    project_id: int,
    payload: ProjectCreate,
    current_user: UserModel,
) -> ProjectModel:
    project = _get_project_or_404(db, project_id)
    _assert_can_modify(project, current_user)

    project.name = payload.name
    project.description = payload.description
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int, current_user: UserModel) -> dict:
    """Hard delete — admin only (second guard after route-level check)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete projects.",
        )
    project = _get_project_or_404(db, project_id)
    db.delete(project)
    db.commit()
    return {"message": f"Project '{project.name}' (id={project_id}) deleted successfully."}
