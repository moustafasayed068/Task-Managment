"""
authorization.py
================
Role-based access control helpers.

Roles defined in the project:
  - "admin"           → full access (manage projects, tasks, users)
  - "project_manager" → assign / monitor tasks; create & update projects
  - "employee"        → update only their OWN assigned tasks (status only)

Usage in routes:
    current_user: UserModel = Depends(require_admin())
    current_user: UserModel = Depends(require_admin_or_pm())
    current_user: UserModel = Depends(require_roles(["admin", "project_manager"]))
"""

from typing import List

from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.models.user_models import UserModel


# ---------------------------------------------------------------------------
# Generic helper — accepts any of the listed roles
# ---------------------------------------------------------------------------

def require_roles(allowed_roles: List[str]):
    """
    Returns a FastAPI dependency that passes only when the authenticated
    user's role is one of *allowed_roles*.

    Example::

        @router.delete("/{id}")
        def delete_something(
            id: int,
            current_user: UserModel = Depends(require_roles(["admin"]))
        ):
            ...
    """

    def _checker(current_user: UserModel = Depends(get_current_user)) -> UserModel:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Required role(s): {', '.join(allowed_roles)}. "
                    f"Your role: '{current_user.role}'."
                ),
            )
        return current_user

    return _checker


# ---------------------------------------------------------------------------
# Convenience shortcuts
# ---------------------------------------------------------------------------

def require_admin():
    """Only 'admin' role is allowed."""
    return require_roles(["admin"])


def require_admin_or_pm():
    """'admin' or 'project_manager' roles are allowed."""
    return require_roles(["admin", "project_manager"])


def require_any_authenticated():
    """Any logged-in user (all roles). Just validates the JWT."""
    return get_current_user
