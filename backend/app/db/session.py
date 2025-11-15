from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings

engine = create_async_engine(str(get_settings().async_database_url), future=True)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Returns a session to access the database.

    Configuration:
        expire_on_commit=False: Required for async sessions. Default behavior expires
        attributes after commit, triggering implicit lazy loads that cause MissingGreenlet
        errors in async contexts.

    References:
        https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
        https://github.com/sqlalchemy/sqlalchemy/discussions/11495
    """
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


SessionDependency = Annotated[AsyncSession, Depends(get_session)]
