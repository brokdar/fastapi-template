"""JWT authentication service for login and token refresh operations."""

import structlog

from app.core.auth.exceptions import InactiveUserError
from app.core.auth.providers.jwt.schemas import TokenResponse
from app.core.auth.providers.jwt.tokens import (
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.core.security.password import PasswordHasher
from app.domains.users.exceptions import InvalidCredentialsError, UserNotFoundError
from app.domains.users.models import User
from app.domains.users.repositories import UserRepository

logger = structlog.get_logger("auth.jwt")


class JWTAuthService:
    """JWT authentication service handling login and token refresh.

    Attributes:
        user_repository: Repository for user data access.
        password_service: Service for password verification.
        secret_key: Secret key for JWT signing and verification.
        algorithm: JWT signing algorithm.
        access_token_expire_minutes: Access token expiration time in minutes.
        refresh_token_expire_days: Refresh token expiration time in days.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        password_service: PasswordHasher,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
    ) -> None:
        """Initialize JWTAuthService.

        Args:
            user_repository: Repository for user data access.
            password_service: Service for password hashing and verification.
            secret_key: Secret key for JWT signing and verification.
            algorithm: JWT signing algorithm (default: HS256).
            access_token_expire_minutes: Access token expiration in minutes (default: 15).
            refresh_token_expire_days: Refresh token expiration in days (default: 7).
        """
        self.user_repository = user_repository
        self.password_service = password_service
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    async def login(self, username_or_email: str, password: str) -> TokenResponse:
        """Authenticate user and issue JWT tokens.

        Args:
            username_or_email: Username or email address.
            password: Plain text password.

        Returns:
            TokenResponse: Access and refresh tokens.

        Raises:
            InvalidCredentialsError: If credentials are invalid.
            InactiveUserError: If user account is inactive.
        """
        user = await self._get_user_by_identifier(username_or_email)
        self._verify_password(user, password)
        self._check_active(user)

        if user.id is None:
            raise InvalidCredentialsError("User ID is missing")

        access_token = create_access_token(
            user.id,
            user.username,
            user.role,
            self.secret_key,
            self.algorithm,
            self.access_token_expire_minutes,
        )
        refresh_token = create_refresh_token(
            user.id,
            self.secret_key,
            self.algorithm,
            self.refresh_token_expire_days,
        )

        logger.info(
            "User logged in successfully",
            user_id=user.id,
            username=user.username,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """Issue new token pair using refresh token.

        Args:
            refresh_token: Valid refresh token.

        Returns:
            TokenResponse: New access and refresh tokens.

        Raises:
            UserNotFoundError: If user no longer exists.
            InactiveUserError: If user account is inactive.
            InvalidTokenError: If token is invalid.
            TokenExpiredError: If token has expired.
        """
        token_payload = verify_token(
            refresh_token, "refresh", self.secret_key, self.algorithm
        )

        user = await self.user_repository.get_by_id(token_payload.sub)
        if not user:
            raise UserNotFoundError(message="User not found", user_id=token_payload.sub)

        self._check_active(user)

        if user.id is None:
            raise UserNotFoundError(message="User ID is missing", user_id=None)

        access_token = create_access_token(
            user.id,
            user.username,
            user.role,
            self.secret_key,
            self.algorithm,
            self.access_token_expire_minutes,
        )
        new_refresh_token = create_refresh_token(
            user.id,
            self.secret_key,
            self.algorithm,
            self.refresh_token_expire_days,
        )

        logger.info(
            "Tokens refreshed successfully",
            user_id=user.id,
            username=user.username,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )

    async def _get_user_by_identifier(self, identifier: str) -> User:
        """Get user by username or email.

        Args:
            identifier: Username or email address.

        Returns:
            User: Found user.

        Raises:
            InvalidCredentialsError: If user not found.
        """
        user = await self.user_repository.get_by_name(identifier)
        if not user:
            user = await self.user_repository.get_by_mail(identifier)

        if not user:
            logger.warning(
                "Login attempt with invalid identifier", identifier=identifier
            )
            raise InvalidCredentialsError("Invalid username/email or password")

        return user

    def _verify_password(self, user: User, password: str) -> None:
        """Verify user password.

        Args:
            user: User to verify password for.
            password: Plain text password.

        Raises:
            InvalidCredentialsError: If password is incorrect.
        """
        if not self.password_service.verify_password(password, user.hashed_password):
            logger.warning(
                "Login attempt with invalid password",
                user_id=user.id,
                username=user.username,
            )
            raise InvalidCredentialsError("Invalid username/email or password")

    def _check_active(self, user: User) -> None:
        """Check if user account is active.

        Args:
            user: User to check.

        Raises:
            InactiveUserError: If account is inactive.
        """
        if not user.is_active:
            logger.warning(
                "Login attempt for inactive account",
                user_id=user.id,
                username=user.username,
            )
            raise InactiveUserError(user_id=user.id)
