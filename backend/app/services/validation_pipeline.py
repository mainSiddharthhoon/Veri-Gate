"""
VeriGate Backend — Validation Pipeline Orchestrator

Orchestrates the validation workflow:
  1. Fetch document record
  2. Look up reference document
  3. Run validation checks
  4. Persist results to Supabase
  5. Create audit log entry
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from supabase import Client

from app.database import repositories as repo
from app.services.validation import validate_document, ValidationResult

logger = logging.getLogger(__name__)


def run_validation_pipeline(
    session_id: str,
    db: Client,
) -> ValidationResult:
    """Run the full validation pipeline for a screening session.

    Requires that OCR and document extraction have already completed
    for the given session (i.e., a `documents` row must exist).

    Args:
        session_id: The screening session ID to validate.
        db: Supabase client.

    Returns:
        ValidationResult with all checks and aggregate counts.

    Raises:
        ValueError: If no document record exists for the session.
    """
    pipeline_start = time.time()

    # --- Step 1: Fetch the extracted document ---
    document = repo.get_document_by_session(db, session_id)
    if not document:
        raise ValueError(f"No document record found for session {session_id}")

    # --- Step 2: Look up reference document ---
    reference = None
    doc_type = document.get("document_type", "passport")
    doc_number = document.get("document_number")
    issuing_country = document.get("issuing_country")

    if doc_number:
        try:
            reference = repo.find_reference_document(
                db,
                document_type=doc_type,
                document_number=doc_number,
                issuing_country=issuing_country,
            )
            if reference:
                logger.info(
                    "Reference document found for %s %s: status=%s",
                    doc_type, doc_number, reference.get("status"),
                )
            else:
                logger.info(
                    "No reference document found for %s %s",
                    doc_type, doc_number,
                )
        except Exception as e:
            logger.warning("Reference lookup failed: %s", e)

    # --- Step 3: Run validation ---
    mrz_parsed = document.get("mrz_parsed")
    result = validate_document(
        document=document,
        mrz_parsed=mrz_parsed,
        reference=reference,
    )

    processing_time_ms = int((time.time() - pipeline_start) * 1000)

    # --- Step 4: Persist results ---
    _persist_results(db, session_id, result, processing_time_ms)

    return result


def _persist_results(
    db: Client,
    session_id: str,
    result: ValidationResult,
    processing_time_ms: int,
) -> None:
    """Save validation results to Supabase."""

    # Insert validation_results summary row
    validation_result_id = None
    try:
        summary_data = {
            "session_id": session_id,
            "is_valid": result.is_valid,
            "checks_passed": result.checks_passed,
            "checks_failed": result.checks_failed,
            "checks_warned": result.checks_warned,
        }
        saved = repo.create_validation_result(db, summary_data)
        validation_result_id = saved["id"]
        logger.info("Saved validation result for session %s: is_valid=%s", session_id, result.is_valid)
    except Exception as e:
        logger.error("Failed to save validation result: %s", e)
        return  # Can't insert checks without the parent row

    # Insert individual validation_checks rows
    for check in result.checks:
        try:
            repo.create_validation_check(db, check.to_db_dict(validation_result_id))
        except Exception as e:
            logger.error("Failed to save validation check '%s': %s", check.check_name, e)

    # Audit log
    try:
        repo.create_audit_entry(db, {
            "session_id": session_id,
            "event_type": "validation_completed",
            "event_data": {
                "is_valid": result.is_valid,
                "checks_passed": result.checks_passed,
                "checks_failed": result.checks_failed,
                "checks_warned": result.checks_warned,
                "checks_skipped": result.checks_skipped,
                "processing_time_ms": processing_time_ms,
            },
        })
    except Exception as e:
        logger.error("Failed to create validation audit entry: %s", e)
