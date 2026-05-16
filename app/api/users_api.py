from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session_db import get_db
from app.models.user_models import UserModel
from app.schemas.user_schemas import CurrentUser
from app.core.dependencies import get_current_user, require_role

router = APIRouter()


# get current logged user
@router.get("/me")
def get_me(current_user: CurrentUser = Depends(get_current_user)):
    return current_user


# get all users (for dropdowns)
@router.get("/")
def get_users(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    users = db.query(UserModel).all()
    return [{"id": u.id, "username": u.username, "role": u.role} for u in users]


# delete user (admin only)
@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}