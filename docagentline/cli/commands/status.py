"""Status command."""

import asyncio

import click
from sqlalchemy import select

from docagentline.db import documents, pipeline_runs
from docagentline.db.connection import DatabaseManager


@click.command()
@click.option("--document-id", required=True, type=int, help="Document ID")
def status(document_id: int):
    """Check document processing status."""
    asyncio.run(get_status(document_id))


async def get_status(document_id: int):
    """Get status async."""
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
        click.echo(f"Schema: {doc.schema_version}")
        click.echo(f"Status: {doc.status}")
        click.echo(f"Created: {doc.created_at}")
        click.echo(f"Updated: {doc.updated_at}")
        click.echo()

        # Get pipeline runs
        result = await conn.execute(
            select(pipeline_runs)
            .where(pipeline_runs.c.document_id == document_id)
            .order_by(pipeline_runs.c.started_at)
        )
        runs = result.fetchall()

        if runs:
            click.echo("Pipeline Stages:")
            for run in runs:
                status_icon = "✓" if run.status == "completed" else "✗" if run.status == "failed" else "⋯"
                click.echo(f"  {status_icon} {run.stage}: {run.status} (attempt {run.attempt})")
                if run.error_message:
                    click.echo(f"    Error: {run.error_message[:100]}")
