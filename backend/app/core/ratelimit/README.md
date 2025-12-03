# Rate Limiting

This module provides reusable rate limiting for FastAPI routes using [slowapi](https://github.com/laurentS/slowapi).

## Quick Start

```python
from fastapi import Request
from app.core.ratelimit import limiter

@router.post("/endpoint")
@limiter.limit("10/minute")
async def my_endpoint(request: Request):
    ...
```

For user-based rate limiting on authenticated routes:

```python
from fastapi import Request, Security
from app.core.ratelimit import limiter, get_user_identifier
from app.dependencies import auth_service

@router.post("/user-action")
@limiter.limit("5/minute", key_func=get_user_identifier)
async def user_action(
    request: Request,
    user: User = Security(auth_service.require_user),
):
    ...
```

## Key Functions

| Function | Description | Use Case |
|----------|-------------|----------|
| Default (IP-based) | Uses client IP address | Public endpoints, login |
| `get_user_identifier` | Uses authenticated user ID, falls back to IP | Authenticated endpoints |

## Rate Limit Format

Limits follow the format: `<count>/<period>`

Examples:

- `5/minute` - 5 requests per minute
- `100/hour` - 100 requests per hour
- `1000/day` - 1000 requests per day

## Configuration

Rate limits for auth endpoints are configurable via environment variables:

```bash
AUTH__JWT__LOGIN_RATE_LIMIT=5/minute
AUTH__JWT__REFRESH_RATE_LIMIT=10/minute
AUTH__API_KEY__CREATE_RATE_LIMIT=5/minute
AUTH__API_KEY__DELETE_RATE_LIMIT=10/minute
```

## Response Headers

When rate limiting is active, responses include:

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests allowed |
| `X-RateLimit-Remaining` | Remaining requests in window |
| `X-RateLimit-Reset` | Seconds until limit resets |

When limit is exceeded, returns `429 Too Many Requests` with a `Retry-After` header.

## Architecture

```tree
app/core/ratelimit/
├── __init__.py     # Public exports
└── limiter.py      # Limiter instance and key functions
```

The shared `limiter` instance is attached to the FastAPI app in `main.py`:

```python
from app.core.ratelimit import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

## Testing

For tests, configure high rate limits to avoid test interference:

```python
@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        auth=AuthSettings(
            jwt=JWTSettings(login_rate_limit="1000/minute"),
            api_key=APIKeySettings(create_rate_limit="1000/minute"),
        )
    )
```

Or via environment variables in test scripts:

```bash
export AUTH__JWT__LOGIN_RATE_LIMIT="1000/minute"
```
