"""Metrics endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func

from docagentline.db import documents, pipeline_runs, metrics, chunks, extractions
from docagentline.db.connection import DatabaseManager
from docagentline.observability import get_logger

router = APIRouter()
logger = get_logger(__name__)


class StageMetrics(BaseModel):
    """Stage metrics."""

    stage: str
    latency_ms: float
    tokens_in: int | None
    tokens_out: int | None
    cost_usd: float | None


class DocumentMetrics(BaseModel):
    """Document metrics response."""

    document_id: int
    total_latency_ms: float
    total_tokens_in: int
    total_tokens_out: int
    total_cost_usd: float
    chunk_count: int
    extraction_count: int
    valid_extraction_count: int
    invalid_extraction_count: int
    stage_metrics: list[StageMetrics]


@router.get("/documents/{document_id}/metrics", response_model=DocumentMetrics)
async def get_document_metrics(document_id: int):
    """Get metrics for document processing.

    Args:
        document_id: Document ID

    Returns:
        Comprehensive metrics for document processing
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

        # Get stage metrics
        result = await conn.execute(
            select(metrics, pipeline_runs)
            .join(pipeline_runs, metrics.c.run_id == pipeline_runs.c.id)
            .where(pipeline_runs.c.document_id == document_id)
            .order_by(metrics.c.created_at)
        )
        metric_rows = result.fetchall()

        stage_metrics_list = [
            StageMetrics(
                stage=row.stage,
                latency_ms=row.latency_ms,
                tokens_in=row.tokens_in,
                tokens_out=row.tokens_out,
                cost_usd=row.cost_usd,
            )
            for row in metric_rows
        ]

        # Get chunk count
        result = await conn.execute(
            select(func.count(chunks.c.id)).where(chunks.c.document_id == document_id)
        )
        chunk_count = result.scalar() or 0

        # Get extraction metrics
        result = await conn.execute(
            select(
                func.count(extractions.c.id).label("total"),
                func.sum(extractions.c.tokens_in).label("tokens_in"),
                func.sum(extractions.c.tokens_out).label("tokens_out"),
                func.sum(extractions.c.cost_usd).label("cost"),
                func.sum(func.cast(extractions.c.is_valid, type_=func.Integer())).label("valid"),
            )
            .select_from(extractions)
            .join(chunks, extractions.c.chunk_id == chunks.c.id)
            .where(chunks.c.document_id == document_id)
        )
        extraction_stats = result.fetchone()

        total_extractions = extraction_stats.total or 0
        total_tokens_in = extraction_stats.tokens_in or 0
        total_tokens_out = extraction_stats.tokens_out or 0
        total_cost = extraction_stats.cost or 0.0
        valid_count = extraction_stats.valid or 0
        invalid_count = total_extractions - valid_count

        # Calculate total latency
        total_latency = sum(m.latency_ms for m in stage_metrics_list)

        return DocumentMetrics(
            document_id=document_id,
            total_latency_ms=total_latency,
            total_tokens_in=total_tokens_in,
            total_tokens_out=total_tokens_out,
            total_cost_usd=total_cost,
            chunk_count=chunk_count,
            extraction_count=total_extractions,
            valid_extraction_count=valid_count,
            invalid_extraction_count=invalid_count,
            stage_metrics=stage_metrics_list,
        )
