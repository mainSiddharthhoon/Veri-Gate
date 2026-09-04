"""
VeriGate Backend — OCR Pipeline Orchestrator

Runs the complete OCR pipeline for a document image:
preprocess → OCR → MRZ detection → MRZ parsing → field extraction → persist.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field as dc_field
from typing import Any, Optional

from supabase import Client

from app.database import repositories as repo
from app.services.preprocessing import (
    preprocess_for_ocr,
    decode_image,
    encode_image_to_bytes,
)
from app.services.ocr import run_ocr, OcrRawResult, OcrBlock
from app.services.mrz import detect_mrz_lines, parse_td3_mrz, MrzResult, MrzCheckResult
from app.services.field_extraction import (
    extract_passport_fields,
    extract_fields_from_raw_text,
    DocumentData,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result data class
# ---------------------------------------------------------------------------

@dataclass
class PipelineResult:
    """Complete result from the OCR pipeline."""
    session_id: Optional[str] = None

    # OCR
    raw_text: str = ""
    ocr_blocks: list[dict] = dc_field(default_factory=list)
    ocr_confidence: float = 0.0
    ocr_processing_time_ms: int = 0

    # MRZ
    mrz_detected: bool = False
    mrz_line_1: Optional[str] = None
    mrz_line_2: Optional[str] = None
    mrz_parsed: Optional[dict] = None
    mrz_check_results: list[dict] = dc_field(default_factory=list)
    mrz_all_valid: bool = False

    # Extracted fields
    document_fields: Optional[dict] = None

    # Processing
    total_processing_time_ms: int = 0
    errors: list[str] = dc_field(default_factory=list)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_ocr_pipeline(
    image_bytes: bytes,
    db: Client,
    document_type: str = "passport",
    *,
    session_id: Optional[str] = None,
) -> PipelineResult:
    """Run the full OCR pipeline on a document image.

    Steps:
        1. Create or reuse screening session
        2. Preprocess image for OCR
        3. Run PaddleOCR
        4. Detect MRZ lines
        5. Parse MRZ (TD3 for passports)
        6. Extract structured passport fields
        7. Persist OCR result and document to Supabase
        8. Return structured result

    Args:
        image_bytes: Raw uploaded image bytes.
        db: Supabase client.
        document_type: Type of document (default: 'passport').
        session_id: Existing session ID to use, or None to create new.

    Returns:
        PipelineResult with all extracted data and processing info.
    """
    pipeline_start = time.time()
    result = PipelineResult()

    # --- Step 1: Create screening session if needed ---
    if session_id is None:
        try:
            session = repo.create_screening_session(db, {
                "status": "processing",
                "document_type": document_type,
                "document_image_path": "pending",  # Updated after storage upload
                "person_image_path": "pending",     # Not provided in OCR-only flow
            })
            session_id = session["id"]
            logger.info("Created screening session: %s", session_id)
        except Exception as e:
            result.errors.append(f"Failed to create session: {e}")
            logger.error("Session creation failed: %s", e)
            return result
    else:
        # Update existing session status
        try:
            repo.update_screening_session(db, session_id, {"status": "processing"})
        except Exception as e:
            logger.warning("Could not update session status: %s", e)

    result.session_id = session_id

    # --- Step 2: Preprocess image ---
    try:
        original_image = decode_image(image_bytes)
        preprocessed_image = preprocess_for_ocr(image_bytes)
    except ValueError as e:
        result.errors.append(f"Image preprocessing failed: {e}")
        _update_session_failed(db, session_id)
        return result

    # --- Step 3: Run PaddleOCR ---
    # Run on original image (PaddleOCR has its own preprocessing)
    try:
        ocr_result = run_ocr(original_image)
    except Exception as e:
        result.errors.append(f"OCR failed: {e}")
        logger.error("OCR failed: %s", e)
        _update_session_failed(db, session_id)
        return result

    result.raw_text = ocr_result.raw_text
    result.ocr_blocks = [
        {
            "text": b.text,
            "confidence": b.confidence,
            "bounding_box": b.bounding_box,
        }
        for b in ocr_result.blocks
    ]
    result.ocr_confidence = ocr_result.average_confidence
    result.ocr_processing_time_ms = ocr_result.processing_time_ms

    # --- Step 4: Detect MRZ lines ---
    mrz_lines = detect_mrz_lines(ocr_result.raw_text)

    if mrz_lines is None:
        result.mrz_detected = False
        logger.warning("MRZ not detected for session %s, attempting fallback visual field extraction", session_id)
        doc_data = extract_fields_from_raw_text(ocr_result.raw_text)
        if doc_data:
            result.document_fields = doc_data.to_db_dict(session_id)
            logger.info("Successfully extracted visual/synthetic document fields for session %s: %s", session_id, result.document_fields)
        else:
            result.errors.append("MRZ lines and visual document fields not detected in OCR output")
    else:
        result.mrz_detected = True
        result.mrz_line_1 = mrz_lines[0]
        result.mrz_line_2 = mrz_lines[1]

        # --- Step 5: Parse MRZ ---
        mrz_result = parse_td3_mrz(mrz_lines[0], mrz_lines[1])

        result.mrz_parsed = {
            "document_code": mrz_result.document_code,
            "issuing_country": mrz_result.issuing_country,
            "surname": mrz_result.surname,
            "given_names": mrz_result.given_names,
            "document_number": mrz_result.document_number,
            "nationality": mrz_result.nationality,
            "date_of_birth": mrz_result.date_of_birth,
            "sex": mrz_result.sex,
            "date_of_expiry": mrz_result.date_of_expiry,
            "personal_number": mrz_result.personal_number,
            "all_checks_valid": mrz_result.all_checks_valid,
        }

        result.mrz_check_results = [
            {
                "field_name": c.field_name,
                "expected": c.expected,
                "computed": c.computed,
                "is_valid": c.is_valid,
            }
            for c in mrz_result.check_results
        ]
        result.mrz_all_valid = mrz_result.all_checks_valid

        # --- Step 6: Extract passport fields ---
        doc_data = extract_passport_fields(mrz_result, ocr_result.raw_text)
        result.document_fields = doc_data.to_db_dict(session_id)

    # --- Step 7: Persist to Supabase ---
    _persist_results(db, session_id, result, ocr_result)

    # --- Step 8: Auto-trigger validation ---
    if result.document_fields:
        try:
            from app.services.validation_pipeline import run_validation_pipeline
            validation_result = run_validation_pipeline(session_id, db)
            logger.info(
                "Validation completed for session %s: is_valid=%s (passed=%d, failed=%d, warned=%d)",
                session_id,
                validation_result.is_valid,
                validation_result.checks_passed,
                validation_result.checks_failed,
                validation_result.checks_warned,
            )
        except Exception as e:
            result.errors.append(f"Validation failed: {e}")
            logger.error("Validation failed for session %s: %s", session_id, e)

    # --- Step 9: Auto-trigger tampering analysis ---
    try:
        from app.services.tampering_pipeline import run_tampering_pipeline
        tampering_result = run_tampering_pipeline(session_id, image_bytes, db)
        logger.info(
            "Tampering analysis completed for session %s: suspicious=%s (score=%.2f)",
            session_id,
            tampering_result.is_suspicious,
            tampering_result.tamper_score,
        )
    except Exception as e:
        result.errors.append(f"Tampering analysis failed: {e}")
        logger.error("Tampering analysis failed for session %s: %s", session_id, e)

    # --- Finalize ---
    result.total_processing_time_ms = int((time.time() - pipeline_start) * 1000)

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _persist_results(
    db: Client,
    session_id: str,
    result: PipelineResult,
    ocr_result: OcrRawResult,
) -> None:
    """Save OCR and document results to Supabase."""

    # Save OCR result
    try:
        ocr_data = {
            "session_id": session_id,
            "engine": "paddleocr",
            "raw_text": result.raw_text,
            "raw_blocks": result.ocr_blocks,
            "confidence_score": min(result.ocr_confidence, 1.0),  # Clamp to [0,1]
            "processing_time_ms": result.ocr_processing_time_ms,
        }
        repo.create_ocr_result(db, ocr_data)
        logger.info("Saved OCR result for session %s", session_id)
    except Exception as e:
        result.errors.append(f"Failed to save OCR result: {e}")
        logger.error("Failed to save OCR result: %s", e)

    # Save extracted document if MRZ was detected
    if result.document_fields:
        try:
            repo.create_document(db, result.document_fields)
            logger.info("Saved document for session %s", session_id)
        except Exception as e:
            result.errors.append(f"Failed to save document: {e}")
            logger.error("Failed to save document: %s", e)

    # Update session status
    new_status = "completed" if not result.errors else "failed"
    try:
        repo.update_screening_session(db, session_id, {"status": new_status})
    except Exception as e:
        logger.error("Failed to update session status: %s", e)

    # Audit log
    try:
        repo.create_audit_entry(db, {
            "session_id": session_id,
            "event_type": "ocr_completed" if not result.errors else "ocr_failed",
            "event_data": {
                "mrz_detected": result.mrz_detected,
                "ocr_confidence": result.ocr_confidence,
                "processing_time_ms": result.total_processing_time_ms,
                "error_count": len(result.errors),
            },
        })
    except Exception as e:
        logger.error("Failed to create audit entry: %s", e)


def _update_session_failed(db: Client, session_id: str) -> None:
    """Mark a session as failed."""
    try:
        repo.update_screening_session(db, session_id, {"status": "failed"})
    except Exception:
        pass
