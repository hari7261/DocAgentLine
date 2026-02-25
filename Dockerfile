FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY docagentline/ docagentline/
COPY migrations/ migrations/
COPY alembic.ini .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create directories
RUN mkdir -p /app/storage /app/schemas

# Expose API port
EXPOSE 8000

# Run API server
CMD ["uvicorn", "docagentline.app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
