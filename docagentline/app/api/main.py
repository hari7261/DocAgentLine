"""FastAPI application."""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from docagentline.config import get_settings
from docagentline.db import close_db
from docagentline.observability import setup_logging
from docagentline.app.api.routes import documents, status, extractions, metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    setup_logging()
    yield
    await close_db()


app = FastAPI(
    title="DocAgentLine",
    description="Production document extraction pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()

if settings.api_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(status.router, prefix="/api/v1", tags=["status"])
app.include_router(extractions.router, prefix="/api/v1", tags=["extractions"])
app.include_router(metrics.router, prefix="/api/v1", tags=["metrics"])


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
