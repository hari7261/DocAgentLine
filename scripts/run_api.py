"""Run API server."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from docagentline.config import get_settings


def main():
    """Run API server."""
    settings = get_settings()

    uvicorn.run(
        "docagentline.app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
