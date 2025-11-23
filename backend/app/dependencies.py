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
from app.domains.users.services import IntUserService

password_service = default_password_service
settings = get_settings()


def get_user_repository(session: SessionDependency) -> UserRepository[int]:
    """Create UserRepository instance for dependency injection.

    Args:
        session: Database session dependency.

    Returns:
        UserRepository[int]: Repository instance for user operations with integer IDs.
    """
    return UserRepository(session)


def get_user_service(
    repository: Annotated[UserRepository[int], Depends(get_user_repository)],
) -> IntUserService:
    """Create IntUserService instance for dependency injection.

    Returns a composed UserService with IntIDMixin, providing integer ID
    parsing capability via Python's Method Resolution Order (MRO).

    Args:
        repository: User repository instance.

    Returns:
        IntUserService: Service instance with integer ID parsing capability.
    """
    return IntUserService(repository, password_service)


def get_api_key_repository(session: SessionDependency) -> APIKeyRepository:
    """Create APIKeyRepository instance for dependency injection."""
    return APIKeyRepository(session)


def get_api_key_service(
    repository: Annotated[APIKeyRepository, Depends(get_api_key_repository)],
) -> APIKeyService:
    """Create APIKeyService instance for dependency injection."""
    return APIKeyService(
        repository=repository,
        hasher=default_api_key_service,
        max_per_user=settings.auth.api_key.max_per_user,
        default_expiration_days=settings.auth.api_key.default_expiration_days,
    )


jwt_provider: JWTAuthProvider[int] = JWTAuthProvider(
    secret_key=settings.auth.jwt.secret_key.get_secret_value(),
    algorithm=settings.auth.jwt.algorithm,
    access_token_expire_minutes=settings.auth.jwt.access_token_expire_minutes,
    refresh_token_expire_days=settings.auth.jwt.refresh_token_expire_days,
)

api_key_provider: APIKeyProvider[int] = APIKeyProvider(
    get_api_key_service=get_api_key_service,
    header_name=settings.auth.api_key.header_name,
)

auth_service: AuthService[int] = AuthService(
    get_user_service=get_user_service,
    providers=[api_key_provider, jwt_provider],  # API key first, JWT fallback
    provider_dependencies={"api_key_service": get_api_key_service},
)

UserServiceDependency = Annotated[IntUserService, Depends(get_user_service)]
APIKeyServiceDependency = Annotated[APIKeyService, Depends(get_api_key_service)]
