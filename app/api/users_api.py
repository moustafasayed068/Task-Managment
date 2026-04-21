from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session_db import get_db
from app.models.user_models import UserModel
from app.core.dependencies import get_current_user, require_role

router = APIRouter()


# get current logged user
@router.get("/me")
def get_me(current_user: UserModel = Depends(get_current_user)):
    return current_user


# delete user (admin only)
@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: UserModel = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}