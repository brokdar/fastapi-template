"""User domain Pydantic schemas for request/response validation.

This module defines all Pydantic models used for validating input data
and structuring API responses for user management operations.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr

from .models import UserRole


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=12,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Username must be 3-12 characters, alphanumeric and underscores only",
    )
    email: EmailStr = Field(
        ..., max_length=255, description="Valid email address, maximum 255 characters"
    )
    first_name: str | None = Field(
        None, max_length=100, description="User's first name, maximum 100 characters"
    )
    last_name: str | None = Field(
        None, max_length=100, description="User's last name, maximum 100 characters"
    )
    password: SecretStr = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password must be at least 8 characters",
    )
    role: UserRole = Field(UserRole.USER, description="User role, defaults to 'user'")

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""

    username: str | None = Field(
        None,
        min_length=3,
        max_length=12,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Username must be 3-12 characters, alphanumeric and underscores only",
    )
    email: EmailStr | None = Field(
        None, max_length=255, description="Valid email address, maximum 255 characters"
    )
    first_name: str | None = Field(
        None, max_length=100, description="User's first name, maximum 100 characters"
    )
    last_name: str | None = Field(
        None, max_length=100, description="User's last name, maximum 100 characters"
    )
    role: UserRole | None = Field(None, description="User role")
    is_active: bool | None = Field(
        None, description="Whether the user account is active"
    )

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """Schema for user data in API responses."""

    id: int = Field(description="Unique user identifier")
    username: str = Field(description="Username")
    email: EmailStr = Field(description="Email address")
    first_name: str | None = Field(None, description="First name")
    last_name: str | None = Field(None, description="Last name")
    full_name: str = Field(description="Full name computed from first and last name")
    role: UserRole = Field(description="User role")
    is_active: bool = Field(description="Whether the user account is active")
    created_at: datetime = Field(description="Account creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)
