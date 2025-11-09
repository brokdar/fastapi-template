from typing import Protocol
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.security.base import SecurityBase

from app.core.auth.protocols import AuthenticationUserService
from app.domains.users.models import User


class AuthProvider[ID: (int, UUID)](Protocol):
    """Protocol defining the interface for authentication providers.

    Authentication providers implement different authentication mechanisms
    (e.g., JWT, OAuth, API Key) and provide a consistent interface for
    authenticating requests and managing authentication-specific routes.

    Attributes:
        name: Unique identifier for the authentication provider.
    """

    name: str

    def can_authenticate(self, request: Request) -> bool:
        """Determines if this provider can authenticate the given request.

        Args:
            request: The incoming FastAPI request to check.

        Returns:
            True if this provider can handle authentication for the request,
            False otherwise.
        """
        ...

    async def authenticate(
        self, request: Request, user_service: AuthenticationUserService[ID]
    ) -> User | None:
        """Authenticates the request and returns the authenticated user.

        Args:
            request: The incoming FastAPI request containing authentication credentials.
            user_service: Service for user data access and operations.

        Returns:
            The authenticated User if authentication succeeds, None otherwise.
        """
        ...

    def get_security_scheme(self) -> SecurityBase:
        """Returns the FastAPI security scheme for OpenAPI documentation.

        Returns:
            The security scheme that defines how this provider's authentication
            mechanism appears in the OpenAPI/Swagger documentation.
        """
        ...

    def get_router(self) -> APIRouter:
        """Returns provider-specific API routes.

        Returns:
            APIRouter containing authentication-related endpoints specific to
            this provider (e.g., login, logout, token refresh).
        """
        ...
