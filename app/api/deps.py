"""API dependency injection."""

from typing import Generator

from app.config import Settings, get_settings


async def get_db() -> Generator:
    """Database session dependency."""
    yield None


def get_settings_dep() -> Settings:
    """Settings dependency."""
    return get_settings()
