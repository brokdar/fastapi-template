"""Test suite for ProviderRegistry."""

from collections.abc import Generator
from typing import Any, ClassVar
from unittest.mock import Mock

import pytest

from app.config import Settings
from app.core.auth.providers.base import AuthProvider
from app.core.auth.providers.registry import ProviderFactory, ProviderRegistry


@pytest.fixture(autouse=True)
def clear_registry() -> Generator[None, None, None]:
    """Reset registry state after each test."""
    yield
    ProviderRegistry.clear()


@pytest.fixture
def mock_settings() -> Mock:
    """Provide mock Settings object."""
    return Mock(spec=Settings)


@pytest.fixture
def mock_provider() -> Mock:
    """Provide mock AuthProvider instance."""
    return Mock(spec=AuthProvider)


def create_factory(
    factory_name: str,
    return_value: AuthProvider | None = None,
) -> type[ProviderFactory]:
    """Create a test factory class."""
    provider = return_value

    class TestFactory:
        name: str = factory_name
        priority: ClassVar[int] = 100

        @staticmethod
        def create(settings: Settings, **dependencies: Any) -> AuthProvider | None:
            return provider

    return TestFactory


class TestProviderRegistryRegister:
    """Test suite for ProviderRegistry.register decorator."""

    def test_registers_factory_successfully(self) -> None:
        """Test successful factory registration."""
        factory = create_factory("test_provider")

        registered = ProviderRegistry.register("test_provider")(factory)

        assert registered is factory
        assert ProviderRegistry.get_factory("test_provider") is factory

    def test_raises_value_error_when_duplicate_name(self) -> None:
        """Test ValueError is raised for duplicate provider name."""
        factory1 = create_factory("duplicate")
        factory2 = create_factory("duplicate")
        ProviderRegistry.register("duplicate")(factory1)

        with pytest.raises(
            ValueError, match="Provider 'duplicate' is already registered"
        ):
            ProviderRegistry.register("duplicate")(factory2)

    def test_sets_priority_on_factory(self) -> None:
        """Test that priority is set on the factory class."""
        factory = create_factory("priority_test")

        ProviderRegistry.register("priority_test", priority=50)(factory)

        assert factory.priority == 50

    @pytest.mark.parametrize(
        ("priorities", "expected_order"),
        [
            ([100, 50, 75], ["p2", "p3", "p1"]),
            ([10, 20, 30], ["p1", "p2", "p3"]),
            ([50, 50, 50], ["p1", "p2", "p3"]),
        ],
        ids=["mixed_priorities", "ascending_priorities", "equal_priorities"],
    )
    def test_maintains_sorted_order_by_priority(
        self,
        priorities: list[int],
        expected_order: list[str],
    ) -> None:
        """Test that providers are sorted by priority."""
        for i, priority in enumerate(priorities, 1):
            factory = create_factory(f"p{i}")
            ProviderRegistry.register(f"p{i}", priority=priority)(factory)

        assert ProviderRegistry.list_registered() == expected_order


class TestProviderRegistryGetEnabledProviders:
    """Test suite for ProviderRegistry.get_enabled_providers."""

    def test_returns_enabled_providers_in_priority_order(
        self,
        mock_settings: Mock,
    ) -> None:
        """Test enabled providers are returned in priority order."""
        provider1 = Mock(spec=AuthProvider)
        provider2 = Mock(spec=AuthProvider)
        provider3 = Mock(spec=AuthProvider)

        factory1 = self._create_factory_with_mock("high", provider1)
        factory2 = self._create_factory_with_mock("low", provider2)
        factory3 = self._create_factory_with_mock("medium", provider3)

        ProviderRegistry.register("high", priority=100)(factory1)
        ProviderRegistry.register("low", priority=10)(factory2)
        ProviderRegistry.register("medium", priority=50)(factory3)

        providers = ProviderRegistry.get_enabled_providers(mock_settings)

        assert providers == [provider2, provider3, provider1]

    def test_excludes_disabled_providers(self, mock_settings: Mock) -> None:
        """Test that disabled providers (returning None) are excluded."""
        enabled_provider = Mock(spec=AuthProvider)
        factory_enabled = self._create_factory_with_mock("enabled", enabled_provider)
        factory_disabled = self._create_factory_with_mock("disabled", None)

        ProviderRegistry.register("enabled", priority=50)(factory_enabled)
        ProviderRegistry.register("disabled", priority=10)(factory_disabled)

        providers = ProviderRegistry.get_enabled_providers(mock_settings)

        assert providers == [enabled_provider]

    def test_passes_dependencies_to_factories(self, mock_settings: Mock) -> None:
        """Test that dependencies are passed to factory create method."""
        create_mock = Mock(return_value=None)

        class FactoryWithMock:
            name: str = "dep_test"
            priority: ClassVar[int] = 100
            create = staticmethod(create_mock)

        ProviderRegistry.register("dep_test")(FactoryWithMock)  # type: ignore[arg-type]

        ProviderRegistry.get_enabled_providers(
            mock_settings,
            get_api_key_service=Mock(),
            other_dep="value",
        )

        create_mock.assert_called_once()
        call_kwargs = create_mock.call_args[1]
        assert "get_api_key_service" in call_kwargs
        assert call_kwargs["other_dep"] == "value"

    def test_returns_empty_list_when_no_providers_enabled(
        self,
        mock_settings: Mock,
    ) -> None:
        """Test empty list is returned when no providers are enabled."""
        factory = self._create_factory_with_mock("disabled", None)
        ProviderRegistry.register("disabled")(factory)

        providers = ProviderRegistry.get_enabled_providers(mock_settings)

        assert providers == []

    def _create_factory_with_mock(
        self,
        name: str,
        return_value: AuthProvider | None,
    ) -> type[ProviderFactory]:
        """Create factory that returns specified provider."""
        mock_create = Mock(return_value=return_value)

        class MockFactory:
            priority: ClassVar[int] = 100
            create = staticmethod(mock_create)

        MockFactory.name = name  # type: ignore[attr-defined]
        return MockFactory  # type: ignore[return-value]


class TestProviderRegistryGetFactory:
    """Test suite for ProviderRegistry.get_factory."""

    def test_returns_factory_when_found(self) -> None:
        """Test factory is returned when it exists."""
        factory = create_factory("existing")
        ProviderRegistry.register("existing")(factory)

        result = ProviderRegistry.get_factory("existing")

        assert result is factory

    def test_returns_none_when_not_found(self) -> None:
        """Test None is returned when factory doesn't exist."""
        result = ProviderRegistry.get_factory("nonexistent")

        assert result is None


class TestProviderRegistryListRegistered:
    """Test suite for ProviderRegistry.list_registered."""

    def test_returns_names_in_priority_order(self) -> None:
        """Test names are returned in priority order."""
        ProviderRegistry.register("last", priority=100)(create_factory("last"))
        ProviderRegistry.register("first", priority=10)(create_factory("first"))
        ProviderRegistry.register("middle", priority=50)(create_factory("middle"))

        result = ProviderRegistry.list_registered()

        assert result == ["first", "middle", "last"]

    def test_returns_empty_list_when_none_registered(self) -> None:
        """Test empty list is returned when no providers registered."""
        result = ProviderRegistry.list_registered()

        assert result == []


class TestProviderRegistryClear:
    """Test suite for ProviderRegistry.clear."""

    def test_clears_all_factories_and_order(self) -> None:
        """Test that clear removes all registered factories."""
        ProviderRegistry.register("test1")(create_factory("test1"))
        ProviderRegistry.register("test2")(create_factory("test2"))

        ProviderRegistry.clear()

        assert ProviderRegistry.list_registered() == []
        assert ProviderRegistry.get_factory("test1") is None
        assert ProviderRegistry.get_factory("test2") is None
