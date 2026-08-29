"""
VeriGate Backend — Tampering Pipeline Orchestrator

Runs the tampering core logic, saves visual evidence, and persists
signals and analysis summaries to Supabase.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from supabase import Client

from app.database import repositories as repo
from app.services.tampering_core import analyze_document_tampering, TamperingResult

logger = logging.getLogger(__name__)

# Temporary local storage for evidence images until Supabase Storage is set up
EVIDENCE_DIR = Path("backend/evidence")


def run_tampering_pipeline(
    session_id: str,
    image_bytes: bytes,
    db: Client,
) -> TamperingResult:
    """Run the tampering detection pipeline on a document image.

    Args:
        session_id: The screening session ID.
        image_bytes: The raw image bytes.
        db: Supabase client.

    Returns:
        TamperingResult containing the score and signals.
    """
    pipeline_start = time.time()
    
    # Run pure core logic
    try:
        result = analyze_document_tampering(image_bytes)
    except Exception as e:
        logger.error("Tampering analysis failed for session %s: %s", session_id, e)
        raise

    result.processing_time_ms = int((time.time() - pipeline_start) * 1000)
    
    # Save evidence image locally
    evidence_path = None
    if result.ela_heatmap:
        try:
            # We are running from the `backend` directory, but creating the 
            # absolute path defensively. We'll use a relative path just in case.
            # (Note: In production this would upload to Supabase Storage)
            os.makedirs("evidence", exist_ok=True)
            filename = f"{session_id}_ela_heatmap.jpg"
            filepath = Path("evidence") / filename
            filepath.write_bytes(result.ela_heatmap)
            evidence_path = f"evidence/{filename}"
            logger.info("Saved tampering evidence image to %s", evidence_path)
        except Exception as e:
            logger.error("Failed to save evidence image: %s", e)

    # Persist to Supabase
    _persist_results(db, session_id, result, evidence_path)
    
    return result


def _persist_results(
    db: Client,
    session_id: str,
    result: TamperingResult,
    evidence_path: str | None,
) -> None:
    """Save tampering analysis and signals to Supabase."""
    
    analysis_id = None
    try:
        analysis_data = {
            "session_id": session_id,
            "tamper_score": result.tamper_score,
            "is_suspicious": result.is_suspicious,
            "analysis_metadata": {
                "methods": ["exif_software", "ela_global", "ela_face_region"],
                "version": "1.0",
            },
            "processing_time_ms": result.processing_time_ms,
        }
        saved = repo.create_tampering_analysis(db, analysis_data)
        analysis_id = saved["id"]
        logger.info(
            "Saved tampering analysis for session %s: score=%.2f, suspicious=%s", 
            session_id, result.tamper_score, result.is_suspicious
        )
    except Exception as e:
        logger.error("Failed to save tampering analysis: %s", e)
        return  # Can't insert signals without parent row

    # Insert individual signals
    for signal in result.signals:
        try:
            # Only the primary ELA photo_region or noise_analysis gets the heatmap link
            # For simplicity, we attach it to all ELA signals.
            sig_evidence = evidence_path if "ela" in signal.signal_name else None
            repo.create_tampering_signal(db, signal.to_db_dict(analysis_id, sig_evidence))
        except Exception as e:
            logger.error("Failed to save tampering signal '%s': %s", signal.signal_name, e)

    # Audit log
    try:
        repo.create_audit_entry(db, {
            "session_id": session_id,
            "event_type": "tampering_analysis_completed",
            "event_data": {
                "tamper_score": result.tamper_score,
                "is_suspicious": result.is_suspicious,
                "processing_time_ms": result.processing_time_ms,
            },
        })
    except Exception as e:
        logger.error("Failed to create tampering audit entry: %s", e)
