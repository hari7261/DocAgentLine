"""Document submission endpoints."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import insert

from docagentline.config import get_settings
from docagentline.db import documents, raw_content
from docagentline.db.connection import DatabaseManager
from docagentline.observability import get_logger
from docagentline.storage import FileHandler, ContentHasher
from docagentline.pipeline.engine import PipelineEngine
from docagentline.pipeline.registry import StageRegistry
from docagentline.pipeline.stages import (
    IngestStage,
    TextExtractionStage,
    LayoutNormalizationStage,
    ChunkingStage,
    EmbeddingStage,
    StructuredExtractionStage,
    ValidationStage,
    PersistenceStage,
    MetricsAndAuditStage,
)

router = APIRouter()
logger = get_logger(__name__)


class DocumentSubmitResponse(BaseModel):
    """Document submission response."""

    document_id: int
    correlation_id: str
    status: str


async def run_pipeline(document_id: int, correlation_id: str):
    """Run pipeline in background."""
    # Initialize stages
    registry = StageRegistry()
    registry.register("ingest", IngestStage())
    registry.register("text_extraction", TextExtractionStage())
    registry.register("layout_normalization", LayoutNormalizationStage())
    registry.register("chunking", ChunkingStage())
    registry.register("embedding", EmbeddingStage())
    registry.register("structured_extraction", StructuredExtractionStage())
    registry.register("validation", ValidationStage())
    registry.register("persistence", PersistenceStage())
    registry.register("metrics_and_audit", MetricsAndAuditStage())

    engine = PipelineEngine()
    engine.registry = registry

    try:
        await engine.execute_pipeline(document_id, correlation_id)
    except Exception as e:
        logger.error(
            "Pipeline execution failed",
            extra={
                "document_id": document_id,
                "correlation_id": correlation_id,
                "error": str(e),
            },
            exc_info=True,
        )


@router.post("/documents", response_model=DocumentSubmitResponse)
async def submit_document(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    schema_version: Annotated[str, Form()],
):
    """Submit document for processing.

    Args:
        file: Document file
        schema_version: Schema version to use for extraction

    Returns:
        Document submission response
    """
    settings = get_settings()
    file_handler = FileHandler()
    hasher = ContentHasher()
    db_manager = DatabaseManager()

    correlation_id = str(uuid.uuid4())

    try:
        # Read file content
        content = await file.read()

        # Check size
        max_size = settings.storage_max_file_size_mb * 1024 * 1024
        if len(content) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {len(content)} bytes (max: {max_size})",
            )

        # Calculate hash
        content_hash = hasher.hash_content(content)

        # Detect MIME type
        mime_type = file.content_type or "application/octet-stream"

        # Check for existing document with same hash and schema
        async with db_manager.get_connection() as conn:
            from sqlalchemy import select

            result = await conn.execute(
                select(documents).where(
                    documents.c.content_hash == content_hash,
                    documents.c.schema_version == schema_version,
                )
            )
            existing = result.fetchone()

            if existing:
                logger.info(
                    "Document already exists",
                    extra={
                        "document_id": existing.id,
                        "content_hash": content_hash,
                        "schema_version": schema_version,
                    },
                )
                return DocumentSubmitResponse(
                    document_id=existing.id,
                    correlation_id=correlation_id,
                    status=existing.status,
                )

            # Create document record
            result = await conn.execute(
                insert(documents).values(
                    source=file.filename or "upload",
                    content_hash=content_hash,
                    schema_version=schema_version,
                    status="pending",
                    file_size_bytes=len(content),
                    mime_type=mime_type,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            )
            document_id = result.inserted_primary_key[0]

            # Store raw content
            await conn.execute(
                insert(raw_content).values(
                    document_id=document_id,
                    content=content,
                    is_hashed=settings.storage_hash_raw_content,
                    created_at=datetime.utcnow(),
                )
            )

            await conn.commit()

            logger.info(
                "Document submitted",
                extra={
                    "document_id": document_id,
                    "correlation_id": correlation_id,
                    "schema_version": schema_version,
                    "file_size": len(content),
                },
            )

            # Start pipeline in background
            background_tasks.add_task(run_pipeline, document_id, correlation_id)

            return DocumentSubmitResponse(
                document_id=document_id,
                correlation_id=correlation_id,
                status="pending",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to submit document",
            extra={"error": str(e), "correlation_id": correlation_id},
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to submit document: {str(e)}")
