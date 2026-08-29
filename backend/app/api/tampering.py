"""
VeriGate Backend — Tampering API

Endpoints for running document tampering analysis.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from supabase import Client

from app.core.database import get_db
from app.database import repositories as repo
from app.schemas.tampering import TamperingResponse, TamperingSignalResponse
from app.services.tampering_pipeline import run_tampering_pipeline

router = APIRouter(prefix="/tampering", tags=["tampering"])


@router.post("/analyze/{session_id}", response_model=TamperingResponse)
async def analyze_tampering(
    session_id: str,
    file: UploadFile = File(..., description="Document image (JPEG, PNG)"),
    db: Client = Depends(get_db),
) -> TamperingResponse:
    """Run tampering analysis on a document image for a specific session.
    
    Accepts the document image upload, runs ELA and metadata checks,
    fuses the signals, generates an evidence heatmap, and stores the results.
    """
    # Verify session exists
    session = repo.get_screening_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Screening session not found")

    # Validate file type
    if file.content_type and file.content_type not in (
        "image/jpeg", "image/png", "image/jpg", "image/webp", "image/tiff",
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Use JPEG, PNG, WebP, or TIFF.",
        )

    # Read uploaded file
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    try:
        result = run_tampering_pipeline(
            session_id=session_id,
            image_bytes=image_bytes,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tampering analysis failed: {e}")

    return TamperingResponse(
        session_id=session_id,
        tamper_score=result.tamper_score,
        is_suspicious=result.is_suspicious,
        processing_time_ms=result.processing_time_ms,
        signals=[
            TamperingSignalResponse(
                signal_type=s.signal_type,
                signal_name=s.signal_name,
                score=s.score,
                is_suspicious=s.is_suspicious,
                details=s.details,
                evidence_image_path=s.to_db_dict(session_id).get("evidence_image_path"),
                message=s.message,
            )
            for s in result.signals
        ],
    )
