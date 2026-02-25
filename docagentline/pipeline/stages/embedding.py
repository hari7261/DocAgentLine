"""Embedding stage - generate vector embeddings."""

import asyncio
import struct
from datetime import datetime

from sqlalchemy import select, update, insert, delete

from docagentline.config import get_settings
from docagentline.db import documents, chunks, embeddings
from docagentline.db.connection import DatabaseManager
from docagentline.observability import get_logger
from docagentline.services.embedding import get_embedding_provider
from docagentline.utils.errors import EmbeddingError

logger = get_logger(__name__)


class EmbeddingStage:
    """Embedding stage."""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.settings = get_settings()
        self.batch_size = self.settings.embedding_batch_size
        self.provider = None

    async def execute(self, document_id: int):
        """Execute embedding stage."""
        self.provider = get_embedding_provider()

        try:
            async with self.db_manager.get_connection() as conn:
                # Get all chunks for document
                result = await conn.execute(
                    select(chunks)
                    .where(chunks.c.document_id == document_id)
                    .order_by(chunks.c.sequence)
                )
                chunk_rows = result.fetchall()

                if not chunk_rows:
                    logger.warning(
                        "No chunks found for document",
                        extra={"document_id": document_id},
                    )
                    return

                # Delete existing embeddings
                chunk_ids = [row.id for row in chunk_rows]
                await conn.execute(
                    delete(embeddings).where(embeddings.c.chunk_id.in_(chunk_ids))
                )
                await conn.commit()

                # Process in batches
                for i in range(0, len(chunk_rows), self.batch_size):
                    batch = chunk_rows[i : i + self.batch_size]
                    await self._process_batch(conn, batch)

                await conn.execute(
                    update(documents)
                    .where(documents.c.id == document_id)
                    .values(status="embedded", updated_at=datetime.utcnow())
                )
                await conn.commit()

                logger.info(
                    "Embeddings generated successfully",
                    extra={
                        "document_id": document_id,
                        "chunk_count": len(chunk_rows),
                    },
                )

        finally:
            if self.provider:
                await self.provider.close()

    async def _process_batch(self, conn, batch):
        """Process batch of chunks."""
        texts = [row.text for row in batch]
        chunk_ids = [row.id for row in batch]

        # Generate embeddings
        response = await self.provider.embed_batch(texts)

        # Store embeddings
        for chunk_id, vector in zip(chunk_ids, response.vectors):
            # Serialize vector as binary
            vector_bytes = struct.pack(f"{len(vector)}f", *vector)

            await conn.execute(
                insert(embeddings).values(
                    chunk_id=chunk_id,
                    model=response.provider_metadata.get("model", "unknown"),
                    vector=vector_bytes,
                    created_at=datetime.utcnow(),
                )
            )

        await conn.commit()
