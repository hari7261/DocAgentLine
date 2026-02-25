"""Pytest configuration and fixtures."""

import asyncio
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from docagentline.config import get_settings
from docagentline.db.models import metadata


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db():
    """Create test database."""
    test_db_path = Path("test_docagentline.db")

    # Remove if exists
    if test_db_path.exists():
        test_db_path.unlink()

    # Set test database URL
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"

    # Create tables
    engine = create_engine(f"sqlite:///{test_db_path}")
    metadata.create_all(engine)

    yield

    # Cleanup
    if test_db_path.exists():
        test_db_path.unlink()


@pytest.fixture
def sample_schema():
    """Sample JSON schema for testing."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "amount": {"type": "number"},
            "date": {"type": "string", "format": "date"},
        },
        "required": ["name", "amount"],
    }
