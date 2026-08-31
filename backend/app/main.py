r"""
VeriGate Backend — Main Application
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    # Allow all origins for the hackathon MVP
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    # The approved plain-HTML frontend and locally generated ELA evidence are
    # served by the API process during local development.  The API remains the
    # source of truth; this only makes the browser assets reachable.
    repository_root = Path(__file__).resolve().parents[2]
    app.mount(
        "/frontend",
        StaticFiles(directory=repository_root / "frontend", html=True),
        name="frontend",
    )
    app.mount(
        "/evidence",
        StaticFiles(directory=repository_root / "backend" / "evidence"),
        name="evidence",
    )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
