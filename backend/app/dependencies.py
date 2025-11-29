from typing import Annotated

from fastapi import Depends

from app.config import get_settings
from app.core.auth.providers.api_key.provider import APIKeyProvider
from app.core.auth.providers.api_key.repositories import APIKeyRepository
from app.core.auth.providers.api_key.services import APIKeyService
from app.core.auth.providers.jwt.provider import JWTAuthProvider
from app.core.auth.services import AuthService
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


jwt_provider: JWTAuthProvider = JWTAuthProvider(
    secret_key=settings.auth.jwt.secret_key.get_secret_value(),
    algorithm=settings.auth.jwt.algorithm,
    access_token_expire_minutes=settings.auth.jwt.access_token_expire_minutes,
    refresh_token_expire_days=settings.auth.jwt.refresh_token_expire_days,
)

api_key_provider: APIKeyProvider = APIKeyProvider(
    get_api_key_service=get_api_key_service,
    header_name=settings.auth.api_key.header_name,
)

auth_service: AuthService = AuthService(
    get_user_service=get_user_service,
    providers=[api_key_provider, jwt_provider],  # API key first, JWT fallback
    provider_dependencies={"api_key_service": get_api_key_service},
)

UserServiceDependency = Annotated[UserService, Depends(get_user_service)]
APIKeyServiceDependency = Annotated[APIKeyService, Depends(get_api_key_service)]
