"""FastAPI application factory for Digital Literacy Bridge."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router as api_router
from config.database import create_tables
from config.settings import get_dlb_settings
from utils.content_loader import ContentLoader


def create_app() -> FastAPI:
    """
    Application factory for Digital Literacy Bridge.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_dlb_settings()

    app = FastAPI(
        title="Digital Literacy Bridge",
        description="An accessible platform for digital literacy education",
        version="0.1.0",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.dlb_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files
    static_dir = Path(__file__).parent.parent / "frontend" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Include API routes
    app.include_router(api_router)

    # Root endpoint - serve the SPA index.html
    @app.get("/", include_in_schema=False)
    async def serve_spa():
        index_path = Path(__file__).parent.parent / "frontend" / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {
            "message": "Digital Literacy Bridge API",
            "docs": "/docs",
            "api": "/api/v1",
        }

    # Startup event: create database tables if they don't exist
    @app.on_event("startup")
    async def startup_event():
        logger = getattr(app, "logger", None)
        try:
            await create_tables()
            if logger:
                logger.info("Database tables created successfully")
            # Pre-warm content loader cache
            ContentLoader()
            if logger:
                logger.info("Content loader initialized")
        except Exception as e:
            if logger:
                logger.error(f"Failed to initialize database: {e}")
            else:
                print(f"Failed to initialize database: {e}")

    return app


# Global app instance for uvicorn
app = create_app()
