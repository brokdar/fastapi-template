"""JWT authentication provider implementation."""

import structlog
from fastapi import APIRouter, Request
from fastapi.security import HTTPBearer
from fastapi.security.base import SecurityBase

from app.core.auth.exceptions import InvalidTokenError, TokenExpiredError
from app.core.auth.providers.base import AuthProvider
from app.core.auth.providers.jwt.tokens import verify_token
from app.domains.users.models import User
from app.domains.users.repositories import UserRepository

logger = structlog.get_logger("auth.jwt.provider")


class JWTAuthProvider(AuthProvider):
    """JWT Bearer token authentication provider.

    Stateless provider that authenticates users by extracting and validating
    JWT tokens from the Authorization header (Bearer scheme).

    User repository is injected per-request to ensure fresh database sessions
    and proper request scoping.

    Attributes:
        secret_key: Secret key for JWT signing and verification.
        algorithm: JWT signing algorithm (default: HS256).
        access_token_expire_minutes: Access token expiration time in minutes.
        refresh_token_expire_days: Refresh token expiration time in days.
    """

    name = "jwt"

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
    ) -> None:
        """Initialize JWT authentication provider.

        Args:
            secret_key: Secret key for JWT signing and verification.
            algorithm: JWT signing algorithm (default: HS256).
            access_token_expire_minutes: Access token expiration in minutes (default: 15).
            refresh_token_expire_days: Refresh token expiration in days (default: 7).
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def can_authenticate(self, request: Request) -> bool:
        """Check if request contains JWT Bearer token.

        Args:
            request: FastAPI request object.

        Returns:
            True if Authorization header with Bearer scheme is present.
        """
        auth_header = request.headers.get("Authorization")
        return bool(auth_header and auth_header.startswith("Bearer "))

    async def authenticate(
        self, request: Request, user_repository: UserRepository
    ) -> User | None:
        """Extract JWT from Authorization header and validate.

        Args:
            request: FastAPI request object.
            user_repository: Injected repository for user data access.

        Returns:
            User | None: Authenticated user if valid token, None if provider
                cannot handle this request.
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.removeprefix("Bearer ")

        try:
            payload = verify_token(token, "access", self.secret_key, self.algorithm)
            user = await user_repository.get_by_id(payload.sub)

            if not user or not user.is_active:
                logger.warning(
                    "JWT authentication failed",
                    reason="user_not_found_or_inactive",
                    user_id=payload.sub,
                )
                return None

            logger.debug(
                "JWT authentication successful",
                user_id=user.id,
                username=user.username,
            )
            return user

        except (InvalidTokenError, TokenExpiredError) as e:
            logger.debug("JWT authentication failed", reason=str(e))
            return None

    def get_security_scheme(self) -> SecurityBase:
        """Return HTTPBearer security scheme for OpenAPI documentation.

        Returns:
            HTTPBearer security scheme for Swagger UI.
        """
        return HTTPBearer()

    def get_router(self) -> APIRouter:
        """Return JWT authentication routes.

        Returns:
            APIRouter: Router with /login and /refresh endpoints.
        """
        from app.core.auth.providers.jwt.endpoints import router

        return router
