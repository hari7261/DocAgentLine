"""Initialize database and run migrations."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from docagentline.config import get_settings
from docagentline.db.models import metadata


def init_database():
    """Initialize database."""
    settings = get_settings()

    print(f"Initializing database: {settings.database_url}")

    engine = create_engine(settings.database_url)

    # Create all tables
    metadata.create_all(engine)

    print("Database initialized successfully")
    print("\nTables created:")
    for table in metadata.sorted_tables:
        print(f"  - {table.name}")


if __name__ == "__main__":
    init_database()
