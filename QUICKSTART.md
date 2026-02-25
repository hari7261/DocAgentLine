# DocAgentLine Quick Start

## Installation

```bash
# Clone repository
git clone <repository-url>
cd docagentline

# Install dependencies
pip install -e .

# Or using make
make install
```

## Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys
# Required:
# - LLM_API_KEY (OpenAI or compatible)
# - EMBEDDING_API_KEY (OpenAI or compatible)
```

## Database Setup

```bash
# Initialize database
python scripts/init_db.py

# Or run migrations
alembic upgrade head
```

## Create Schema

Create a JSON schema in `schemas/` directory:

```bash
# Example: schemas/my_schema_v1.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "field1": {"type": "string"},
    "field2": {"type": "number"}
  },
  "required": ["field1"]
}
```

## Usage

### CLI

```bash
# Submit document
docagentline submit --source document.pdf --schema my_schema_v1 --wait

# Check status
docagentline status --document-id 1

# Get results
docagentline results --document-id 1 --output results.json

# View metrics
docagentline metrics --document-id 1
```

### API

```bash
# Start API server
python scripts/run_api.py

# Or using uvicorn directly
uvicorn docagentline.app.api.main:app --reload

# Submit document
curl -X POST http://localhost:8000/api/v1/documents \
  -F "file=@document.pdf" \
  -F "schema_version=my_schema_v1"

# Check status
curl http://localhost:8000/api/v1/documents/1/status

# Get results
curl http://localhost:8000/api/v1/documents/1/extractions

# Get metrics
curl http://localhost:8000/api/v1/documents/1/metrics
```

## Docker

```bash
# Build image
docker build -t docagentline:latest .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop
docker-compose down
```

## Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=docagentline --cov-report=html

# Or using make
make test
```

## Example Workflow

1. **Prepare document**: Have a PDF, image, or text file ready

2. **Create schema**: Define JSON schema for extraction in `schemas/`

3. **Submit document**:
   ```bash
   docagentline submit --source invoice.pdf --schema invoice_v1 --wait
   ```

4. **Check results**:
   ```bash
   docagentline results --document-id 1 --output invoice_results.json
   ```

5. **Review metrics**:
   ```bash
   docagentline metrics --document-id 1
   ```

## Common Issues

### "Module not found" errors

```bash
# Ensure package is installed
pip install -e .
```

### Database errors

```bash
# Reinitialize database
rm docagentline.db
python scripts/init_db.py
```

### API key errors

```bash
# Check .env file has correct keys
cat .env | grep API_KEY
```

### Tesseract not found (for OCR)

```bash
# Install tesseract
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr

# macOS:
brew install tesseract

# Windows:
# Download from https://github.com/UB-Mannheim/tesseract/wiki
```

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Read [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- Customize schemas for your use case
- Configure LLM provider settings
- Set up monitoring and logging
- Scale with multiple workers

## Support

For issues and questions:
- Check logs in structured JSON format
- Review error messages in pipeline_runs table
- Enable DEBUG logging for detailed output
