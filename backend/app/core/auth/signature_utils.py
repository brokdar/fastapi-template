"""Utilities for dynamic function signature manipulation."""

from collections.abc import Awaitable, Callable
from inspect import Signature
from typing import ParamSpec, TypeVar, cast

from makefun import with_signature

P = ParamSpec("P")
R = TypeVar("R")


def typed_signature(
    signature: Signature,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Apply dynamic signature to async function while preserving type information.

    Wraps makefun.with_signature to maintain proper type hints for async functions.
    Used to inject security scheme parameters for OpenAPI documentation without
    affecting runtime behavior.

    Args:
        signature: The signature to apply to the target function.

    Returns:
        Decorator that applies signature while preserving return type information.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        wrapped = with_signature(signature)(func)
        return cast(Callable[P, Awaitable[R]], wrapped)

    return decorator
