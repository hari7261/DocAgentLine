"""Document status endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from docagentline.db import documents, pipeline_runs
from docagentline.db.connection import DatabaseManager
from docagentline.observability import get_logger

router = APIRouter()
logger = get_logger(__name__)


class StageStatus(BaseModel):
    """Stage status."""

    stage: str
    status: str
    attempt: int
    started_at: datetime
    finished_at: datetime | None
    error_type: str | None
    error_message: str | None


class DocumentStatus(BaseModel):
    """Document status response."""

    document_id: int
    source: str
    schema_version: str
    status: str
    created_at: datetime
    updated_at: datetime
    stages: list[StageStatus]


@router.get("/documents/{document_id}/status", response_model=DocumentStatus)
async def get_document_status(document_id: int):
    """Get document processing status.

    Args:
        document_id: Document ID

    Returns:
        Document status with stage details
    """
    db_manager = DatabaseManager()

    async with db_manager.get_connection() as conn:
        # Get document
        result = await conn.execute(
            select(documents).where(documents.c.id == document_id)
        )
        doc = result.fetchone()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get pipeline runs
        result = await conn.execute(
            select(pipeline_runs)
            .where(pipeline_runs.c.document_id == document_id)
            .order_by(pipeline_runs.c.started_at)
        )
        runs = result.fetchall()

        stages = [
            StageStatus(
                stage=run.stage,
                status=run.status,
                attempt=run.attempt,
                started_at=run.started_at,
                finished_at=run.finished_at,
                error_type=run.error_type,
                error_message=run.error_message,
            )
            for run in runs
        ]

        return DocumentStatus(
            document_id=doc.id,
            source=doc.source,
            schema_version=doc.schema_version,
            status=doc.status,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            stages=stages,
        )
