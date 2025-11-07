"""FastAPI dependencies for authentication and authorization.

This module re-exports auth dependencies from app.dependencies for backward compatibility.
All dependency factories are centralized in app.dependencies.
"""

from app.dependencies import (
    OptionalUserDependency,
    RequiresUserDependency,
    get_current_user,
    get_optional_user,
    oauth2_scheme,
    oauth2_scheme_optional,
    require_role,
)

__all__ = [
    "RequiresUserDependency",
    "OptionalUserDependency",
    "get_current_user",
    "get_optional_user",
    "require_role",
    "oauth2_scheme",
    "oauth2_scheme_optional",
]
