from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session_db import get_db
from app.models.project_models import ProjectModel
from app.schemas.project_schemas import ProjectCreate, ProjectResponse
from app.core.dependencies import get_current_user
from app.models.user_models import UserModel

router = APIRouter()


# Create Project
@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    new_project = ProjectModel(
        name=project.name,
        description=project.description,
        owner_id=current_user.id
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


# Get All Projects
@router.get("/", response_model=list[ProjectResponse])
def get_projects(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    return db.query(ProjectModel).all()


# Get Single Project
@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# Update Project
@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_update: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.name = project_update.name
    project.description = project_update.description
    db.commit()
    db.refresh(project)
    return project


# Delete Project
@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}