"""
Role-based access control helpers.

Roles:
  - "admin"           → full access
  - "project_manager" → assign / monitor tasks; create & update projects
  - "employee"        → update only their own assigned tasks
"""

from typing import List

from fastapi import Depends, HTTPException, Request, status

from app.core.dependencies import get_current_user
from app.core.logger_core import logger
from app.models.user_models import UserModel


def require_roles(allowed_roles: List[str]):
    def _checker(
        request: Request,
        current_user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        if current_user.role not in allowed_roles:
            client_ip = request.client.host if request.client else "unknown"
            endpoint  = request.url.path

            logger.warning(
                "UNAUTHORIZED ACCESS | username={} | role={} | ip={} "
                "| endpoint={} | required={}",
                current_user.username, current_user.role,
                client_ip, endpoint, allowed_roles,
            )

            # Synchronous email — guaranteed to send before the 403 response
            from app.services.email_service import send_unauthorized_access_alert
            send_unauthorized_access_alert(
                username=current_user.username,
                ip_address=client_ip,
                role=current_user.role,
                endpoint=endpoint,
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Required role(s): {', '.join(allowed_roles)}. "
                    f"Your role: '{current_user.role}'."
                ),
            )
        return current_user

    return _checker


def require_admin():
    return require_roles(["admin"])


def require_admin_or_pm():
    return require_roles(["admin", "project_manager"])


def require_any_authenticated():
    return get_current_user