"""Role-Based Access Control (RBAC) for the application.

Defines user roles and permission dependencies for API endpoints.
Three roles are supported:
  - admin: Full access to all resources and users
  - editor: Can create, edit, and delete own resources
  - viewer: Read-only access to own resources
"""

import enum
import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from backend.app.api.deps import get_current_user
from backend.app.models.user import User

logger = logging.getLogger(__name__)


class UserRole(enum.StrEnum):
    """User role enumeration."""

    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


# Permission hierarchy: admin > editor > viewer
_ROLE_HIERARCHY = {
    UserRole.ADMIN: 3,
    UserRole.EDITOR: 2,
    UserRole.VIEWER: 1,
}


def _get_role_level(role: str) -> int:
    """Return numeric level for a role string.

    Args:
        role: Role string value.

    Returns:
        Numeric role level (higher = more permissions).
    """
    try:
        return _ROLE_HIERARCHY[UserRole(role)]
    except (ValueError, KeyError):
        return 0


def require_role(minimum_role: UserRole) -> Callable[..., User]:
    """Create a FastAPI dependency that enforces a minimum role.

    Args:
        minimum_role: The minimum role required to access the endpoint.

    Returns:
        A FastAPI dependency function.
    """

    def _role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Check that the current user has sufficient role.

        Args:
            current_user: The authenticated user.

        Returns:
            The user if authorized.

        Raises:
            HTTPException 403: If user's role is insufficient.
        """
        user_role = getattr(current_user, "role", UserRole.EDITOR.value)
        user_level = _get_role_level(user_role)
        required_level = _ROLE_HIERARCHY[minimum_role]

        if user_level < required_level:
            logger.warning(
                "Access denied for user %s (role=%s, required=%s)",
                current_user.id,
                user_role,
                minimum_role.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {minimum_role.value}",
            )

        return current_user

    return _role_checker


def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """FastAPI dependency that requires admin role.

    Args:
        current_user: The authenticated user.

    Returns:
        The user if admin.

    Raises:
        HTTPException 403: If user is not admin.
    """
    user_role = getattr(current_user, "role", UserRole.EDITOR.value)
    if user_role != UserRole.ADMIN.value and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
