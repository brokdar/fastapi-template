"""Dependency injection configuration.

This module defines the dependency factories for services and repositories,
including the auth_service instance created at module level.
"""

from typing import Annotated

from fastapi import Depends

from app.config import get_settings
from app.core.auth.providers.api_key.dependencies import APIKeyDeps
from app.core.auth.providers.api_key.repositories import APIKeyRepository
from app.core.auth.providers.api_key.services import APIKeyService
from app.core.auth.providers.types import ProviderDeps
from app.core.auth.services import AuthService
from app.core.auth.setup import create_auth_service
from app.core.security.hasher import default_api_key_service
from app.core.security.password import default_password_service
from app.db.session import SessionDependency
from app.domains.users.repositories import UserRepository
from app.domains.users.services import UserService

password_service = default_password_service
settings = get_settings()


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

# Build typed provider dependencies
provider_deps: dict[str, ProviderDeps] = {}

if settings.auth.api_key.enabled:
    provider_deps["api_key"] = APIKeyDeps(
        get_api_key_service=get_api_key_service,
    )

# Create auth service at module level (Null Object pattern: always AuthService, may have no providers)
auth_service: AuthService = create_auth_service(
    settings=settings,
    get_user_service=get_user_service,
    provider_deps=provider_deps,
)
