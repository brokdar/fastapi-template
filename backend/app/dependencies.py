from typing import Annotated

from fastapi import Depends

from app.config import get_settings
from app.core.auth.providers.jwt.provider import JWTAuthProvider
from app.core.auth.providers.jwt.service import JWTAuthService
from app.core.auth.services import AuthService
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
        UserRepository: Repository instance for user operations.
    """
    return UserRepository(session)


def get_user_service(
    repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    """Create UserService instance for dependency injection.

    Args:
        repository: User repository instance.

    Returns:
        UserService: Service instance for user operations.
    """
    return UserService(repository, password_service)


jwt_provider = JWTAuthProvider(
    secret_key=settings.AUTH.JWT_SECRET_KEY.get_secret_value(),
    algorithm=settings.AUTH.JWT_ALGORITHM,
    access_token_expire_minutes=settings.AUTH.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    refresh_token_expire_days=settings.AUTH.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
)

auth_service = AuthService(
    get_user_repository=get_user_repository,
    providers=[jwt_provider],
)


def get_jwt_auth_service(
    repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> JWTAuthService:
    """Create JWTAuthService instance for login/refresh endpoints.

    Args:
        repository: User repository instance.

    Returns:
        JWTAuthService: JWT-specific authentication service for login/refresh.
    """
    return JWTAuthService(
        user_repository=repository,
        password_service=password_service,
        secret_key=settings.AUTH.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.AUTH.JWT_ALGORITHM,
        access_token_expire_minutes=settings.AUTH.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days=settings.AUTH.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
    )


UserServiceDependency = Annotated[UserService, Depends(get_user_service)]
JWTAuthServiceDependency = Annotated[JWTAuthService, Depends(get_jwt_auth_service)]
