"""API Key authentication provider implementation."""

from collections.abc import Callable

import structlog
from fastapi import APIRouter, Request
from fastapi.security import APIKeyHeader
from fastapi.security.base import SecurityBase

from app.core.auth.protocols import AuthenticationUserService
from app.core.auth.providers.api_key.config import APIKeySettings
from app.core.auth.providers.base import AuthProvider
from app.domains.users.exceptions import UserNotFoundError
from app.domains.users.models import User

from .exceptions import APIKeyExpiredError, InvalidAPIKeyError
from .services import APIKeyService

logger = structlog.get_logger("auth.provider.api_key")


class APIKeyProvider(AuthProvider):
    """API Key authentication provider.

    Authenticates requests using API keys passed via X-API-Key header.
    The API key service is retrieved from request.state (set by AuthService).
    """

    name = "api_key"

    def __init__(
        self,
        get_api_key_service: Callable[..., APIKeyService],
        settings: APIKeySettings,
    ) -> None:
        """Initialize API Key provider.

        Args:
            get_api_key_service: Dependency factory for APIKeyService.
            settings: API Key configuration settings.
        """
        self._settings = settings
        self._header_name = settings.header_name
        self._get_api_key_service = get_api_key_service

    def can_authenticate(self, request: Request) -> bool:
        """Check if request has API key header.

        Args:
            request: The incoming HTTP request.

        Returns:
            True if the API key header is present, False otherwise.
        """
        return request.headers.get(self._header_name) is not None

    async def authenticate(
        self, request: Request, user_service: AuthenticationUserService
    ) -> User | None:
        """Authenticate using API key from header.

        Retrieves APIKeyService from request.state.api_key_service (set by AuthService).
        Validates the key, gets user_id, fetches user via user_service.

        Args:
            request: The incoming HTTP request.
            user_service: Service for user authentication operations.

        Returns:
            Authenticated User or None on failure to allow fallback to other providers.
        """
        api_key = request.headers.get(self._header_name)
        if not api_key:
            logger.warning("authentication_failed", reason="missing_api_key")
            return None

        # Get API key service from request state (injected by AuthService)
        api_key_service: APIKeyService | None = getattr(
            request.state, "api_key_service", None
        )
        if api_key_service is None:
            logger.error(
                "authentication_failed", reason="api_key_service_not_in_request_state"
            )
            return None

        try:
            user_id_from_key, key_id = await api_key_service.validate_key(api_key)
        except (InvalidAPIKeyError, APIKeyExpiredError) as e:
            logger.warning("authentication_failed", reason=str(e))
            return None

        try:
            user_id = user_service.parse_id(str(user_id_from_key))
        except (ValueError, TypeError) as e:
            logger.warning(
                "authentication_failed", reason="invalid_user_id", error=str(e)
            )
            return None

        try:
            user = await user_service.get_by_id(user_id)
        except UserNotFoundError:
            logger.warning("authentication_failed", reason="user_not_found")
            return None

        if not user.is_active:
            logger.warning(
                "authentication_failed", reason="inactive_user", user_id=user.id
            )
            return None

        logger.info(
            "authentication_successful",
            user_id=user.id,
            username=user.username,
            key_id=key_id,
        )
        return user

    def get_security_scheme(self) -> SecurityBase:
        """Get FastAPI security scheme for OpenAPI documentation.

        Returns:
            APIKeyHeader security scheme for OpenAPI docs.
        """
        return APIKeyHeader(name=self._header_name, auto_error=False)

    def get_router(self) -> APIRouter:
        """Get FastAPI router with API key management endpoints.

        Returns:
            Router with API key management endpoints.
        """
        # Inline import to avoid circular dependency: router imports provider dependencies
        from app.core.auth.providers.api_key.router import create_api_key_router

        return create_api_key_router(self._get_api_key_service, self._settings)
