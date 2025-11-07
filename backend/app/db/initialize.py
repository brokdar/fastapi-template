import asyncio


async def init_db() -> None:
    """Initialize database with required initial data."""
    pass


def main() -> None:
    """Initialize the database."""
    asyncio.run(init_db())


if __name__ == "__main__":
    main()
