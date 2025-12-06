# FastAPI Starter Template

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.121+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

FastAPI starter with the annoying parts solved: authentication, user management, database migrations, and Docker infrastructure. Develop in a ready-to-go devcontainer, deploy with Docker Compose. Build your app, not the scaffolding.

## Features

### 🔐 Extensible Authentication & Authorization

- **Multi-provider architecture** - JWT included, easily add OAuth, API keys, LDAP, or custom methods
- **Drop-in provider pattern** - Add new auth methods without modifying core code
- **Role-Based Access Control (RBAC)** - Fine-grained permissions system
- **Secure defaults** - BCrypt password hashing, JWT tokens, refresh token rotation

### 🗄️ Database & Persistence

- **PostgreSQL** with async SQLAlchemy/SQLModel
- **Alembic migrations** for version-controlled schema changes
- **Generic repository pattern** with type safety
- **Auto-initialization** with configurable super user

### 🏗️ Code Quality & Architecture

- **Domain-Driven Design** with clear separation of concerns
- **100% type hints** with strict mypy configuration
- **Structured logging** with request ID tracking (structlog)
- **Comprehensive exception handling** with structured error responses

### 🐳 Developer Experience

- **Docker Compose** for one-command setup
- **VS Code DevContainer** with pre-configured environment
- **Pre-commit hooks** with Ruff and mypy
- **GitHub Actions CI/CD** for automated testing

## Quick Start

### Docker Compose (Recommended)

```bash
# Clone and navigate
git clone <your-repo-url>
cd fastapi-template

# Configure environment
cp .env.example .env
# Edit .env and set:
#   - POSTGRES__PASSWORD (strong password)
#   - AUTH__JWT__SECRET_KEY (generate: python -c "import secrets; print(secrets.token_urlsafe(32))")
#   - SUPER_USER__PASSWORD (admin password)

# Start all services
docker compose up

# API available at:
# - Docs: http://localhost:8000/api/v1/docs
# - Health: http://localhost:8000/api/v1/health
```

### Local Development

```bash
# Start database
docker compose up db -d

# Install dependencies (in backend/)
cd backend
uv sync  # or: pip install -e .

# Configure environment
cp ../.env.example ../.env
# Edit .env with your settings

# Run migrations and initialize
alembic upgrade head
python app/db/initialize.py

# Start development server
fastapi dev app/main.py
```

### VS Code DevContainer

Open in VS Code → Command Palette (Ctrl+Shift+P) → "Dev Containers: Reopen in Container"

Everything is automatically configured: database, dependencies, and tools.

## Authentication Flow

The template includes JWT authentication out of the box:

```bash
# 1. Login
curl -X POST "http://localhost:8000/api/v1/auth/jwt/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your-super-user-password"

# Returns: { "access_token": "...", "refresh_token": "...", "token_type": "bearer" }

# 2. Use access token
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer <access_token>"

# 3. Refresh token
curl -X POST "http://localhost:8000/api/v1/auth/jwt/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

## Project Structure

```txt
fastapi-template/
├── backend/
│   ├── app/
│   │   ├── core/              # Cross-cutting concerns
│   │   │   ├── auth/         # Authentication system
│   │   │   ├── base/         # Base models & repositories
│   │   │   ├── exceptions/   # Error handling
│   │   │   ├── logging/      # Structured logging
│   │   │   ├── pagination/   # Pagination utilities
│   │   │   └── security/     # Password hashing
│   │   ├── domains/          # Business domains
│   │   │   ├── users/       # User management
│   │   │   └── health/      # Health checks
│   │   ├── db/              # Database configuration
│   │   ├── config.py        # Settings management
│   │   ├── dependencies.py  # Dependency injection
│   │   └── main.py         # Application entry
│   ├── alembic/            # Database migrations
│   ├── tests/              # Test suite
│   └── pyproject.toml      # Dependencies & tooling
├── .devcontainer/          # VS Code DevContainer
├── .github/workflows/      # CI/CD pipelines
└── docker-compose.yml      # Service orchestration
```

## Technology Stack

### Core Framework

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [SQLModel](https://sqlmodel.tiangolo.com/) - SQL databases with Pydantic models
- [PostgreSQL](https://www.postgresql.org/) - Primary database
- [Pydantic V2](https://docs.pydantic.dev/) - Data validation and settings

### Authentication & Security

- [PyJWT](https://pyjwt.readthedocs.io/) - JWT token handling
- [BCrypt](https://github.com/pyca/bcrypt/) - Password hashing

### Development Tools

- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- [Ruff](https://docs.astral.sh/ruff/) - Linting and formatting
- [mypy](https://mypy.readthedocs.io/) - Static type checking
- [pytest](https://pytest.org/) - Testing framework

### Infrastructure

- [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/) - Containerization
- [Alembic](https://alembic.sqlalchemy.org/) - Database migrations

## Development Workflow

### Code Quality

```bash
cd backend

# Format and lint
ruff format .
ruff check . --fix

# Type check
mypy .

# Run tests
pytest
pytest --cov=app --cov-report=html  # With coverage
```

### Pre-commit Hooks

```bash
# Install hooks (runs checks automatically on commit)
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Documentation

Detailed guides and documentation:

- **[Backend README](backend/README.md)** - API documentation and architecture
- **[Authentication Guide](backend/docs/authentication.md)** - Adding providers, OAuth setup
- **[Coding Guidelines](backend/docs/coding_guidelines.md)** - Code standards and patterns
- **[Testing Guidelines](backend/docs/testing_guidelines.md)** - Test practices and examples
- **[Logging System](backend/app/core/logging/README.md)** - Structured logging architecture
- **[Exception Handling](backend/app/core/exceptions/README.md)** - Error handling system

## Testing

```bash
cd backend

# Run all tests
pytest

# Run specific test file
pytest tests/unit/domains/users/test_services.py

# Run tests matching pattern
pytest -k "test_create"

# Run with coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html  # View coverage report
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**⭐ If you find this template useful, please consider starring it!**
