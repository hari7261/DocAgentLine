"""Layout normalization stage."""

import re
from datetime import datetime

from sqlalchemy import select, update

from docagentline.db import documents
from docagentline.db.connection import DatabaseManager
from docagentline.observability import get_logger

logger = get_logger(__name__)


class LayoutNormalizationStage:
    """Layout normalization stage."""

    def __init__(self):
        self.db_manager = DatabaseManager()

    async def execute(self, document_id: int):
        """Execute layout normalization stage."""
        # In a real implementation, this would normalize layout, remove headers/footers,
        # fix spacing, etc. For now, we'll just mark as completed.

        async with self.db_manager.get_connection() as conn:
            await conn.execute(
                update(documents)
                .where(documents.c.id == document_id)
                .values(status="layout_normalized", updated_at=datetime.utcnow())
            )
            await conn.commit()

            logger.info(
                "Layout normalized successfully",
                extra={"document_id": document_id},
            )
