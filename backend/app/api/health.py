"""
VeriGate Backend — Health API
"""

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.config import get_settings, Settings
from app.core.database import get_db
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(
    settings: Settings = Depends(get_settings),
    db: Client = Depends(get_db),
) -> HealthResponse:
    """Health check endpoint.

    Verifies the API is running and can connect to the database.
    """
    db_connected = False
    try:
        # Quick connectivity check — count rows in a small table
        result = db.table("reference_documents").select("id", count="exact").limit(1).execute()
        db_connected = True
    except Exception:
        db_connected = False

    return HealthResponse(
        status="ok" if db_connected else "degraded",
        app_name=settings.app_name,
        version=settings.app_version,
        database_connected=db_connected,
    )
