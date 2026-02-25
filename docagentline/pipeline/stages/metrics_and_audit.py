"""Metrics and audit stage - finalize metrics."""

from datetime import datetime

from sqlalchemy import select, update

from docagentline.db import documents, pipeline_runs, extractions, chunks
from docagentline.db.connection import DatabaseManager
from docagentline.observability import get_logger

logger = get_logger(__name__)


class MetricsAndAuditStage:
    """Metrics and audit stage."""

    def __init__(self):
        self.db_manager = DatabaseManager()

    async def execute(self, document_id: int):
        """Execute metrics and audit stage."""
        async with self.db_manager.get_connection() as conn:
            # Aggregate metrics
            result = await conn.execute(
                select(extractions, chunks)
                .join(chunks, extractions.c.chunk_id == chunks.c.id)
                .where(chunks.c.document_id == document_id)
            )
            extraction_rows = result.fetchall()

            total_tokens_in = sum(row.tokens_in for row in extraction_rows)
            total_tokens_out = sum(row.tokens_out for row in extraction_rows)
            total_cost = sum(row.cost_usd for row in extraction_rows)
            valid_count = sum(1 for row in extraction_rows if row.is_valid)
            invalid_count = len(extraction_rows) - valid_count

            await conn.execute(
                update(documents)
                .where(documents.c.id == document_id)
                .values(status="completed", updated_at=datetime.utcnow())
            )
            await conn.commit()

            logger.info(
                "Metrics and audit completed",
                extra={
                    "document_id": document_id,
                    "total_tokens_in": total_tokens_in,
                    "total_tokens_out": total_tokens_out,
                    "total_cost_usd": total_cost,
                    "valid_extractions": valid_count,
                    "invalid_extractions": invalid_count,
                },
            )
