"""
VeriGate Backend — Validation API

Endpoints for running and retrieving document validation results.
"""

import time

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_db
from app.database import repositories as repo
from app.schemas.validation import ValidationCheckResponse, ValidationResponse
from app.services.validation_pipeline import run_validation_pipeline

router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("/run/{session_id}", response_model=ValidationResponse)
def run_validation(
    session_id: str,
    db: Client = Depends(get_db),
) -> ValidationResponse:
    """Run document validation for an existing screening session.

    Requires that OCR and document extraction have already completed.
    This endpoint can be used for manual re-validation or standalone validation.
    """
    start = time.time()

    # Verify session exists
    session = repo.get_screening_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Screening session not found")

    try:
        result = run_validation_pipeline(session_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")

    elapsed_ms = int((time.time() - start) * 1000)

    return ValidationResponse(
        session_id=session_id,
        is_valid=result.is_valid,
        checks_passed=result.checks_passed,
        checks_failed=result.checks_failed,
        checks_warned=result.checks_warned,
        checks_skipped=result.checks_skipped,
        checks=[
            ValidationCheckResponse(
                check_name=c.check_name,
                check_category=c.check_category,
                status=c.status,
                expected_value=c.expected_value,
                actual_value=c.actual_value,
                message=c.message,
            )
            for c in result.checks
        ],
        processing_time_ms=elapsed_ms,
    )


@router.get("/{session_id}", response_model=ValidationResponse)
def get_validation(
    session_id: str,
    db: Client = Depends(get_db),
) -> ValidationResponse:
    """Retrieve existing validation results for a session."""
    validation = repo.get_validation_by_session(db, session_id)
    if not validation:
        raise HTTPException(status_code=404, detail="No validation results found for this session")

    checks = repo.get_validation_checks(db, validation["id"])

    return ValidationResponse(
        session_id=session_id,
        is_valid=validation["is_valid"],
        checks_passed=validation["checks_passed"],
        checks_failed=validation["checks_failed"],
        checks_warned=validation["checks_warned"],
        checks_skipped=0,  # Not stored in DB summary; count from checks
        checks=[
            ValidationCheckResponse(
                check_name=c["check_name"],
                check_category=c["check_category"],
                status=c["status"],
                expected_value=c.get("expected_value"),
                actual_value=c.get("actual_value"),
                message=c.get("message", ""),
            )
            for c in checks
        ],
    )
