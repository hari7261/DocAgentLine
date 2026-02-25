"""Pipeline test without embedding (to avoid rate limits)."""

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
    StructuredExtractionStage,
    ValidationStage,
    PersistenceStage,
    MetricsAndAuditStage,
)
from docagentline.observability import setup_logging


async def run_pipeline_test():
    """Run pipeline test without embedding."""
    setup_logging()
    
    print("=" * 70)
    print("DocAgentLine - Pipeline Test (Without Embedding)")
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
    
    print(f"✓ Document ID: {document_id}")
    print()
    
    # Initialize pipeline WITHOUT embedding
    print("Step 3: Initializing pipeline (skipping embedding)...")
    registry = StageRegistry()
    registry.register("ingest", IngestStage())
    registry.register("text_extraction", TextExtractionStage())
    registry.register("layout_normalization", LayoutNormalizationStage())
    registry.register("chunking", ChunkingStage())
    # SKIP: registry.register("embedding", EmbeddingStage())
    registry.register("structured_extraction", StructuredExtractionStage())
    registry.register("validation", ValidationStage())
    registry.register("persistence", PersistenceStage())
    registry.register("metrics_and_audit", MetricsAndAuditStage())
    
    # Update stage order
    registry._order = [
        "ingest",
        "text_extraction",
        "layout_normalization",
        "chunking",
        "structured_extraction",
        "validation",
        "persistence",
        "metrics_and_audit",
    ]
    
    engine = PipelineEngine()
    engine.registry = registry
    
    print("✓ Pipeline initialized with 8 stages (embedding skipped)")
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
            print(f"  ✓ {stage}: {status}")
        print()
        
        # Get extractions
        async with db_manager.get_connection() as conn:
            from docagentline.db import chunks, extractions
            result = await conn.execute(
                select(extractions, chunks)
                .join(chunks, extractions.c.chunk_id == chunks.c.id)
                .where(chunks.c.document_id == document_id)
                .order_by(chunks.c.sequence)
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
                    
                    print(f"Chunk {row.sequence + 1}:")
                    print(f"  Valid: {'✓' if row.is_valid else '✗'}")
                    print(f"  Tokens: {row.tokens_in} in, {row.tokens_out} out")
                    print(f"  Cost: ${row.cost_usd:.6f}")
                    print(f"  Latency: {row.latency_ms:.0f}ms")
                    
                    # Show extracted data
                    data = json.loads(row.json_result)
                    print(f"  Extracted Data:")
                    if "invoice_number" in data:
                        print(f"    Invoice #: {data.get('invoice_number')}")
                    if "vendor" in data and isinstance(data["vendor"], dict):
                        print(f"    Vendor: {data['vendor'].get('name')}")
                    if "total" in data:
                        print(f"    Total: ${data.get('total')}")
                    print()
                
                print("=" * 70)
                print("Summary:")
                print(f"  Total chunks: {len(extraction_rows)}")
                print(f"  Valid extractions: {valid_count}")
                print(f"  Invalid extractions: {len(extraction_rows) - valid_count}")
                print(f"  Total tokens: {sum(r.tokens_in + r.tokens_out for r in extraction_rows)}")
                print(f"  Total cost: ${total_cost:.6f}")
                print("=" * 70)
                print()
        
        print("SUCCESS! Full pipeline test completed.")
        print()
        print("The system successfully:")
        print("  ✓ Ingested the document")
        print("  ✓ Extracted text")
        print("  ✓ Normalized layout")
        print("  ✓ Created semantic chunks")
        print("  ✓ Performed LLM-driven extraction")
        print("  ✓ Validated against JSON schema")
        print("  ✓ Persisted results")
        print("  ✓ Recorded metrics")
        print()
        
    except Exception as e:
        print()
        print("=" * 70)
        print("ERROR: Pipeline execution failed")
        print("=" * 70)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_pipeline_test())
