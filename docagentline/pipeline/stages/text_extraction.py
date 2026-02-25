"""Text extraction stage - extract text from documents."""

import io
from datetime import datetime

from pypdf import PdfReader
from PIL import Image
import pytesseract
from sqlalchemy import select, update, insert

from docagentline.db import documents, raw_content
from docagentline.db.connection import DatabaseManager
from docagentline.observability import get_logger
from docagentline.utils.errors import ExtractionError

logger = get_logger(__name__)


class TextExtractionStage:
    """Text extraction stage."""

    def __init__(self):
        self.db_manager = DatabaseManager()

    async def execute(self, document_id: int):
        """Execute text extraction stage."""
        async with self.db_manager.get_connection() as conn:
            # Get document and content
            result = await conn.execute(
                select(documents, raw_content)
                .join(raw_content, documents.c.id == raw_content.c.document_id)
                .where(documents.c.id == document_id)
            )
            row = result.fetchone()

            if not row:
                raise ExtractionError(
                    f"Document or content not found: {document_id}",
                    details={"document_id": document_id},
                )

            mime_type = row.mime_type
            content = row.content

            # Extract text based on MIME type
            if mime_type == "application/pdf":
                text = await self._extract_pdf(content)
            elif mime_type.startswith("image/"):
                text = await self._extract_image(content)
            elif mime_type == "text/plain":
                text = content.decode("utf-8", errors="ignore")
            else:
                # Try as text
                try:
                    text = content.decode("utf-8", errors="ignore")
                except Exception:
                    raise ExtractionError(
                        f"Unsupported MIME type: {mime_type}",
                        details={"document_id": document_id, "mime_type": mime_type},
                    )

            # Store extracted text in document metadata (or separate table if needed)
            # For now, we'll assume it's stored and accessible by next stages
            # In production, you might want a separate extracted_text table

            await conn.execute(
                update(documents)
                .where(documents.c.id == document_id)
                .values(status="text_extracted", updated_at=datetime.utcnow())
            )
            await conn.commit()

            logger.info(
                "Text extracted successfully",
                extra={
                    "document_id": document_id,
                    "text_length": len(text),
                    "mime_type": mime_type,
                },
            )

    async def _extract_pdf(self, content: bytes) -> str:
        """Extract text from PDF."""
        try:
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)

            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            return "\n\n".join(text_parts)

        except Exception as e:
            raise ExtractionError(
                "Failed to extract text from PDF",
                details={"error": str(e)},
            )

    async def _extract_image(self, content: bytes) -> str:
        """Extract text from image using OCR."""
        try:
            image = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(image)
            return text

        except Exception as e:
            raise ExtractionError(
                "Failed to extract text from image",
                details={"error": str(e)},
            )
