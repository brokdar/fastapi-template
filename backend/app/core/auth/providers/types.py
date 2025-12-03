"""Base types for provider dependency injection."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderDeps:
    """Base class for provider dependencies.

    Each provider that requires dependencies should define a subclass
    with typed fields for each dependency it needs. The frozen=True
    ensures immutability after creation.

    Example:
        @dataclass(frozen=True)
        class MyProviderDeps(ProviderDeps):
            get_my_service: Callable[..., MyService]
    """

    pass
