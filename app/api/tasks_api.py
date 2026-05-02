from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session_db import get_db
from app.models.task_models import TaskModel
from app.models.project_models import ProjectModel
from app.models.user_models import UserModel
from app.schemas.task_schemas import TaskCreate, TaskResponse
from app.core.dependencies import get_current_user
from app.core.cache_core import (
    cache_project_by_id,
    cache_user_by_id,
    invalidate_project_cache
)

router = APIRouter()


@cache_project_by_id
def _get_project_by_id(project_id: int, db: Session):
    """Get project from database with caching."""
    return db.query(ProjectModel).filter(ProjectModel.id == project_id).first()


@cache_user_by_id
def _get_user_by_id(user_id: int, db: Session):
    """Get user from database with caching."""
    return db.query(UserModel).filter(UserModel.id == user_id).first()


# Create Task
@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    # Check if project exists (cached)
    project = _get_project_by_id(task.project_id, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if assignee exists (cached)
    assignee = _get_user_by_id(task.assignee_id, db)
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found")
    
    new_task = TaskModel(
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        project_id=task.project_id,
        assignee_id=task.assignee_id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Invalidate project cache after task creation
    invalidate_project_cache()
    
    return new_task


# Get All Tasks
@router.get("/", response_model=list[TaskResponse])
def get_tasks(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    return db.query(TaskModel).all()


# Get Single Task
@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# Update Task
@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.title = task_update.title
    task.description = task_update.description
    task.status = task_update.status
    task.priority = task_update.priority
    task.project_id = task_update.project_id
    task.assignee_id = task_update.assignee_id
    db.commit()
    db.refresh(task)
    
    # Invalidate project cache after update
    invalidate_project_cache()
    
    return task


# Delete Task
@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    
    # Invalidate project cache after deletion
    invalidate_project_cache()
    
    return {"message": "Task deleted successfully"}