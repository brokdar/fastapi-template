"""Test suite for ProviderRegistry."""

from collections.abc import Callable, Generator
from dataclasses import dataclass
from unittest.mock import MagicMock, Mock

import pytest

from app.config import Settings
from app.core.auth.providers.base import AuthProvider
from app.core.auth.providers.registry import ProviderFactory, ProviderRegistry
from app.core.auth.providers.types import ProviderDeps


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
    factory_deps_type: type[ProviderDeps] | None = None,
) -> type[ProviderFactory]:
    """Create a test factory class."""
    provider = return_value
    stored_deps_type = factory_deps_type

    class TestFactory:
        name = factory_name
        priority = 100
        deps_type: type[ProviderDeps] | None = stored_deps_type

        @staticmethod
        def create(
            settings: Settings, deps: ProviderDeps | None
        ) -> AuthProvider | None:
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

    def test_stores_deps_type_on_registration(self) -> None:
        """Test that deps_type is stored when registering."""

        @dataclass(frozen=True)
        class TestDeps(ProviderDeps):
            some_service: Callable[..., object]

        factory = create_factory("deps_test", factory_deps_type=TestDeps)

        ProviderRegistry.register("deps_test", deps_type=TestDeps)(factory)

        assert ProviderRegistry.get_required_deps_types() == {"deps_test": TestDeps}

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

    def test_passes_typed_deps_to_factories(self) -> None:
        """Test that typed dependencies are passed to factory create method."""

        @dataclass(frozen=True)
        class TestDeps(ProviderDeps):
            get_service: Callable[..., object]

        received_deps: list[ProviderDeps | None] = []
        settings = MagicMock()

        class FactoryWithMock:
            name = "dep_test"
            priority = 100
            deps_type: type[ProviderDeps] | None = TestDeps

            @staticmethod
            def create(
                settings: Settings, deps: ProviderDeps | None
            ) -> AuthProvider | None:
                received_deps.append(deps)
                return None

        ProviderRegistry.register("dep_test", deps_type=TestDeps)(FactoryWithMock)

        test_deps = TestDeps(get_service=Mock())
        ProviderRegistry.get_enabled_providers(
            settings,
            dependencies={"dep_test": test_deps},
        )

        assert len(received_deps) == 1
        assert received_deps[0] is test_deps

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
        captured_return = return_value

        class MockFactory:
            priority = 100
            deps_type: type[ProviderDeps] | None = None

            @staticmethod
            def create(
                settings: Settings, deps: ProviderDeps | None
            ) -> AuthProvider | None:
                return captured_return

        MockFactory.name = name  # type: ignore[attr-defined]
        return MockFactory  # type: ignore[return-value]


class TestProviderRegistryDependencyTypeValidation:
    """Test suite for dependency type validation in get_enabled_providers."""

    def test_raises_value_error_when_wrong_deps_type(self) -> None:
        """Test that validation fails when deps are of wrong type."""

        @dataclass(frozen=True)
        class TestDeps(ProviderDeps):
            some_service: Callable[..., object]

        @dataclass(frozen=True)
        class WrongDeps(ProviderDeps):
            other_service: Callable[..., object]

        factory = create_factory("test_provider", factory_deps_type=TestDeps)
        ProviderRegistry.register("test_provider", deps_type=TestDeps)(factory)

        settings = MagicMock()
        wrong_deps = WrongDeps(other_service=Mock())

        with pytest.raises(ValueError, match="requires TestDeps, got WrongDeps"):
            ProviderRegistry.get_enabled_providers(
                settings, {"test_provider": wrong_deps}
            )

    def test_accepts_correct_deps_type(self) -> None:
        """Test that validation passes when correct deps type is provided."""

        @dataclass(frozen=True)
        class TestDeps(ProviderDeps):
            some_service: Callable[..., object]

        factory = create_factory("test_provider", factory_deps_type=TestDeps)
        ProviderRegistry.register("test_provider", deps_type=TestDeps)(factory)

        settings = MagicMock()
        correct_deps = TestDeps(some_service=Mock())

        ProviderRegistry.get_enabled_providers(
            settings, {"test_provider": correct_deps}
        )

    def test_ignores_deps_for_unknown_providers(self) -> None:
        """Test that deps for unregistered providers are ignored."""
        factory = create_factory("known_provider", factory_deps_type=None)
        ProviderRegistry.register("known_provider")(factory)

        @dataclass(frozen=True)
        class UnknownDeps(ProviderDeps):
            some_service: Callable[..., object]

        settings = MagicMock()
        unknown_deps = UnknownDeps(some_service=Mock())

        ProviderRegistry.get_enabled_providers(
            settings, {"unknown_provider": unknown_deps}
        )


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


class TestProviderRegistryGetRequiredDepsTypes:
    """Test suite for ProviderRegistry.get_required_deps_types."""

    def test_returns_deps_types_for_providers_with_deps(self) -> None:
        """Test that only providers with deps_type are returned."""

        @dataclass(frozen=True)
        class TestDeps(ProviderDeps):
            some_service: Callable[..., object]

        factory_with_deps = create_factory("with_deps", factory_deps_type=TestDeps)
        factory_without_deps = create_factory("without_deps", factory_deps_type=None)

        ProviderRegistry.register("with_deps", deps_type=TestDeps)(factory_with_deps)
        ProviderRegistry.register("without_deps")(factory_without_deps)

        result = ProviderRegistry.get_required_deps_types()

        assert result == {"with_deps": TestDeps}

    def test_returns_empty_dict_when_no_deps_required(self) -> None:
        """Test empty dict when no providers require deps."""
        factory = create_factory("no_deps", factory_deps_type=None)
        ProviderRegistry.register("no_deps")(factory)

        result = ProviderRegistry.get_required_deps_types()

        assert result == {}


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

    def test_clears_deps_types(self) -> None:
        """Test that clear also removes deps_types."""

        @dataclass(frozen=True)
        class TestDeps(ProviderDeps):
            some_service: Callable[..., object]

        factory = create_factory("test", factory_deps_type=TestDeps)
        ProviderRegistry.register("test", deps_type=TestDeps)(factory)

        ProviderRegistry.clear()

        assert ProviderRegistry.get_required_deps_types() == {}
