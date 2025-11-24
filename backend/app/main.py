from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.config import get_settings
from app.core.exceptions.handlers import setup_exception_handlers
from app.core.logging.config import configure_logging
from app.routes import setup_routes


def custom_generate_unique_id(route: APIRoute) -> str:
    """Custom function to generate unique id for each route."""
    return f"{route.tags[0]}-{route.name}"


settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Configure logging after uvicorn starts but before handling requests."""
    configure_logging(
        log_level=settings.log.level,
        log_file_path=settings.log.file_path,
        disable_colors=settings.log.disable_colors,
    )
    yield


app = FastAPI(
    title=settings.application_name,
    description="FastAPI template with user management and authentication.",
    version="1.0.0",
    root_path=settings.api_path,
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

setup_exception_handlers(app)

if settings.cors_origins:
    origins = [origin.strip() for origin in settings.cors_origins]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

setup_routes(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)  # noqa: S104
