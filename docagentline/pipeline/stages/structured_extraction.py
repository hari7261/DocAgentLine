"""Structured extraction stage - LLM-driven extraction."""

import asyncio
import json
from datetime import datetime

from sqlalchemy import select, update, insert, delete

from docagentline.config import get_settings
from docagentline.db import documents, chunks, extractions, prompts
from docagentline.db.connection import DatabaseManager
from docagentline.observability import get_logger
from docagentline.services.llm import get_llm_provider
from docagentline.services.validation import SchemaRegistry
from docagentline.storage import ContentHasher
from docagentline.utils.errors import ExtractionError

logger = get_logger(__name__)


class StructuredExtractionStage:
    """Structured extraction stage."""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.settings = get_settings()
        self.schema_registry = SchemaRegistry()
        self.hasher = ContentHasher()
        self.provider = None
        self.max_concurrent = self.settings.pipeline_max_concurrent_chunks

    async def execute(self, document_id: int):
        """Execute structured extraction stage."""
        self.provider = get_llm_provider()

        try:
            async with self.db_manager.get_connection() as conn:
                # Get document
                result = await conn.execute(
                    select(documents).where(documents.c.id == document_id)
                )
                doc = result.fetchone()

                if not doc:
                    raise ExtractionError(
                        f"Document not found: {document_id}",
                        details={"document_id": document_id},
                    )

                schema_version = doc.schema_version
                schema = self.schema_registry.get_schema(schema_version)

                # Get all chunks
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

                # Delete existing extractions for these chunks
                chunk_ids = [row.id for row in chunk_rows]
                await conn.execute(
                    delete(extractions).where(extractions.c.chunk_id.in_(chunk_ids))
                )
                await conn.commit()

                # Process chunks with concurrency control
                semaphore = asyncio.Semaphore(self.max_concurrent)

                async def process_chunk(chunk_row):
                    async with semaphore:
                        await self._process_chunk(conn, chunk_row, schema, schema_version)

                await asyncio.gather(*[process_chunk(row) for row in chunk_rows])

                await conn.execute(
                    update(documents)
                    .where(documents.c.id == document_id)
                    .values(status="extracted", updated_at=datetime.utcnow())
                )
                await conn.commit()

                logger.info(
                    "Structured extraction completed",
                    extra={
                        "document_id": document_id,
                        "chunk_count": len(chunk_rows),
                        "schema_version": schema_version,
                    },
                )

        finally:
            if self.provider:
                await self.provider.close()

    async def _process_chunk(self, conn, chunk_row, schema, schema_version):
        """Process single chunk."""
        chunk_id = chunk_row.id
        chunk_text = chunk_row.text

        # Build prompt
        prompt = self._build_prompt(chunk_text)
        prompt_hash = self.hasher.hash_string(prompt)

        # Call LLM
        response = await self.provider.generate_structured(
            prompt=prompt,
            schema=schema,
            temperature=self.settings.llm_temperature,
            max_tokens=self.settings.llm_max_tokens,
        )

        # Calculate cost
        cost_usd = self._calculate_cost(response.tokens_in, response.tokens_out)

        # Store extraction (validation happens in next stage)
        result = await conn.execute(
            insert(extractions).values(
                chunk_id=chunk_id,
                schema_version=schema_version,
                model=self.settings.llm_model,
                json_result=json.dumps(response.parsed_json),
                is_valid=False,  # Will be validated in next stage
                latency_ms=response.latency_ms,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                cost_usd=cost_usd,
                prompt_hash=prompt_hash,
                raw_response=response.raw_response if self.settings.storage_persist_raw_responses else None,
                created_at=datetime.utcnow(),
            )
        )
        extraction_id = result.inserted_primary_key[0]

        # Store prompt if configured
        if self.settings.storage_persist_prompts:
            await conn.execute(
                insert(prompts).values(
                    extraction_id=extraction_id,
                    prompt_text=prompt,
                    prompt_hash=prompt_hash,
                    created_at=datetime.utcnow(),
                )
            )

        await conn.commit()

        logger.debug(
            "Chunk extracted",
            extra={
                "chunk_id": chunk_id,
                "extraction_id": extraction_id,
                "tokens_in": response.tokens_in,
                "tokens_out": response.tokens_out,
                "cost_usd": cost_usd,
            },
        )

    def _build_prompt(self, text: str) -> str:
        """Build extraction prompt."""
        return f"""Extract structured information from the following text.
Return only valid JSON that conforms to the provided schema.

Text:
{text}
"""

    def _calculate_cost(self, tokens_in: int, tokens_out: int) -> float:
        """Calculate cost in USD."""
        cost_in = (tokens_in / 1000) * self.settings.cost_per_1k_input_tokens
        cost_out = (tokens_out / 1000) * self.settings.cost_per_1k_output_tokens
        return cost_in + cost_out
