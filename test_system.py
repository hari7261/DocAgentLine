"""Quick system test."""

import asyncio
from datetime import datetime
from sqlalchemy import insert, select

from docagentline.db import documents, raw_content
from docagentline.db.connection import DatabaseManager
from docagentline.storage import ContentHasher


async def test_basic_operations():
    """Test basic database operations."""
    print("Testing DocAgentLine system...")
    print()
    
    db_manager = DatabaseManager()
    hasher = ContentHasher()
    
    # Read test file
    with open("test_invoice.txt", "rb") as f:
        content = f.read()
    
    content_hash = hasher.hash_content(content)
    print(f"✓ File read successfully ({len(content)} bytes)")
    print(f"✓ Content hash: {content_hash[:16]}...")
    print()
    
    # Create document record
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
        
        # Store raw content
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
    
    # Verify document in new connection
    async with db_manager.get_connection() as conn:
        result = await conn.execute(
            select(documents).where(documents.c.id == document_id)
        )
        doc = result.fetchone()
        
        print("Document details:")
        print(f"  ID: {doc.id}")
        print(f"  Source: {doc.source}")
        print(f"  Schema: {doc.schema_version}")
        print(f"  Status: {doc.status}")
        print(f"  Size: {doc.file_size_bytes} bytes")
        print()
        
    print("✓ All basic operations successful!")
    print()
    print("System is ready for use!")
    print()
    print("Next steps:")
    print("1. Add your LLM API keys to .env file")
    print("2. Run: docagentline submit --source test_invoice.txt --schema invoice_v1")
    print("3. Or start the API: python scripts/run_api.py")


if __name__ == "__main__":
    asyncio.run(test_basic_operations())
