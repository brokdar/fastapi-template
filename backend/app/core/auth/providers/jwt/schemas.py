"""JWT authentication schemas for request/response models."""

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """OAuth2-compliant token response.

    Returns access and refresh tokens with metadata.
    """

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type (always bearer)")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class TokenPayload(BaseModel):
    """JWT token payload structure.

    RFC 7519 compliant claims with custom type and jti fields.
    The jti field is optional for backward compatibility with tokens
    created before blacklist support was added.
    """

    sub: str = Field(..., description="Subject (user ID)")
    exp: int = Field(..., description="Expiration time (Unix timestamp)")
    iat: int = Field(..., description="Issued at (Unix timestamp)")
    type: str = Field(..., description="Token type (access or refresh)")
    jti: str | None = Field(default=None, description="JWT ID for token revocation")


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh endpoint."""

    refresh_token: str = Field(..., description="JWT refresh token to exchange")


class LogoutResponse(BaseModel):
    """Response model for logout endpoint."""

    message: str = Field(
        default="Successfully logged out",
        description="Logout confirmation message",
    )
