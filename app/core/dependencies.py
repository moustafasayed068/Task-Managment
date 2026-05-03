from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from sqlalchemy.orm import Session
from app.db.session_db import get_db
from app.models.user_models import UserModel
from app.core.security import decode_token
from app.core.cache_core import cache_user_by_id, invalidate_user_cache
from app.core.logger_core import logger

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
    def role_checker(
        request: Request,
        current_user: UserModel = Depends(get_current_user),
    ):
        if current_user.role != required_role:
            client_ip = request.client.host if request.client else "unknown"
            endpoint  = request.url.path

            logger.warning(
                "UNAUTHORIZED ACCESS | username={} | role={} | ip={} "
                "| endpoint={} | required_role={}",
                current_user.username, current_user.role,
                client_ip, endpoint, required_role,
            )

            # Synchronous email alert for unauthorized access
            from app.services.email_service import send_unauthorized_access_alert
            send_unauthorized_access_alert(
                username=current_user.username,
                ip_address=client_ip,
                role=current_user.role,
                endpoint=endpoint,
            )

            raise HTTPException(
                status_code=403,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker