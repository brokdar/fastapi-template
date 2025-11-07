from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings

engine = create_async_engine(str(get_settings().async_database_url), future=True)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Returns a session to access the database."""
    async with AsyncSession(engine) as session:
        yield session


SessionDependency = Annotated[AsyncSession, Depends(get_session)]
