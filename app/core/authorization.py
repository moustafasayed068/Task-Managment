"""
Role-based access control helpers.
"""

from typing import List

from fastapi import Depends, HTTPException, Request, status

from app.core.dependencies import get_current_user
from app.core.logger_core import logger
from app.schemas.user_schemas import CurrentUser


def require_roles(allowed_roles: List[str]):
    def _checker(
        request: Request,
        current_user: CurrentUser = Depends(get_current_user),
    ):
        user_role = current_user.role
        user_username = current_user.username

        if user_role not in allowed_roles:
            client_ip = request.client.host if request.client else "unknown"
            endpoint = request.url.path

            logger.warning(
                "UNAUTHORIZED ACCESS | username={} | role={} | ip={} | endpoint={} | required={}",
                user_username, user_role, client_ip, endpoint, allowed_roles,
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(allowed_roles)}. Your role: '{user_role}'."
            )
        return current_user

    return _checker


def require_admin():
    return require_roles(["admin"])


def require_admin_or_pm():
    return require_roles(["admin", "project_manager"])


def require_any_authenticated():
    return get_current_user