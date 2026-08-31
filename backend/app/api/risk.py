import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_db
from app.database import repositories as repo
from app.services.risk_scoring import assess_session_risk

router = APIRouter(prefix="/risk", tags=["risk"])
logger = logging.getLogger(__name__)

@router.post("/assess/{session_id}")
def assess_risk_endpoint(
    session_id: UUID,
    db: Client = Depends(get_db)
):
    """
    Manually assess risk for a given session.
    """
    session_id_str = str(session_id)
    if not repo.get_screening_session(db, session_id_str):
        raise HTTPException(
            status_code=404,
            detail={
                "code": "screening_not_found",
                "message": "The screening session does not exist.",
            },
        )

    # Risk assessment is the final stage and can be safely retried. Return a
    # previously persisted result instead of attempting a duplicate insert.
    existing_assessment = repo.get_risk_assessment_by_session(db, session_id_str)
    if existing_assessment:
        return {
            "assessment": existing_assessment,
            "factors": repo.get_risk_factors(db, existing_assessment["id"]),
        }

    try:
        return assess_session_risk(session_id_str, db)
    except Exception:
        logger.exception("Error assessing risk for session %s", session_id)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "risk_assessment_failed",
                "message": "Risk assessment could not be completed.",
            },
        )
