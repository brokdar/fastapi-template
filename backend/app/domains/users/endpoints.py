"""User management API endpoints.

This module defines all REST API endpoints for user CRUD operations.
Follows FastAPI best practices with proper validation, documentation, and error handling.
"""

import structlog
from fastapi import status
from fastapi.routing import APIRouter

from app.core.auth.dependencies import RequiresUserDependency
from app.core.exceptions.schemas import (
    ErrorResponse,
    InternalServerErrorResponse,
    ValidationErrorResponse,
)
from app.core.pagination import Page, PaginationDependency
from app.dependencies import UserServiceDependency

from .schemas import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

logger = structlog.get_logger("users.endpoints")


@router.get(
    "/",
    response_model=Page[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all users",
    description="Retrieve a paginated list of all users in the system",
    responses={
        200: {"description": "Users retrieved successfully"},
        422: {
            "model": ValidationErrorResponse,
            "description": "Invalid query parameters",
        },
        500: {
            "model": InternalServerErrorResponse,
            "description": "Internal server error",
        },
    },
)
async def get_users(
    pagination: PaginationDependency,
    user_service: UserServiceDependency,
) -> Page[UserResponse]:
    """Get a paginated list of users.

    Returns a paginated list of users with metadata about the pagination state.
    Users are ordered by ID for consistent pagination.

    Query Parameters:
        offset: Number of items to skip (default: 0)
        limit: Maximum number of users to return (1-100, default: 10)
    """
    users, total = await user_service.get_all(
        offset=pagination.offset, limit=pagination.limit
    )
    return Page[UserResponse].create(
        items=[UserResponse.model_validate(user) for user in users],
        offset=pagination.offset,
        limit=pagination.limit,
        total=total,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user by ID",
    description="Retrieve a specific user by their unique identifier",
    responses={
        200: {"description": "User retrieved successfully"},
        404: {"model": ErrorResponse, "description": "User not found"},
        422: {
            "model": ValidationErrorResponse,
            "description": "Invalid user ID format",
        },
        500: {
            "model": InternalServerErrorResponse,
            "description": "Internal server error",
        },
    },
)
async def get_user(
    user_id: int,
    user_service: UserServiceDependency,
) -> UserResponse:
    """Get a user by their ID.

    Returns the full user information for the specified user ID.
    Raises 404 if the user does not exist.
    """
    user = await user_service.get_by_id(user_id)
    return UserResponse.model_validate(user)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
    description="Create a new user account with provided information",
    responses={
        201: {"description": "User created successfully"},
        409: {
            "model": ErrorResponse,
            "description": "User already exists (email or username conflict)",
        },
        422: {"model": ValidationErrorResponse, "description": "Invalid user data"},
        500: {
            "model": InternalServerErrorResponse,
            "description": "Internal server error",
        },
    },
)
async def create_user(
    user_data: UserCreate,
    user_service: UserServiceDependency,
) -> UserResponse:
    """Create a new user.

    Creates a new user with the provided information. Username and email must be unique.
    Returns the created user with generated ID and timestamps.
    """
    created_user = await user_service.create_user(user_data)
    return UserResponse.model_validate(created_user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user",
    description="Update specific fields of an existing user",
    responses={
        200: {"description": "User updated successfully"},
        404: {"model": ErrorResponse, "description": "User not found"},
        409: {
            "model": ErrorResponse,
            "description": "Update would create conflict (email or username)",
        },
        422: {
            "model": ValidationErrorResponse,
            "description": "Invalid user data or user ID format",
        },
        500: {
            "model": InternalServerErrorResponse,
            "description": "Internal server error",
        },
    },
)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    user_service: UserServiceDependency,
) -> UserResponse:
    """Update an existing user.

    Updates only the fields provided in the request body. All fields are optional.
    Username and email must remain unique if updated.
    Returns the updated user information.
    """
    updated_user = await user_service.update_user(user_id, user_update)
    return UserResponse.model_validate(updated_user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user by ID",
    description="Delete a user account permanently",
    responses={
        204: {"description": "User deleted successfully"},
        404: {"model": ErrorResponse, "description": "User not found"},
        422: {
            "model": ValidationErrorResponse,
            "description": "Invalid user ID format",
        },
        500: {
            "model": InternalServerErrorResponse,
            "description": "Internal server error",
        },
    },
)
async def delete_user(
    user_id: int,
    user_service: UserServiceDependency,
) -> None:
    """Delete a user by their ID.

    Args:
        user_id: The unique identifier of the user to delete.
        user_service: Injected user service dependency.
    """
    await user_service.delete_user(user_id)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current authenticated user's information",
    description="Common pattern for self-service user info retrieval",
    responses={
        200: {"description": "User information retrieved successfully"},
        401: {
            "model": ErrorResponse,
            "description": "Authentication required",
        },
        500: {
            "model": InternalServerErrorResponse,
            "description": "Internal server error",
        },
    },
)
async def get_user_profile(
    user: RequiresUserDependency,
) -> UserResponse:
    """Retrieve current authenticated user's information.

    Returns the full user information for the currently authenticated user.
    Requires valid authentication to access this endpoint.

    Args:
        user: Currently authenticated user from dependency.

    Returns:
        UserResponse: Current user's information.
    """
    logger.info(
        "user_profile_access",
        user_id=user.id,
        username=user.username,
    )

    return UserResponse.model_validate(user)


@router.patch(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user's information",
    description="RESTful partial update of current user's profile information",
    responses={
        200: {"description": "User updated successfully"},
        400: {
            "model": ErrorResponse,
            "description": "Email already in use (UPDATE_USER_EMAIL_ALREADY_EXISTS), Invalid password format (UPDATE_USER_INVALID_PASSWORD)",
        },
        401: {
            "model": ErrorResponse,
            "description": "Authentication required",
        },
        422: {
            "model": ValidationErrorResponse,
            "description": "Invalid user data",
        },
        500: {
            "model": InternalServerErrorResponse,
            "description": "Internal server error",
        },
    },
)
async def update_user_profile(
    user_update: UserUpdate,
    user: RequiresUserDependency,
    user_service: UserServiceDependency,
) -> UserResponse:
    """Update current user's information.

    Updates only the fields provided in the request body using RESTful partial update.
    All fields are optional. Username and email must remain unique if updated.

    Args:
        user_update: User update data with optional fields.
        user: Currently authenticated user.
        user_service: User service for database operations.

    Returns:
        UserResponse: Updated user information.

    Raises:
        UserAlreadyExistsError: For UPDATE_USER_EMAIL_ALREADY_EXISTS.
        ValidationError: For UPDATE_USER_INVALID_PASSWORD.
    """
    logger.info(
        "user_profile_update",
        user_id=user.id,
        username=user.username,
    )

    if user.id is None:
        raise ValueError("Authenticated user must have an ID")

    updated_user = await user_service.update_user(user.id, user_update)
    return UserResponse.model_validate(updated_user)
