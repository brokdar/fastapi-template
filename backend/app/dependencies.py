"""Dependency injection configuration.

This module defines the dependency factories for services and repositories.
Authentication providers are now configured via setup_authentication() in main.py.

The auth_service variable is populated by setup_authentication() at app startup.
Endpoints can still use:
    from app.dependencies import auth_service
    user: User = Depends(auth_service.require_user)
"""

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends

from app.config import get_settings
from app.core.auth.providers.api_key.repositories import APIKeyRepository
from app.core.auth.providers.api_key.services import APIKeyService
from app.core.security.hasher import default_api_key_service
from app.core.security.password import default_password_service
from app.db.session import SessionDependency
from app.domains.users.repositories import UserRepository
from app.domains.users.services import UserService

if TYPE_CHECKING:
    from app.core.auth.services import AuthService

password_service = default_password_service
settings = get_settings()

# Auth service - populated by setup_authentication() at app startup
# This allows existing code to continue using:
#   from app.dependencies import auth_service
#   user: User = Depends(auth_service.require_user)
auth_service: "AuthService | None" = None


def get_auth_service() -> "AuthService":
    """Get the auth service, raising if not initialized.

    This function provides proper type narrowing for mypy and should be used
    in contexts where auth_service must be available (e.g., endpoint definitions).

    Returns:
        The initialized AuthService instance.

    Raises:
        RuntimeError: If auth_service has not been initialized.
    """
    if auth_service is None:
        raise RuntimeError(
            "auth_service not initialized. Ensure setup_authentication() "
            "has been called before accessing auth_service."
        )
    return auth_service


def get_user_repository(session: SessionDependency) -> UserRepository:
    """Create UserRepository instance for dependency injection.

    Args:
        session: Database session dependency.

    Returns:
        Repository instance for user operations.
    """
    return UserRepository(session)


def get_user_service(
    repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    """Create UserService instance for dependency injection.

    Returns a composed UserService with IntIDMixin, providing integer ID
    parsing capability via Python's Method Resolution Order (MRO).

    Args:
        repository: User repository instance.

    Returns:
        Service instance with integer ID parsing capability.
    """
    return UserService(repository, password_service)


def get_api_key_repository(session: SessionDependency) -> APIKeyRepository:
    """Create APIKeyRepository instance for dependency injection.

    Args:
        session: Database session dependency.

    Returns:
        Repository instance for API key operations.
    """
    return APIKeyRepository(session)


def get_api_key_service(
    repository: Annotated[APIKeyRepository, Depends(get_api_key_repository)],
) -> APIKeyService:
    """Create APIKeyService instance for dependency injection.

    Args:
        repository: API key repository instance.

    Returns:
        Service instance for API key operations.
    """
    return APIKeyService(
        repository=repository,
        hasher=default_api_key_service,
        max_per_user=settings.auth.api_key.max_per_user,
        default_expiration_days=settings.auth.api_key.default_expiration_days,
    )


# Type aliases for dependency injection
UserServiceDependency = Annotated[UserService, Depends(get_user_service)]
APIKeyServiceDependency = Annotated[APIKeyService, Depends(get_api_key_service)]
