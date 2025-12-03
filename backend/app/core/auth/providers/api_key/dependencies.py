"""Dependency definitions for API Key provider."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.auth.providers.types import ProviderDeps

if TYPE_CHECKING:
    from app.core.auth.providers.api_key.services import APIKeyService


@dataclass(frozen=True)
class APIKeyDeps(ProviderDeps):
    """Dependencies required by the API Key authentication provider.

    Args:
        get_api_key_service: FastAPI dependency callable that returns
            an APIKeyService instance. This is resolved per-request
            to get a fresh database session.
    """

    get_api_key_service: Callable[..., APIKeyService]
