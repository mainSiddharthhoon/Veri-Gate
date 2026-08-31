"""
VeriGate Backend — Database Repositories

Thin data-access layer around the Supabase client.
Each public function maps to a specific database operation.
"""

from __future__ import annotations

from typing import Any

from supabase import Client


# ---------------------------------------------------------------------------
# Screening Sessions
# ---------------------------------------------------------------------------

def create_screening_session(db: Client, data: dict[str, Any]) -> dict:
    """Insert a new screening session and return the created row."""
    result = db.table("screening_sessions").insert(data).execute()
    return result.data[0]


def get_screening_session(db: Client, session_id: str) -> dict | None:
    """Fetch a single screening session by ID."""
    result = (
        db.table("screening_sessions")
        .select("*")
        .eq("id", session_id)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


def list_screening_sessions(
    db: Client,
    *,
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
) -> list[dict]:
    """List screening sessions with optional status filter."""
    query = (
        db.table("screening_sessions")
        .select("*")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return result.data


def update_screening_session(db: Client, session_id: str, data: dict[str, Any]) -> dict:
    """Update a screening session."""
    result = (
        db.table("screening_sessions")
        .update(data)
        .eq("id", session_id)
        .execute()
    )
    return result.data[0] if result.data else {}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def get_document_by_session(db: Client, session_id: str) -> dict | None:
    """Fetch the extracted document for a session."""
    result = (
        db.table("documents")
        .select("*")
        .eq("session_id", session_id)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def get_validation_by_session(db: Client, session_id: str) -> dict | None:
    """Fetch validation result for a session."""
    result = (
        db.table("validation_results")
        .select("*")
        .eq("session_id", session_id)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


def get_validation_checks(db: Client, validation_result_id: str) -> list[dict]:
    """Fetch all validation checks for a validation result."""
    result = (
        db.table("validation_checks")
        .select("*")
        .eq("validation_result_id", validation_result_id)
        .execute()
    )
    return result.data if result else []


def create_validation_result(db: Client, data: dict[str, Any]) -> dict:
    """Insert a new validation result and return the created row."""
    result = db.table("validation_results").insert(data).execute()
    return result.data[0]


def create_validation_check(db: Client, data: dict[str, Any]) -> dict:
    """Insert a new validation check and return the created row."""
    result = db.table("validation_checks").insert(data).execute()
    return result.data[0]


# ---------------------------------------------------------------------------
# Tampering
# ---------------------------------------------------------------------------

def get_tampering_by_session(db: Client, session_id: str) -> dict | None:
    """Fetch tampering analysis for a session."""
    result = (
        db.table("tampering_analyses")
        .select("*")
        .eq("session_id", session_id)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


def get_tampering_signals(db: Client, tampering_analysis_id: str) -> list[dict]:
    """Fetch all tampering signals for an analysis."""
    result = (
        db.table("tampering_signals")
        .select("*")
        .eq("tampering_analysis_id", tampering_analysis_id)
        .execute()
    )
    return result.data if result else None


def create_tampering_analysis(db: Client, data: dict[str, Any]) -> dict:
    """Insert a new tampering analysis and return the created row."""
    result = db.table("tampering_analyses").insert(data).execute()
    return result.data[0]


def create_tampering_signal(db: Client, data: dict[str, Any]) -> dict:
    """Insert a new tampering signal and return the created row."""
    result = db.table("tampering_signals").insert(data).execute()
    return result.data[0]


# ---------------------------------------------------------------------------
# Face Verification
# ---------------------------------------------------------------------------

def create_face_verification(db: Client, data: dict[str, Any]) -> dict:
    """Insert a new face verification result and return the created row."""
    result = db.table("face_verifications").insert(data).execute()
    return result.data[0]


def get_face_verification_by_session(db: Client, session_id: str) -> dict | None:
    """Fetch face verification result for a session."""
    result = (
        db.table("face_verifications")
        .select("*")
        .eq("session_id", session_id)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


# ---------------------------------------------------------------------------
# Risk Assessment
# ---------------------------------------------------------------------------

def get_risk_assessment_by_session(db: Client, session_id: str) -> dict | None:
    """Fetch risk assessment for a session."""
    result = (
        db.table("risk_assessments")
        .select("*")
        .eq("session_id", session_id)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


def get_risk_factors(db: Client, risk_assessment_id: str) -> list[dict]:
    """Fetch all risk factors for an assessment."""
    result = (
        db.table("risk_factors")
        .select("*")
        .eq("risk_assessment_id", risk_assessment_id)
        .execute()
    )
    return result.data if result else []

def create_risk_assessment(db: Client, data: dict[str, Any]) -> dict:
    """Insert a new risk assessment and return the created row."""
    result = db.table("risk_assessments").insert(data).execute()
    return result.data[0]

def create_risk_factors(db: Client, factors: list[dict[str, Any]]) -> list[dict]:
    """Insert multiple risk factors and return the created rows."""
    if not factors:
        return []
    result = db.table("risk_factors").insert(factors).execute()
    return result.data


# ---------------------------------------------------------------------------
# Reference Documents
# ---------------------------------------------------------------------------

def list_reference_documents(db: Client, *, limit: int = 50) -> list[dict]:
    """List reference documents."""
    result = (
        db.table("reference_documents")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data if result else []


def find_reference_document(
    db: Client,
    document_type: str,
    document_number: str,
    issuing_country: str | None = None,
) -> dict | None:
    """Look up a reference document by type, number, and optionally country."""
    query = (
        db.table("reference_documents")
        .select("*")
        .eq("document_type", document_type)
        .eq("document_number", document_number)
    )
    if issuing_country:
        query = query.eq("issuing_country", issuing_country)
    result = query.maybe_single().execute()
    return result.data if result else None


# ---------------------------------------------------------------------------
# OCR Results
# ---------------------------------------------------------------------------

def create_ocr_result(db: Client, data: dict[str, Any]) -> dict:
    """Insert a new OCR result and return the created row."""
    result = db.table("ocr_results").insert(data).execute()
    return result.data[0]


def get_ocr_result_by_session(db: Client, session_id: str) -> dict | None:
    """Fetch OCR result for a session."""
    result = (
        db.table("ocr_results")
        .select("*")
        .eq("session_id", session_id)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


# ---------------------------------------------------------------------------
# Documents (create)
# ---------------------------------------------------------------------------

def create_document(db: Client, data: dict[str, Any]) -> dict:
    """Insert a new document record and return the created row."""
    result = db.table("documents").insert(data).execute()
    return result.data[0]


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

def create_audit_entry(db: Client, data: dict[str, Any]) -> dict:
    """Insert a new audit log entry and return the created row."""
    result = db.table("audit_log").insert(data).execute()
    return result.data[0]
