# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Reference Documents

Key documentation files for this project:

- **@docs/testing_guidelines.md** - Comprehensive testing standards and best practices
- **@docs/coding_guidelines.md** - Mandatory coding standards and Python requirements
- **@app/core/logging/README.md** - Logging system architecture and usage guide
- **@app/core/exceptions/README.md** - Exception handling architecture and usage guide

## Development Commands

### Environment Setup

```bash
uv sync                     # Install dependencies and sync environment
```

### Code Quality

```bash
ruff check . --fix          # Lint code
ruff format .               # Format code
mypy                        # Type checking
```

### Testing

```bash
pytest                      # Run all tests
pytest tests/unit/          # Run unit tests only
pytest -v                   # Verbose test output
pytest --cov                # Run tests with coverage
```

### Package Management

```bash
uv add package-name         # Add production dependency
uv add --dev package-name   # Add development dependency
uv sync                     # Update dependencies
uv remove package-name      # Remove dependency
```

### Docker and Deployment

```bash
docker compose up           # Start all services
docker compose up api       # Start API service only
docker compose watch        # Start all services with hot-reload (development)
```

The Docker setup uses:

- **Multi-stage build**: Builder stage with uv for dependencies, runtime stage with Python 3.12 Alpine
- **Non-root user**: Runs as user `app` (UID 1001) for security
- **Health check**: Configured at `/api/v1/health` endpoint
- **Production command**: `fastapi run app/main.py` (optimized for production)
- **Port**: Exposes 8000

## Backend Implementation

### Application Entry Point

The application starts in `app/main.py`:

1. **Settings loaded**: Configuration via `get_settings()` from environment
2. **Lifespan handler**: Configures logging after uvicorn starts but before handling requests
3. **CORS middleware**: Configured if `CORS_ORIGINS` is set
4. **Routes setup**: All domain routers registered via `setup_routes()`
5. **OpenAPI customization**: Custom unique ID generation for routes

### Application Lifecycle

```python
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Configure logging after uvicorn starts but before handling requests."""
    configure_logging(
        log_level=settings.LOG.LEVEL,
        log_file_path=settings.LOG.FILE_PATH,
        disable_colors=settings.LOG.DISABLE_COLORS,
    )
    yield
```

The lifespan context manager runs:

- **On startup**: Configure structured logging with settings
- **On shutdown**: Clean up resources (yield statement)

### Dependency Injection

FastAPI dependencies are centralized in `app/dependencies.py`. This file provides:

- Shared dependencies across domains
- Settings access via `get_settings()`
- Database session management (when implemented)
- Authentication/authorization dependencies (when implemented)

### Development Environment

**DevContainer Setup**:

- Python 3.12 (Debian Bullseye base image)
- Docker-in-Docker support
- Git LFS and GitHub CLI pre-installed
- Node.js for frontend tooling
- Auto-installs uv, pre-commit, and npm packages via startup script

**VS Code Configuration**:

- Ruff as default Python formatter
- Auto-format on save and paste
- Auto-fix imports on save
- Pytest integration configured
- Python interpreter set to `backend/.venv`
- Custom terminal profile that auto-activates venv

**Startup Script** (`.devcontainer/startup.sh`):

1. Installs uv package manager
2. Installs Claude Code CLI globally
3. Runs `uv sync` in backend directory
4. Installs and configures pre-commit hooks

## Architecture Overview

### Domain-Driven Structure

The application follows a domain-driven architecture where each business domain is isolated:

```
app/
├── core/              # Cross-cutting concerns (logging, middleware, utilities)
├── domains/           # Business domains (each is self-contained)
│   └── {domain}/
│       ├── endpoints.py   # FastAPI route handlers
│       ├── schemas.py     # Pydantic request/response models
│       ├── services.py    # Business logic layer
│       ├── models.py      # Database models (SQLModel)
│       ├── repositories.py # Data access layer
│       └── exceptions.py  # Domain-specific exceptions
├── config.py          # Application settings (environment-based)
├── dependencies.py    # FastAPI dependency injection
├── main.py           # Application entry point
└── routes.py         # Central route registration
```

### API Implementation Rules

#### General

- **Strict Type Hinting**: You must use strict type hints in all files (even tests), including generics
- **Ensure virtual envirionment**: Ensure that the virtual environment is loaded before running any Python commands
- **Comment the why, not what**: Only use comments to inform about the why something is done and only if it's not obvious
- **Avoid Inline imports**: Use module-level imports wherever possible

#### Endpoints

- **No exception catching**: Let exceptions bubble up to FastAPI's exception handlers
- **No error logging**: FastAPI automatically logs errors; avoid duplicate logging in endpoints
- **Fast-fail validation**: Parse and validate query strings in Pydantic schemas, not in services or repositories
- **Clean interfaces**: Services should receive validated, parsed objects (e.g., Query objects) not raw strings

#### Services

- **Accept parsed objects**: Services should work with typed, validated objects from schemas
- **No exception handling**: Let domain-specific exceptions bubble up to be handled by framework
- **Business logic only**: Focus on core business operations without infrastructure concerns
- **Structured logging**: Use structured logging for operations tracking, not error handling

### Configuration System

Settings are loaded from environment variables via `app/config.py`:

- Uses `pydantic_settings.BaseSettings` with `.env` file support
- Cached with `@lru_cache` for performance
- Access via `get_settings()` function
- Supports nested environment variables with `__` delimiter

Key settings (use `__` delimiter for nested configuration in environment variables):

- `LOG__LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG__FILE_PATH`: Optional file path for JSON log output
- `LOG__DISABLE_COLORS`: Disable colored console output
- `API_PATH`: API route prefix (default: `/api/v1`)
- `CORS_ORIGINS`: Allowed CORS origins

**Note:** The configuration uses nested structure with double underscore (`__`) as delimiter. For example, `LOG__LEVEL` maps to `settings.LOG.LEVEL` in code.

## Critical Development Rules

### Type Hints Are Mandatory

Every function, method, and variable MUST have type hints:

```python
# CORRECT
def process_users(users: list[User], active: bool = True) -> dict[int, User]:
    result: dict[int, User] = {}
    return result

# FORBIDDEN - Will be rejected
def process_users(users, active=True):
    result = {}
    return result
```

### Import Placement

ALL imports MUST be at the top of the file. Inline imports are FORBIDDEN except for breaking circular dependencies.

### Error Handling

Create specific exception classes with detailed context:

```python
class UserNotFoundError(Exception):
    def __init__(self, user_id: int, lookup_field: str = "id"):
        super().__init__(f"User not found: {lookup_field}={user_id}")
```

Always include full error context when re-raising.

### Logging Standards

Use `structlog` for all logging. NEVER use `print()` or string formatting in logs:

```python
# CORRECT
logger.info("user_action_completed", user_id=user.id, action="login")

# FORBIDDEN
print(f"User {user_id} logged in")
logger.error(f"Error: {e}")
```

Log levels:

- `INFO`: Business events
- `WARNING`: Concerning situations
- `DEBUG`: Diagnostic information
- Never log at `ERROR` or `CRITICAL` (handled centrally)

### Documentation

Use Google-style docstrings for all public interfaces:

```python
def create_user(self, data: UserCreate) -> User:
    """Creates a new user with validation.

    Args:
        data: User creation data.

    Returns:
        The newly created user.

    Raises:
        UserAlreadyExistsError: If username/email exists.
    """
```

### Testing Requirements

**Before Writing Tests**: Check for existing parameterized tests to extend, reuse setup code via fixtures, and avoid testing simple data classes.

**Test Structure**:

- Use `pytest.mark.parametrize` for multiple similar cases
- Create fixtures for reusable test data
- Use `AsyncMock(spec=Class)` for repository mocking
- Always include `match` parameter with `pytest.raises`

**Naming Convention**:

```python
# Error scenarios
def test_raises_error_type_when_condition() -> None:

# Successful execution
def test_active_verb_action_successfully() -> None:

# Examples: test_creates_user_successfully, test_validates_email_format
```

**Coverage Requirements**:

- 100% function, class, and method coverage
- Test happy path, error scenarios, and edge cases
- NO comments except for non-obvious "why" explanations
- NO inline imports except for circular dependencies

### Code Quality Workflow

Run before EVERY commit:

```bash
ruff check . --fix && ruff format . && mypy .
```

### Prohibited Patterns

- Backward compatibility code (delete deprecated code immediately)
- Over-engineering (build working features first)
- Bare `except:` clauses
- Returning `None` for failures
- Generic `Exception` catching
- Missing type hints anywhere
- Using `print()` for logging
- Inline imports (except circular deps)

## Adding New Domains

When creating a new domain:

1. Create directory: `app/domains/{domain_name}/`
2. Add required files:
   - `__init__.py`
   - `endpoints.py` - FastAPI routes with proper tags
   - `schemas.py` - Request/response Pydantic models
   - `services.py` - Business logic (if needed)
   - `models.py` - Database models (if needed)
   - `repositories.py` - Data access (if needed)
   - `exceptions.py` - Domain-specific errors (if needed)
3. Register router in `app/routes.py`:

   ```python
   from app.domains.{domain_name}.endpoints import router as {domain_name}_router
   app.include_router({domain_name}_router, prefix=prefix)
   ```

## Testing Structure

Tests mirror the app structure:

```
tests/
└── unit/
    ├── conftest.py          # Shared fixtures
    └── domains/
        └── {domain_name}/
            ├── test_endpoints.py
            ├── test_services.py
            └── test_repositories.py
```

Always check `conftest.py` for existing fixtures before creating new ones.

## Issue Resolution Standards

- **Prioritize best practices over quick fixes** - Always analyze the root cause and implement solutions that align with the tech stack's established patterns, conventions, and architectural guidelines
- **Follow framework conventions** - Use the recommended approaches, error handling patterns, and coding standards specific to the current technology stack rather than generic workarounds
- **Consider long-term maintainability** - Choose solutions that enhance code quality, readability, and future extensibility even if they require more initial implementation effort
- **Avoid dirty workarounds** - Resist the temptation to apply quick patches that may introduce technical debt, create maintenance burdens, or violate established architectural principles
- **Implement proper abstractions** - Structure fixes using appropriate design patterns and abstractions that fit naturally within the existing codebase architecture

## Mandatory Principles

- **DELETE DEPRECATED CODE IMMEDIATELY**: Never maintain backward compatibility. Remove legacy functions instantly.
- **FUNCTIONALITY FIRST**: Build working features before production patterns. No over-engineering.
- **DETAILED ERRORS MANDATORY**: Every error must include: what failed, where, why, and actual values.
- **BREAK TO IMPROVE**: Restructure code when it improves architecture. Never preserve poor patterns.
- **CHECK THE DOCS**: Whenever you are uncertain about an implementation, use context7 to check the documentations
