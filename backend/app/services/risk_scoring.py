import logging
from typing import Dict, Any

from supabase import Client
from app.database.repositories import (
    create_risk_assessment,
    create_risk_factors
)
from app.services.ai_reasoning import assess_evidence

logger = logging.getLogger(__name__)

def _query_data(response: Any) -> Any:
    return getattr(response, "data", None) if response is not None else None

def _safe_read(path: str) -> bytes | None:
    if not path:
        return None
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read image at {path}: {e}")
        return None

def _calculate_temporal_evidence(doc_data: dict) -> dict:
    from datetime import datetime
    today = datetime.now().date()
    
    temporal = {
        "current_date": today.isoformat(),
        "date_of_birth": doc_data.get("date_of_birth"),
        "calculated_age": None,
        "dob_in_future": None,
        "date_of_issue": doc_data.get("date_of_issue"),
        "date_of_expiry": doc_data.get("date_of_expiry"),
        "issue_date_status": "present" if doc_data.get("date_of_issue") else "not_present",
        "expiry_date_status": "present" if doc_data.get("date_of_expiry") else "not_present",
        "document_expired": None,
        "days_until_expiry": None,
        "issue_before_expiry": None,
        "issue_in_future": None,
    }
    
    dob_str = temporal["date_of_birth"]
    if dob_str:
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            temporal["dob_in_future"] = dob > today
            if not temporal["dob_in_future"]:
                temporal["calculated_age"] = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        except ValueError:
            pass

    exp_str = temporal["date_of_expiry"]
    exp_date = None
    if exp_str:
        try:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            temporal["days_until_expiry"] = (exp_date - today).days
            temporal["document_expired"] = temporal["days_until_expiry"] < 0
        except ValueError:
            pass

    iss_str = temporal["date_of_issue"]
    if iss_str:
        try:
            iss_date = datetime.strptime(iss_str, "%Y-%m-%d").date()
            temporal["issue_in_future"] = iss_date > today
            if exp_date:
                temporal["issue_before_expiry"] = iss_date < exp_date
        except ValueError:
            pass
            
    return temporal

def assess_session_risk(session_id: str, db: Client) -> dict:
    """
    Main reasoning layer orchestration. 
    Gathers evidence from Supabase and delegates to AI Reasoning.
    """
    # 1. Fetch data for this session
    session_res = db.table("screening_sessions").select("*").eq("id", session_id).maybe_single().execute()
    session_data = _query_data(session_res)
    if not session_data:
        raise ValueError("Session not found")
        
    doc_path = session_data.get("document_image_path")
    face_path = session_data.get("person_image_path")
    
    ocr_res = db.table("ocr_results").select("*").eq("session_id", session_id).maybe_single().execute()
    ocr_data = _query_data(ocr_res) or {}
    
    mrz_data = {}
    if ocr_data and ocr_data.get("mrz_data"):
        mrz_data = ocr_data["mrz_data"]

    doc_res = db.table("documents").select("*").eq("session_id", session_id).maybe_single().execute()
    document_data = _query_data(doc_res) or {}
    temporal_data = _calculate_temporal_evidence(document_data)

    val_res = db.table("validation_results").select("id").eq("session_id", session_id).maybe_single().execute()
    validation_checks = []
    validation_data = _query_data(val_res)
    if validation_data:
        v_id = validation_data["id"]
        v_checks = db.table("validation_checks").select("*").eq("validation_result_id", v_id).execute()
        validation_checks = _query_data(v_checks) or []

    tamp_res = db.table("tampering_analyses").select("*").eq("session_id", session_id).maybe_single().execute()
    tampering_data = _query_data(tamp_res) or {}
    tamp_heatmap = tampering_data.get("heatmap_image_path")

    face_res = db.table("face_verifications").select("*").eq("session_id", session_id).maybe_single().execute()
    face_data = _query_data(face_res) or {}

    # 2. Read images
    doc_bytes = _safe_read(doc_path)
    face_bytes = _safe_read(face_path)
    tamp_bytes = _safe_read(tamp_heatmap)
    
    if not doc_bytes:
        raise ValueError("Document image is required for assessment.")

    # 3. Call AI Reasoning
    ai_assessment, run1, run2, provider = assess_evidence(
        document_image=doc_bytes,
        face_image=face_bytes,
        tampering_image=tamp_bytes,
        ocr_data=ocr_data,
        mrz_data=mrz_data,
        validation_data=validation_checks,
        tampering_data=tampering_data,
        face_data=face_data,
        temporal_data=temporal_data
    )

    # 4. Format for Database
    assessment_record = {
        "session_id": session_id,
        "risk_score": ai_assessment.risk_score,
        "risk_level": ai_assessment.risk_level,
        "decision": ai_assessment.decision,
        "summary": ai_assessment.report,
        "scoring_config": {"ai_provider": provider, "reason": ai_assessment.reason}
    }

    # Persist to Supabase
    db_assessment = create_risk_assessment(db, assessment_record)
    
    # Translate boolean flags into UI risk factors
    factors = []
    if not ai_assessment.document_valid:
        factors.append({"factor_source": "validation", "factor_name": "document_invalid", "weight": 50, "score_contribution": 50, "severity": "critical", "message": "Document is not visually plausible."})
    if not ai_assessment.identity_consistent:
        factors.append({"factor_source": "validation", "factor_name": "identity_inconsistent", "weight": 50, "score_contribution": 50, "severity": "high", "message": "Fields are internally inconsistent."})
    if ai_assessment.tampering_concern:
        factors.append({"factor_source": "tampering", "factor_name": "tampering_concern", "weight": 50, "score_contribution": 50, "severity": "high", "message": "Forensic evidence supports suspicion of tampering."})
    if ai_assessment.identity_match_status == "mismatch":
        factors.append({"factor_source": "face_verification", "factor_name": "face_mismatch", "weight": 50, "score_contribution": 50, "severity": "critical", "message": "Document face does not match presented person."})
    if ai_assessment.inconclusive:
        factors.append({"factor_source": "validation", "factor_name": "inconclusive", "weight": 50, "score_contribution": 50, "severity": "medium", "message": "AI deemed evidence inconclusive or contradictory."})
        
    for rf in ai_assessment.risk_factors:
        factors.append({"factor_source": "validation", "factor_name": "ai_risk_factor", "weight": 20, "score_contribution": 20, "severity": "medium", "message": rf})

    db_factors = []
    if factors:
        factor_records = [{**f, "risk_assessment_id": db_assessment["id"]} for f in factors]
        db_factors = create_risk_factors(db, factor_records)

    # Attach the provider back out to the top-level response so the router can return it
    db_assessment["ai_provider"] = provider

    return {
        "assessment": db_assessment,
        "factors": db_factors,
        "debug_run1": run1.model_dump() if run1 else None,
        "debug_run2": run2.model_dump() if run2 else None
    }
