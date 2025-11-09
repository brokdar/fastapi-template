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

    RFC 7519 compliant claims with custom type field.
    """

    sub: str = Field(..., description="Subject (user ID)")
    exp: int = Field(..., description="Expiration time (Unix timestamp)")
    iat: int = Field(..., description="Issued at (Unix timestamp)")
    type: str = Field(..., description="Token type (access or refresh)")


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh endpoint."""

    refresh_token: str = Field(..., description="JWT refresh token to exchange")
