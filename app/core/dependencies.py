from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from sqlalchemy.orm import Session
from app.db.session_db import get_db
from app.models.user_models import UserModel
from app.core.security import decode_token
from app.core.cache_core import cache_user_by_id, invalidate_user_cache

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@cache_user_by_id
def _get_user_from_db(user_id: int, db: Session):
    """Get user from database with caching."""
    return db.query(UserModel).filter(UserModel.id == user_id).first()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = decode_token(token)
        
        if payload is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

    except (JWTError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token")

    user = _get_user_from_db(int(user_id), db)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


def require_role(required_role: str):
    def role_checker(current_user: UserModel = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=403,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker