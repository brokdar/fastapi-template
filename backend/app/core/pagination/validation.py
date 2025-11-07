from collections.abc import Awaitable, Callable
from functools import wraps

from .exceptions import InvalidPaginationError


def validate_pagination[**P, R](
    func: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    """Validate pagination parameters (limit and offset).

    Ensures limit > 0 and offset >= 0.

    Raises:
        InvalidPaginationError: If limit <= 0 or offset < 0
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if "limit" in kwargs:
            limit = kwargs["limit"]
            if not isinstance(limit, int) or limit <= 0:
                raise InvalidPaginationError(
                    parameter="limit",
                    value=limit,
                    constraint="must be positive integer",
                )

        if "offset" in kwargs:
            offset = kwargs["offset"]
            if not isinstance(offset, int) or offset < 0:
                raise InvalidPaginationError(
                    parameter="offset",
                    value=offset,
                    constraint="must be non-negative integer",
                )

        return await func(*args, **kwargs)

    return wrapper
