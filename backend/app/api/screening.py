"""
VeriGate Backend — Screening API

Endpoints for creating, listing, and retrieving screening sessions.
The actual AI/CV processing pipeline is not implemented yet.
"""

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_db
from app.schemas.screening import (
    ScreeningCreateRequest,
    ScreeningResponse,
    ScreeningListItem,
    SessionStatus,
)
from app.services import screening as screening_service

router = APIRouter(prefix="/screening", tags=["screening"])


@router.post("", response_model=dict, status_code=201)
def create_screening(
    request: ScreeningCreateRequest,
    db: Client = Depends(get_db),
):
    """Create a new screening session.

    Accepts document metadata and image paths. In the future, this will
    accept file uploads and trigger the full screening pipeline.
    """
    session_data = {
        "status": SessionStatus.PENDING.value,
        "document_type": request.document_type.value,
        "operator_id": request.operator_id,
        "operator_notes": request.operator_notes,
        "document_image_path": request.document_image_path,
        "person_image_path": request.person_image_path,
    }
    session = screening_service.create_session(db, session_data)
    return {"id": session["id"], "status": session["status"], "message": "Screening session created"}


@router.get("", response_model=list[ScreeningListItem])
def list_screenings(
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
    db: Client = Depends(get_db),
):
    """List screening sessions with optional status filter."""
    sessions = screening_service.list_sessions(db, limit=limit, offset=offset, status=status)
    return sessions


@router.get("/{session_id}")
def get_screening(
    session_id: str,
    db: Client = Depends(get_db),
):
    """Get a screening session with all analysis results.

    Returns the session plus any associated document extraction,
    validation, tampering, face verification, and risk assessment data.
    """
    result = screening_service.get_session_detail(db, session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Screening session not found")
    return result
