"""API Key management routes."""

from collections.abc import Callable

import structlog
from fastapi import APIRouter, Depends, Security, status

from app.dependencies import auth_service
from app.domains.users.models import User, UserRole

from .schemas import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeyResponse,
)
from .services import APIKeyService

logger = structlog.get_logger("auth.provider.api_key.router")


def create_api_key_router(
    get_api_key_service: Callable[[], APIKeyService],
) -> APIRouter:
    """Create API key management router.

    Args:
        get_api_key_service: Dependency factory for APIKeyService instances.

    Returns:
        APIRouter: Router containing API key management endpoints.
    """
    router = APIRouter(prefix="/api-keys", tags=["api-keys"])

    @router.get(
        "/users/{user_id}",
        response_model=list[APIKeyListResponse],
        summary="Admin: List user's API keys",
        description="List all API keys for a specific user (admin only).",
    )
    async def admin_list_user_api_keys(
        user_id: int,
        admin: User = Security(auth_service.require_roles(UserRole.ADMIN)),
        api_key_service: APIKeyService = Depends(get_api_key_service),
    ) -> list[APIKeyListResponse]:
        """Admin: List all API keys for a specific user."""
        keys = await api_key_service.list_keys(user_id)
        return [
            APIKeyListResponse(
                id=k.pk,
                user_id=k.user_id,
                name=k.name,
                key_prefix=k.key_prefix,
                created_at=k.created_at,
                expires_at=k.expires_at,
                last_used_at=k.last_used_at,
            )
            for k in keys
        ]

    @router.delete(
        "/users/{user_id}/{key_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Admin: Delete user's API key",
        description="Delete any user's API key (admin only).",
    )
    async def admin_delete_user_api_key(
        user_id: int,
        key_id: int,
        admin: User = Security(auth_service.require_roles(UserRole.ADMIN)),
        api_key_service: APIKeyService = Depends(get_api_key_service),
    ) -> None:
        """Admin: Delete a specific user's API key."""
        await api_key_service.delete_key_admin(key_id=key_id, admin_id=admin.pk)
        logger.info(
            "api_key_deleted_by_admin_via_api",
            admin_id=admin.pk,
            target_user_id=user_id,
            key_id=key_id,
        )

    @router.post(
        "",
        response_model=APIKeyCreateResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create a new API key",
        description="Create a new API key for the authenticated user. The secret key is only returned once.",
    )
    async def create_api_key(
        data: APIKeyCreate,
        user: User = Security(auth_service.require_user),
        api_key_service: APIKeyService = Depends(get_api_key_service),
    ) -> APIKeyCreateResponse:
        """Create a new API key for the current user."""
        plaintext_key, api_key = await api_key_service.create_key(
            user_id=user.pk,
            name=data.name,
            expires_in_days=data.expires_in_days,
        )

        logger.info("api_key_created_via_api", user_id=user.pk, key_id=api_key.pk)

        return APIKeyCreateResponse(
            id=api_key.pk,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            last_used_at=api_key.last_used_at,
            secret_key=plaintext_key,
        )

    @router.get(
        "",
        response_model=list[APIKeyResponse],
        summary="List your API keys",
        description="List all API keys for the authenticated user (secrets not included).",
    )
    async def list_api_keys(
        user: User = Security(auth_service.require_user),
        api_key_service: APIKeyService = Depends(get_api_key_service),
    ) -> list[APIKeyResponse]:
        """List all API keys for the current user."""
        keys = await api_key_service.list_keys(user.pk)
        return [
            APIKeyResponse(
                id=k.pk,
                name=k.name,
                key_prefix=k.key_prefix,
                created_at=k.created_at,
                expires_at=k.expires_at,
                last_used_at=k.last_used_at,
            )
            for k in keys
        ]

    @router.delete(
        "/{key_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Delete an API key",
        description="Delete one of your API keys.",
    )
    async def delete_api_key(
        key_id: int,
        user: User = Security(auth_service.require_user),
        api_key_service: APIKeyService = Depends(get_api_key_service),
    ) -> None:
        """Delete an API key owned by the current user."""
        await api_key_service.delete_key(key_id=key_id, user_id=user.pk)
        logger.info("api_key_deleted_via_api", user_id=user.pk, key_id=key_id)

    return router
