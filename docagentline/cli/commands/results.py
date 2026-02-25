"""Results command."""

import asyncio
import json
from pathlib import Path

import click
from sqlalchemy import select

from docagentline.db import documents, chunks, extractions
from docagentline.db.connection import DatabaseManager


@click.command()
@click.option("--document-id", required=True, type=int, help="Document ID")
@click.option("--output", required=True, type=click.Path(), help="Output file path")
def results(document_id: int, output: str):
    """Retrieve extraction results."""
    asyncio.run(get_results(document_id, output))


async def get_results(document_id: int, output_path: str):
    """Get results async."""
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

        # Get extractions
        result = await conn.execute(
            select(extractions, chunks)
            .join(chunks, extractions.c.chunk_id == chunks.c.id)
            .where(chunks.c.document_id == document_id)
            .order_by(chunks.c.sequence)
        )
        extraction_rows = result.fetchall()

        results = {
            "document_id": document_id,
            "source": doc.source,
            "schema_version": doc.schema_version,
            "status": doc.status,
            "extractions": [],
        }

        for row in extraction_rows:
            results["extractions"].append({
                "chunk_id": row.chunk_id,
                "sequence": row.sequence,
                "data": json.loads(row.json_result),
                "is_valid": row.is_valid,
                "tokens_in": row.tokens_in,
                "tokens_out": row.tokens_out,
                "cost_usd": row.cost_usd,
            })

        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        click.echo(f"Results written to: {output_path}")
        click.echo(f"Total extractions: {len(results['extractions'])}")
