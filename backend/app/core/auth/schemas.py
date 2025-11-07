"""Authentication schemas for request/response models."""

from pydantic import BaseModel, Field, SecretStr

from app.domains.users.models import UserRole


class LoginRequest(BaseModel):
    """Login request with username or email and password.

    Attributes:
        username_or_email: Username or email address for authentication.
        password: User password (secure string).
    """

    username_or_email: str = Field(
        ..., min_length=3, max_length=255, description="Username or email address"
    )
    password: SecretStr = Field(..., description="User password")


class TokenResponse(BaseModel):
    """JWT token response containing access and refresh tokens.

    Attributes:
        access_token: Short-lived access token for API requests.
        refresh_token: Long-lived refresh token for obtaining new access tokens.
        token_type: Token type identifier (always "bearer").
    """

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class RefreshRequest(BaseModel):
    """Refresh token request.

    Attributes:
        refresh_token: Valid refresh token to exchange for new token pair.
    """

    refresh_token: str = Field(..., description="Valid refresh token")


class TokenPayload(BaseModel):
    """JWT token payload structure.

    Attributes:
        sub: Subject (user ID).
        username: Username of the authenticated user.
        role: User role for authorization.
        exp: Expiration timestamp (Unix epoch).
        iat: Issued at timestamp (Unix epoch).
        type: Token type ("access" or "refresh").
    """

    sub: int = Field(..., description="Subject (user ID)")
    username: str = Field(..., description="Username")
    role: UserRole = Field(..., description="User role")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    type: str = Field(..., description="Token type (access or refresh)")
