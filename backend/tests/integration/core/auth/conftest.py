"""Centralized authentication test configuration and skip logic.

This module provides a pytest hook that automatically skips authentication tests
based on feature toggle configuration. It checks both the master auth switch and
provider-specific toggles.

Configuration hierarchy:
    AUTH__ENABLED=false          -> Skip all auth tests
    AUTH__JWT__ENABLED=false     -> Skip JWT provider tests only
    AUTH__API_KEY__ENABLED=false -> Skip API Key provider tests only
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import pytest
from _pytest.nodes import Item

from app.config import Settings, get_settings


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for a provider's skip logic.

    Attributes:
        path_segment: The path segment that identifies tests for this provider
            (e.g., "providers/jwt" matches tests under that directory).
        enabled_check: Callable that returns True if the provider is enabled.
        skip_reason: Human-readable message shown when tests are skipped.
    """

    path_segment: str
    enabled_check: Callable[[Settings], bool]
    skip_reason: str


# Provider configurations - add new providers here
# Each entry maps a path segment to its feature toggle check
PROVIDER_CONFIGS: Sequence[ProviderConfig] = (
    ProviderConfig(
        path_segment="providers/jwt",
        enabled_check=lambda s: s.auth.jwt.enabled,
        skip_reason="JWT authentication disabled (AUTH__JWT__ENABLED=false)",
    ),
    ProviderConfig(
        path_segment="providers/api_key",
        enabled_check=lambda s: s.auth.api_key.enabled,
        skip_reason="API Key authentication disabled (AUTH__API_KEY__ENABLED=false)",
    ),
)


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[Item],
) -> None:
    """Skip auth tests based on feature toggle configuration.

    This hook runs during test collection and adds skip markers to tests
    based on the authentication configuration. It implements a two-level
    skip hierarchy:

    1. If auth.enabled is False, ALL auth tests are skipped
    2. If a specific provider is disabled, only tests in that provider's
       directory are skipped

    Args:
        config: The pytest configuration object.
        items: List of collected test items to potentially modify.
    """
    settings = get_settings()

    # Check master auth switch first
    if not settings.auth.enabled:
        skip_all = pytest.mark.skip(
            reason="Authentication disabled (AUTH__ENABLED=false)"
        )
        for item in items:
            if "/core/auth/" in str(item.fspath):
                item.add_marker(skip_all)
        return

    # Check provider-specific toggles
    for provider_config in PROVIDER_CONFIGS:
        if not provider_config.enabled_check(settings):
            skip_marker = pytest.mark.skip(reason=provider_config.skip_reason)
            for item in items:
                if provider_config.path_segment in str(item.fspath):
                    item.add_marker(skip_marker)
