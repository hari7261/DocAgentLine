"""Persistence stage - finalize storage."""

from datetime import datetime

from sqlalchemy import update

from docagentline.db import documents
from docagentline.db.connection import DatabaseManager
from docagentline.observability import get_logger

logger = get_logger(__name__)


class PersistenceStage:
    """Persistence stage."""

    def __init__(self):
        self.db_manager = DatabaseManager()

    async def execute(self, document_id: int):
        """Execute persistence stage."""
        async with self.db_manager.get_connection() as conn:
            await conn.execute(
                update(documents)
                .where(documents.c.id == document_id)
                .values(status="persisted", updated_at=datetime.utcnow())
            )
            await conn.commit()

            logger.info(
                "Persistence completed",
                extra={"document_id": document_id},
            )
