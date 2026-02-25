"""Chunking stage - split text into semantic chunks."""

import re
from datetime import datetime

from sqlalchemy import select, update, insert, delete
import tiktoken

from docagentline.config import get_settings
from docagentline.db import documents, chunks, raw_content
from docagentline.db.connection import DatabaseManager
from docagentline.observability import get_logger
from docagentline.utils.errors import ChunkingError

logger = get_logger(__name__)


class ChunkingStage:
    """Chunking stage."""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.settings = get_settings()
        self.chunk_size = self.settings.chunk_size
        self.chunk_overlap = self.settings.chunk_overlap
        self.min_chunk_size = self.settings.chunk_min_size

        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None

    async def execute(self, document_id: int):
        """Execute chunking stage."""
        async with self.db_manager.get_connection() as conn:
            # Get document and extract text
            # In real implementation, text would be from text_extraction stage
            # For now, we'll get from raw_content if it's text
            result = await conn.execute(
                select(documents, raw_content)
                .join(raw_content, documents.c.id == raw_content.c.document_id)
                .where(documents.c.id == document_id)
            )
            row = result.fetchone()

            if not row:
                raise ChunkingError(
                    f"Document not found: {document_id}",
                    details={"document_id": document_id},
                )

            # Extract text (simplified - in production, get from extracted_text table)
            if row.mime_type == "text/plain":
                text = row.content.decode("utf-8", errors="ignore")
            else:
                # For other types, assume text was extracted in previous stage
                # This is simplified - in production, read from extracted_text table
                text = row.content.decode("utf-8", errors="ignore")

            # Create chunks
            text_chunks = self._create_chunks(text)

            # Delete existing chunks
            await conn.execute(
                delete(chunks).where(chunks.c.document_id == document_id)
            )

            # Insert new chunks
            for sequence, chunk_text in enumerate(text_chunks):
                token_count = self._count_tokens(chunk_text)

                await conn.execute(
                    insert(chunks).values(
                        document_id=document_id,
                        sequence=sequence,
                        text=chunk_text,
                        token_count=token_count,
                        created_at=datetime.utcnow(),
                    )
                )

            await conn.execute(
                update(documents)
                .where(documents.c.id == document_id)
                .values(status="chunked", updated_at=datetime.utcnow())
            )
            await conn.commit()

            logger.info(
                "Text chunked successfully",
                extra={
                    "document_id": document_id,
                    "chunk_count": len(text_chunks),
                },
            )

    def _create_chunks(self, text: str) -> list[str]:
        """Create overlapping chunks from text."""
        if not text:
            return []

        # Split by paragraphs first
        paragraphs = re.split(r"\n\s*\n", text)

        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_tokens = self._count_tokens(para)

            if current_size + para_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = "\n\n".join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(chunk_text)

                # Start new chunk with overlap
                if self.chunk_overlap > 0:
                    # Keep last paragraph for overlap
                    current_chunk = [current_chunk[-1]] if current_chunk else []
                    current_size = self._count_tokens(current_chunk[0]) if current_chunk else 0
                else:
                    current_chunk = []
                    current_size = 0

            current_chunk.append(para)
            current_size += para_tokens

        # Add final chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)

        return chunks if chunks else [text[:self.chunk_size]]

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Rough approximation
            return int(len(text.split()) * 1.3)
