"""
VeriGate Backend — Screening Service

Orchestrates the screening workflow. Currently a stub that creates sessions
and retrieves results. The actual AI/CV processing modules will be added
in future phases.
"""

from __future__ import annotations

from supabase import Client

from app.database import repositories as repo


def create_session(db: Client, data: dict) -> dict:
    """Create a new screening session.

    In the future, this will also kick off the async processing pipeline.
    For now, it just inserts the session record.
    """
    return repo.create_screening_session(db, data)


def get_session_detail(db: Client, session_id: str) -> dict | None:
    """Fetch a screening session with all its analysis results.

    Returns the session plus any associated documents, validation,
    tampering, face verification, and risk assessment data.
    """
    session = repo.get_screening_session(db, session_id)
    if not session:
        return None

    result = {**session}

    # Attach document fields
    result["document"] = repo.get_document_by_session(db, session_id)

    # Attach validation with individual checks
    validation = repo.get_validation_by_session(db, session_id)
    if validation:
        checks = repo.get_validation_checks(db, validation["id"])
        validation["checks"] = checks
    result["validation"] = validation

    # Attach tampering with individual signals
    tampering = repo.get_tampering_by_session(db, session_id)
    if tampering:
        signals = repo.get_tampering_signals(db, tampering["id"])
        tampering["signals"] = signals
    result["tampering"] = tampering

    # Attach face verification
    result["face_verification"] = repo.get_face_verification_by_session(db, session_id)

    # Attach risk assessment with factors
    risk = repo.get_risk_assessment_by_session(db, session_id)
    if risk:
        factors = repo.get_risk_factors(db, risk["id"])
        risk["factors"] = factors
    result["risk_assessment"] = risk

    return result


def list_sessions(
    db: Client,
    *,
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
) -> list[dict]:
    """List screening sessions with optional filtering."""
    return repo.list_screening_sessions(db, limit=limit, offset=offset, status=status)
