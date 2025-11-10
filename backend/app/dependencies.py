from typing import Annotated

from fastapi import Depends

from app.config import get_settings
from app.core.auth.providers.jwt.provider import JWTAuthProvider
from app.core.auth.services import AuthService
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


jwt_provider: JWTAuthProvider[int] = JWTAuthProvider(
    secret_key=settings.AUTH.JWT_SECRET_KEY.get_secret_value(),
    algorithm=settings.AUTH.JWT_ALGORITHM,
    access_token_expire_minutes=settings.AUTH.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    refresh_token_expire_days=settings.AUTH.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
)

auth_service: AuthService[int] = AuthService(
    get_user_service=get_user_service,
    providers=[jwt_provider],
)


UserServiceDependency = Annotated[IntUserService, Depends(get_user_service)]
