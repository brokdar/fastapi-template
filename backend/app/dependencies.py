from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.core.auth.exceptions import (
    InactiveUserError,
    InsufficientPermissionsError,
    InvalidTokenError,
)
from app.core.auth.services import AuthService
from app.core.auth.tokens import verify_token
from app.core.security.password import default_password_service
from app.db.session import SessionDependency
from app.domains.users.exceptions import UserNotFoundError
from app.domains.users.models import User, UserRole
from app.domains.users.repositories import UserRepository
from app.domains.users.services import UserService

password_service = default_password_service
settings = get_settings()

oauth2_scheme = HTTPBearer()
oauth2_scheme_optional = HTTPBearer(auto_error=False)


def get_user_repository(session: SessionDependency) -> UserRepository:
    """Create UserRepository instance for dependency injection.

    Args:
        session: Database session dependency.

    Returns:
        UserRepository: Repository instance for user operations.
    """
    return UserRepository(session)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(oauth2_scheme)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    """Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Authorization credentials containing JWT token.
        user_repository: Repository for user data access.

    Returns:
        User: Authenticated user.

    Raises:
        InvalidTokenError: If token is invalid or malformed.
        TokenExpiredError: If token has expired.
        UserNotFoundError: If user not found.
        InactiveUserError: If user account is inactive.
    """
    token_payload = verify_token(credentials.credentials, "access")

    user = await user_repository.get_by_id(token_payload.sub)
    if not user:
        raise UserNotFoundError(message="User not found", user_id=token_payload.sub)

    if not user.is_active:
        raise InactiveUserError(user_id=user.id)

    return user


async def get_optional_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(oauth2_scheme_optional)
    ],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> User | None:
    """Get current user if authenticated, otherwise return None.

    Args:
        credentials: Optional HTTP Authorization credentials.
        user_repository: Repository for user data access.

    Returns:
        User | None: Authenticated user or None if not authenticated.

    Raises:
        InvalidTokenError: If token is provided but invalid.
        TokenExpiredError: If token is provided but expired.
        InactiveUserError: If user exists but account is inactive.
    """
    if not credentials:
        return None

    try:
        token_payload = verify_token(credentials.credentials, "access")

        user = await user_repository.get_by_id(token_payload.sub)
        if not user:
            return None

        if not user.is_active:
            raise InactiveUserError(user_id=user.id)

        return user
    except (InvalidTokenError, UserNotFoundError):
        return None


def require_role(required_role: UserRole) -> Callable[[User], User]:
    """Create a dependency that requires a specific user role.

    Args:
        required_role: The role required to access the endpoint.

    Returns:
        Callable: Dependency function that validates user role.

    Example:
        ```python
        @app.get("/admin/dashboard")
        def admin_dashboard(
            user: Annotated[User, Depends(require_role(UserRole.ADMIN))]
        ):
            return {"message": "Welcome to admin dashboard"}
        ```
    """

    def role_checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        """Check if user has required role.

        Args:
            user: Authenticated user.

        Returns:
            User: User with required role.

        Raises:
            InsufficientPermissionsError: If user lacks required role.
        """
        if user.role != required_role:
            raise InsufficientPermissionsError(
                required_role=required_role.value,
                user_role=user.role.value,
            )
        return user

    return role_checker


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


def get_auth_service(
    repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthService:
    """Create AuthService instance for dependency injection.

    Args:
        repository: User repository instance.

    Returns:
        AuthService: Service instance for authentication operations.
    """
    return AuthService(repository, password_service)


RequiresUserDependency = Annotated[User, Depends(get_current_user)]
OptionalUserDependency = Annotated[User | None, Depends(get_optional_user)]
UserServiceDependency = Annotated[UserService, Depends(get_user_service)]
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
