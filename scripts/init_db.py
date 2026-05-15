"""Database initialization script."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings


def init_database():
    """Initialize the database tables."""
    from app.db.database import init_db, Base, engine

    settings = get_settings()
    print(f"Initializing database: {settings.DATABASE_URL}")

    init_db(settings.DATABASE_URL)

    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


if __name__ == "__main__":
    init_database()
