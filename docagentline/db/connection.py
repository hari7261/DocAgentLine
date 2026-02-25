"""Database connection management."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection, create_async_engine

from docagentline.config import get_settings


class DatabaseManager:
    """Manages database connections and lifecycle."""

    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._lock = asyncio.Lock()

    async def get_engine(self) -> AsyncEngine:
        """Get or create async engine."""
        if self._engine is None:
            async with self._lock:
                if self._engine is None:
                    settings = get_settings()
                    db_url = settings.database_url

                    # Convert sqlite:/// to sqlite+aiosqlite:///
                    if db_url.startswith("sqlite:///"):
                        db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

                    connect_args = {}
                    if "sqlite" in db_url:
                        connect_args = {
                            "check_same_thread": False,
                        }

                    self._engine = create_async_engine(
                        db_url,
                        echo=settings.database_echo,
                        poolclass=pool.NullPool if "sqlite" in db_url else pool.QueuePool,
                        connect_args=connect_args,
                    )

                    # Enable WAL mode for SQLite
                    if "sqlite" in db_url:
                        sync_engine = create_engine(
                            settings.database_url,
                            connect_args=connect_args,
                        )

                        @event.listens_for(sync_engine, "connect")
                        def set_sqlite_pragma(dbapi_conn, connection_record):
                            cursor = dbapi_conn.cursor()
                            cursor.execute("PRAGMA journal_mode=WAL")
                            cursor.execute("PRAGMA synchronous=NORMAL")
                            cursor.execute("PRAGMA cache_size=-64000")
                            cursor.execute("PRAGMA busy_timeout=5000")
                            cursor.close()

                        from sqlalchemy import text
                        with sync_engine.connect() as conn:
                            conn.execute(text("SELECT 1"))

        return self._engine

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[AsyncConnection, None]:
        """Get database connection context manager."""
        engine = await self.get_engine()
        async with engine.begin() as conn:
            yield conn

    async def close(self):
        """Close database connections."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None


# Global database manager instance
_db_manager = DatabaseManager()


async def get_db_connection() -> AsyncGenerator[AsyncConnection, None]:
    """Get database connection for dependency injection."""
    async with _db_manager.get_connection() as conn:
        yield conn


async def close_db():
    """Close database connections."""
    await _db_manager.close()
