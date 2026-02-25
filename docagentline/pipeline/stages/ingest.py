"""Ingest stage - validate and store document."""

from datetime import datetime

from sqlalchemy import select, update

from docagentline.db import documents, raw_content
from docagentline.db.connection import DatabaseManager
from docagentline.observability import get_logger
from docagentline.storage import ContentHasher
from docagentline.utils.errors import PipelineStateError

logger = get_logger(__name__)


class IngestStage:
    """Ingest stage."""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.hasher = ContentHasher()

    async def execute(self, document_id: int):
        """Execute ingest stage."""
        async with self.db_manager.get_connection() as conn:
            # Get document
            result = await conn.execute(
                select(documents).where(documents.c.id == document_id)
            )
            doc = result.fetchone()

            if not doc:
                raise PipelineStateError(
                    f"Document not found: {document_id}",
                    details={"document_id": document_id},
                )

            # Get raw content
            result = await conn.execute(
                select(raw_content).where(raw_content.c.document_id == document_id)
            )
            content_row = result.fetchone()

            if not content_row:
                raise PipelineStateError(
                    f"Raw content not found for document: {document_id}",
                    details={"document_id": document_id},
                )

            # Verify content hash
            content = content_row.content
            computed_hash = self.hasher.hash_content(content)

            if computed_hash != doc.content_hash:
                raise PipelineStateError(
                    "Content hash mismatch",
                    details={
                        "document_id": document_id,
                        "expected": doc.content_hash,
                        "computed": computed_hash,
                    },
                )

            # Update document status
            await conn.execute(
                update(documents)
                .where(documents.c.id == document_id)
                .values(status="ingested", updated_at=datetime.utcnow())
            )
            await conn.commit()

            logger.info(
                "Document ingested successfully",
                extra={
                    "document_id": document_id,
                    "content_size": len(content),
                    "content_hash": computed_hash,
                },
            )
