"""Complete end-to-end pipeline test."""

import asyncio
import json
from datetime import datetime
from sqlalchemy import insert, select

from docagentline.db import documents, raw_content
from docagentline.db.connection import DatabaseManager
from docagentline.storage import ContentHasher
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
from docagentline.observability import setup_logging


async def run_full_pipeline_test():
    """Run complete pipeline test."""
    setup_logging()
    
    print("=" * 70)
    print("DocAgentLine - Full Pipeline Test")
    print("=" * 70)
    print()
    
    db_manager = DatabaseManager()
    hasher = ContentHasher()
    
    # Read test file
    print("Step 1: Reading test invoice...")
    with open("test_invoice.txt", "rb") as f:
        content = f.read()
    
    content_hash = hasher.hash_content(content)
    print(f"✓ File read: {len(content)} bytes")
    print(f"✓ Content hash: {content_hash[:16]}...")
    print()
    
    # Create document record
    print("Step 2: Creating document record...")
    async with db_manager.get_connection() as conn:
        result = await conn.execute(
            insert(documents).values(
                source="test_invoice.txt",
                content_hash=content_hash,
                schema_version="invoice_v1",
                status="pending",
                file_size_bytes=len(content),
                mime_type="text/plain",
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
    
    print(f"✓ Document created with ID: {document_id}")
    print()
    
    # Initialize pipeline
    print("Step 3: Initializing pipeline...")
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
    
    print("✓ Pipeline initialized with 9 stages")
    print()
    
    # Execute pipeline
    print("Step 4: Executing pipeline...")
    print("-" * 70)
    
    try:
        results = await engine.execute_pipeline(document_id)
        
        print("-" * 70)
        print()
        print("✓ Pipeline completed successfully!")
        print()
        
        # Show results
        print("Pipeline Results:")
        for stage, status in results.items():
            print(f"  {stage}: {status}")
        print()
        
        # Get final document status
        async with db_manager.get_connection() as conn:
            result = await conn.execute(
                select(documents).where(documents.c.id == document_id)
            )
            doc = result.fetchone()
            
            print("Final Document Status:")
            print(f"  Status: {doc.status}")
            print(f"  Updated: {doc.updated_at}")
            print()
            
            # Get extractions
            from docagentline.db import chunks, extractions
            result = await conn.execute(
                select(extractions, chunks)
                .join(chunks, extractions.c.chunk_id == chunks.c.id)
                .where(chunks.c.document_id == document_id)
            )
            extraction_rows = result.fetchall()
            
            if extraction_rows:
                print(f"Extractions: {len(extraction_rows)} chunks processed")
                print()
                
                total_cost = 0.0
                valid_count = 0
                
                for row in extraction_rows:
                    if row.is_valid:
                        valid_count += 1
                    total_cost += row.cost_usd
                    
                    print(f"Chunk {row.sequence}:")
                    print(f"  Valid: {row.is_valid}")
                    print(f"  Tokens: {row.tokens_in} in, {row.tokens_out} out")
                    print(f"  Cost: ${row.cost_usd:.6f}")
                    print(f"  Latency: {row.latency_ms:.2f}ms")
                    
                    # Show extracted data
                    data = json.loads(row.json_result)
                    print(f"  Extracted Data:")
                    for key, value in list(data.items())[:3]:  # Show first 3 fields
                        print(f"    {key}: {value}")
                    print()
                
                print("Summary:")
                print(f"  Total chunks: {len(extraction_rows)}")
                print(f"  Valid extractions: {valid_count}")
                print(f"  Invalid extractions: {len(extraction_rows) - valid_count}")
                print(f"  Total cost: ${total_cost:.6f}")
                print()
        
        print("=" * 70)
        print("SUCCESS! Full pipeline test completed.")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Check the database: docagentline.db")
        print("2. Review logs for detailed execution info")
        print("3. Try the CLI: python -m docagentline.cli.main status --document-id", document_id)
        print("4. Start the API: python scripts/run_api.py")
        
    except Exception as e:
        print()
        print("=" * 70)
        print("ERROR: Pipeline execution failed")
        print("=" * 70)
        print(f"Error: {str(e)}")
        print()
        print("This might be due to:")
        print("1. Invalid API key")
        print("2. Network connectivity issues")
        print("3. Rate limiting")
        print()
        print("Check the logs for more details.")
        raise


if __name__ == "__main__":
    asyncio.run(run_full_pipeline_test())
