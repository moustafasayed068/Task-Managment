"""
projects_api_v2.py
==================
Project routes with full role-based authorization enforced via
app.core.authorization and delegated to app.services.project_service.

Role matrix
-----------
Endpoint                  | admin | project_manager | employee
--------------------------+-------+-----------------+---------
POST   /v2/projects/      |  ✓    |  ✓ (owns it)    |  ✗
GET    /v2/projects/      |  ✓    |  ✓              |  ✓
GET    /v2/projects/{id}  |  ✓    |  ✓              |  ✓
PUT    /v2/projects/{id}  |  ✓    |  ✓ (owner only) |  ✗
DELETE /v2/projects/{id}  |  ✓    |  ✗              |  ✗
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.authorization import require_admin, require_admin_or_pm, require_any_authenticated
from app.db.session_db import get_db
from app.models.user_models import UserModel
from app.schemas.project_schemas import ProjectCreate, ProjectResponse
from app.services import project_service

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /v2/projects/  — admin or project_manager
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project (Admin / Project Manager only)",
)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_admin_or_pm()),
):
    """
    Create a new project. The authenticated user becomes the owner.

    - **Admin**: unrestricted.
    - **Project Manager**: creates projects; becomes the owner.
    - **Employee**: forbidden (HTTP 403).
    """
    return project_service.create_project(db, payload, current_user)


# ---------------------------------------------------------------------------
# GET /v2/projects/  — all authenticated users
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=list[ProjectResponse],
    summary="List all projects (any authenticated user)",
)
def get_projects(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_any_authenticated()),
):
    """Return the full list of projects. Available to every authenticated role."""
    return project_service.get_all_projects(db)


# ---------------------------------------------------------------------------
# GET /v2/projects/{project_id}  — all authenticated users
# ---------------------------------------------------------------------------
@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get a single project by ID (any authenticated user)",
)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_any_authenticated()),
):
    """Retrieve a project by its ID. Available to every authenticated role."""
    return project_service.get_project_by_id(db, project_id)


# ---------------------------------------------------------------------------
# PUT /v2/projects/{project_id}  — admin or project_manager (owner)
# ---------------------------------------------------------------------------
@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a project (Admin / Project Manager who owns it)",
)
def update_project(
    project_id: int,
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_admin_or_pm()),
):
    """
    Update project name / description.

    - **Admin**: can update any project.
    - **Project Manager**: can update only the projects they own.
    - **Employee**: forbidden (HTTP 403).
    """
    return project_service.update_project(db, project_id, payload, current_user)


# ---------------------------------------------------------------------------
# DELETE /v2/projects/{project_id}  — admin only
# ---------------------------------------------------------------------------
@router.delete(
    "/{project_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a project (Admin only)",
)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_admin()),
):
    """
    Permanently delete a project.

    - **Admin**: can delete any project.
    - **Project Manager / Employee**: forbidden (HTTP 403).
    """
    return project_service.delete_project(db, project_id, current_user)
