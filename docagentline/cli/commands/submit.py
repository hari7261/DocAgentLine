"""Submit document command."""

import asyncio
from datetime import datetime
from pathlib import Path

import click
from sqlalchemy import insert

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

logger = get_logger(__name__)


@click.command()
@click.option("--source", required=True, help="Document source (file path or URL)")
@click.option("--schema", required=True, help="Schema version to use")
@click.option("--wait", is_flag=True, help="Wait for pipeline to complete")
def submit(source: str, schema: str, wait: bool):
    """Submit document for processing."""
    asyncio.run(submit_document(source, schema, wait))


async def submit_document(source: str, schema_version: str, wait: bool):
    """Submit document async."""
    file_handler = FileHandler()
    hasher = ContentHasher()
    db_manager = DatabaseManager()

    try:
        # Ingest file
        click.echo(f"Ingesting document: {source}")

        if source.startswith("http://") or source.startswith("https://"):
            content, mime_type = await file_handler.ingest_url(source)
        else:
            content, mime_type = await file_handler.ingest_local_file(source)

        content_hash = hasher.hash_content(content)

        click.echo(f"Content hash: {content_hash}")
        click.echo(f"MIME type: {mime_type}")
        click.echo(f"Size: {len(content)} bytes")

        # Create document
        async with db_manager.get_connection() as conn:
            result = await conn.execute(
                insert(documents).values(
                    source=source,
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

            await conn.execute(
                insert(raw_content).values(
                    document_id=document_id,
                    content=content,
                    is_hashed=False,
                    created_at=datetime.utcnow(),
                )
            )

            await conn.commit()

        click.echo(f"Document ID: {document_id}")

        if wait:
            click.echo("Starting pipeline execution...")

            # Initialize pipeline
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

            results = await engine.execute_pipeline(document_id)

            click.echo("Pipeline completed!")
            click.echo(f"Results: {results}")
        else:
            click.echo("Document submitted. Use 'docagentline status' to check progress.")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
