from typing import Protocol

from fastapi import APIRouter, Request
from fastapi.security.base import SecurityBase

from app.domains.users.models import User
from app.domains.users.services import UserService


class AuthProvider(Protocol):
    """Protocol for authentication providers.

    Providers own their complete authentication workflow including:
    - Login/logout endpoints (via get_router())
    - Request authentication logic
    - Session/token management
    - Response formatting (JSON tokens, cookies, etc.)

    Providers are tried in the order they are registered in AuthService.
    The first provider where can_authenticate() returns True will be used.
    """

    name: str

    def can_authenticate(self, request: Request) -> bool:
        """Check if this provider can authenticate the given request.

        This method performs a fast check to determine if the request contains
        credentials that this provider can handle (e.g., Bearer token, session
        cookie, API key header). This allows efficient provider selection without
        attempting full authentication on every provider.

        Examples:
        - JWT: Check for "Authorization: Bearer" header
        - Session: Check for session cookie
        - OAuth: Check if path matches callback URL

        Args:
            request: FastAPI request object

        Returns:
            True if this provider can attempt authentication, False otherwise
        """
        ...

    async def authenticate(
        self, request: Request, user_service: UserService
    ) -> User | None:
        """Extract and validate credentials from request.

        This method should:
        1. Check if request contains credentials (cookie, bearer token, etc.)
        2. Validate credentials using the injected user_repository
        3. Return User if valid, None if missing/invalid

        The user_service is injected per-request by the AuthService, ensuring
        fresh database sessions and proper request scoping.

        Should NOT raise exceptions for invalid credentials—return None instead.
        Exceptions should only be raised for system errors.

        Args:
            request: FastAPI request object
            user_service: Injected service for user data access

        Returns:
            User if authenticated, None otherwise
        """
        ...

    def get_security_scheme(self) -> SecurityBase:
        """Return FastAPI security scheme for OpenAPI documentation.

        Examples:
        - HTTPBearer() for JWT
        - APIKeyCookie(name="session_id") for sessions

        Returns:
            SecurityBase instance for OpenAPI spec
        """
        ...

    def get_router(self) -> APIRouter:
        """Return router with login/logout endpoints.

        The router should define provider-specific endpoints:
        - POST /login - Returns provider-specific response (JSON/cookies)
        - POST /logout - Clears authentication state
        - (Optional) POST /refresh - For token refresh
        - (Optional) GET /callback - For OAuth flows

        Returns:
            APIRouter with authentication endpoints
        """
        ...
