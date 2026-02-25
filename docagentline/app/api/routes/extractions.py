"""Extraction results endpoints."""

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from docagentline.db import documents, chunks, extractions, validation_errors
from docagentline.db.connection import DatabaseManager
from docagentline.observability import get_logger

router = APIRouter()
logger = get_logger(__name__)


class ValidationErrorDetail(BaseModel):
    """Validation error detail."""

    json_path: str
    message: str


class ExtractionResult(BaseModel):
    """Extraction result."""

    chunk_id: int
    sequence: int
    json_result: dict
    is_valid: bool
    validation_errors: list[ValidationErrorDetail]
    latency_ms: float
    tokens_in: int
    tokens_out: int
    cost_usd: float


class DocumentExtractions(BaseModel):
    """Document extractions response."""

    document_id: int
    schema_version: str
    extractions: list[ExtractionResult]
    total_cost_usd: float


@router.get("/documents/{document_id}/extractions", response_model=DocumentExtractions)
async def get_document_extractions(document_id: int):
    """Get extraction results for document.

    Args:
        document_id: Document ID

    Returns:
        All extraction results with validation status
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

        # Get extractions
        result = await conn.execute(
            select(extractions, chunks)
            .join(chunks, extractions.c.chunk_id == chunks.c.id)
            .where(chunks.c.document_id == document_id)
            .order_by(chunks.c.sequence)
        )
        extraction_rows = result.fetchall()

        results = []
        total_cost = 0.0

        for row in extraction_rows:
            # Get validation errors
            error_result = await conn.execute(
                select(validation_errors).where(
                    validation_errors.c.extraction_id == row.id
                )
            )
            error_rows = error_result.fetchall()

            errors = [
                ValidationErrorDetail(
                    json_path=err.json_path,
                    message=err.message,
                )
                for err in error_rows
            ]

            results.append(
                ExtractionResult(
                    chunk_id=row.chunk_id,
                    sequence=row.sequence,
                    json_result=json.loads(row.json_result),
                    is_valid=row.is_valid,
                    validation_errors=errors,
                    latency_ms=row.latency_ms,
                    tokens_in=row.tokens_in,
                    tokens_out=row.tokens_out,
                    cost_usd=row.cost_usd,
                )
            )

            total_cost += row.cost_usd

        return DocumentExtractions(
            document_id=document_id,
            schema_version=doc.schema_version,
            extractions=results,
            total_cost_usd=total_cost,
        )
