"""Metrics command."""

import asyncio

import click
from sqlalchemy import select, func

from docagentline.db import documents, chunks, extractions, metrics as metrics_table, pipeline_runs
from docagentline.db.connection import DatabaseManager


@click.command()
@click.option("--document-id", required=True, type=int, help="Document ID")
def metrics(document_id: int):
    """Show document processing metrics."""
    asyncio.run(get_metrics(document_id))


async def get_metrics(document_id: int):
    """Get metrics async."""
    db_manager = DatabaseManager()

    async with db_manager.get_connection() as conn:
        # Get document
        result = await conn.execute(
            select(documents).where(documents.c.id == document_id)
        )
        doc = result.fetchone()

        if not doc:
            click.echo(f"Document not found: {document_id}", err=True)
            return

        click.echo(f"Document ID: {doc.id}")
        click.echo(f"Source: {doc.source}")
        click.echo()

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
        stats = result.fetchone()

        total = stats.total or 0
        tokens_in = stats.tokens_in or 0
        tokens_out = stats.tokens_out or 0
        cost = stats.cost or 0.0
        valid = stats.valid or 0

        click.echo("Extraction Metrics:")
        click.echo(f"  Total extractions: {total}")
        click.echo(f"  Valid extractions: {valid}")
        click.echo(f"  Invalid extractions: {total - valid}")
        click.echo(f"  Total tokens (in): {tokens_in}")
        click.echo(f"  Total tokens (out): {tokens_out}")
        click.echo(f"  Total cost: ${cost:.4f}")
        click.echo()

        # Get stage metrics
        result = await conn.execute(
            select(metrics_table, pipeline_runs)
            .join(pipeline_runs, metrics_table.c.run_id == pipeline_runs.c.id)
            .where(pipeline_runs.c.document_id == document_id)
            .order_by(metrics_table.c.created_at)
        )
        metric_rows = result.fetchall()

        if metric_rows:
            click.echo("Stage Metrics:")
            for row in metric_rows:
                click.echo(f"  {row.stage}: {row.latency_ms:.2f}ms")
