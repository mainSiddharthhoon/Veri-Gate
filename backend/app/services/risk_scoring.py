import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from uuid import UUID

from supabase import Client
from app.database.repositories import (
    create_risk_assessment,
    create_risk_factors
)

@dataclass
class RiskConfig:
    # Validation Factors
    mrz_mismatch_weight: float = 50.0
    expired_document_weight: float = 40.0
    reference_mismatch_weight: float = 50.0
    missing_field_weight: float = 20.0
    reference_not_found_weight: float = 15.0
    format_warning_weight: float = 10.0
    
    # Tampering Factors
    tampering_multiplier: float = 60.0
    
    # Face Verification Factors
    face_mismatch_weight: float = 60.0
    face_error_weight: float = 25.0
    
    # Thresholds
    level_threshold_low: float = 20.0
    level_threshold_medium: float = 50.0
    level_threshold_high: float = 79.0

# Default global instance
CONFIG = RiskConfig()


def _query_data(response: Any) -> Any:
    """Return Supabase query data when a query did not yield a response."""
    return getattr(response, "data", None) if response is not None else None

@dataclass
class RiskFactor:
    factor_source: str
    factor_name: str
    weight: float
    score_contribution: float
    severity: str
    message: str

    def to_db_dict(self, risk_assessment_id: str) -> dict:
        return {
            "risk_assessment_id": risk_assessment_id,
            "factor_source": self.factor_source,
            "factor_name": self.factor_name,
            "weight": float(self.weight),
            "score_contribution": float(self.score_contribution),
            "severity": self.severity,
            "message": self.message,
        }

def determine_level_and_decision(total_score: float, config: RiskConfig) -> tuple[str, str]:
    if total_score <= config.level_threshold_low:
        return "low", "approve"
    elif total_score <= config.level_threshold_medium:
        return "medium", "review"
    elif total_score <= config.level_threshold_high:
        return "high", "review"
    else:
        return "critical", "reject"

def assess_session_risk(session_id: str, db: Client, config: RiskConfig = CONFIG) -> dict:
    """
    Calculate the risk score based on Validation, Tampering, and Face Verification results.
    """
    # 1. Fetch data for this session
    # Validation
    val_res = db.table("validation_results").select("id").eq("session_id", session_id).maybe_single().execute()
    validation_checks = []
    validation_data = _query_data(val_res)
    if validation_data:
        v_id = validation_data["id"]
        v_checks = db.table("validation_checks").select("*").eq("validation_result_id", v_id).execute()
        validation_checks = _query_data(v_checks) or []

    # Tampering
    tamp_res = db.table("tampering_analyses").select("*").eq("session_id", session_id).maybe_single().execute()
    tampering_data = _query_data(tamp_res)

    # Face Verification
    face_res = db.table("face_verifications").select("*").eq("session_id", session_id).maybe_single().execute()
    face_data = _query_data(face_res)

    factors: List[RiskFactor] = []
    total_score = 0.0

    # 2. Analyze Validation Checks
    for check in validation_checks:
        status = check["status"]
        if status == "passed" or status == "skipped":
            continue
            
        # Persisted validation records use ``check_category``; retain the
        # legacy key as a fallback for older callers and tests.
        category = check.get("check_category", check.get("category", ""))
        check_name = check["check_name"]
        msg = check.get("message", f"Check {check_name} failed.")
        
        if check_name == "reference_lookup":
            weight = config.reference_not_found_weight
            factors.append(RiskFactor("database_check", check_name, weight, weight, "medium", msg))
            total_score += weight
        elif category == "database":
            weight = config.reference_mismatch_weight
            factors.append(RiskFactor("database_check", check_name, weight, weight, "critical", msg))
            total_score += weight
        elif category == "mrz":
            weight = config.mrz_mismatch_weight
            factors.append(RiskFactor("validation", check_name, weight, weight, "critical", msg))
            total_score += weight
        elif check_name == "expiry_not_past":
            weight = config.expired_document_weight
            factors.append(RiskFactor("validation", check_name, weight, weight, "high", msg))
            total_score += weight
        elif check_name.startswith("required_"):
            weight = config.missing_field_weight
            factors.append(RiskFactor("validation", check_name, weight, weight, "medium", msg))
            total_score += weight
        elif status == "warning":
            weight = config.format_warning_weight
            factors.append(RiskFactor("validation", check_name, weight, weight, "low", msg))
            total_score += weight
        else:
            weight = config.missing_field_weight  # Default fallback for failed validation
            factors.append(RiskFactor("validation", check_name, weight, weight, "medium", msg))
            total_score += weight

    # 3. Analyze Tampering
    if tampering_data:
        tamper_score_raw = tampering_data.get("tamper_score", 0.0)
        if tamper_score_raw > 0:
            contribution = tamper_score_raw * config.tampering_multiplier
            # Determine severity based on contribution
            sev = "info"
            if contribution >= 50: sev = "critical"
            elif contribution >= 30: sev = "high"
            elif contribution >= 15: sev = "medium"
            elif contribution > 0: sev = "low"
            
            factors.append(RiskFactor(
                factor_source="tampering",
                factor_name="image_tampering",
                weight=config.tampering_multiplier,
                score_contribution=contribution,
                severity=sev,
                message=f"Tampering analysis yielded a score of {tamper_score_raw:.2f}"
            ))
            total_score += contribution

    # 4. Analyze Face Verification
    if face_data:
        error_msg = face_data.get("error_message")
        is_match = face_data.get("is_match", False)
        
        if error_msg:
            weight = config.face_error_weight
            factors.append(RiskFactor(
                factor_source="face_verification",
                factor_name="face_detection_error",
                weight=weight,
                score_contribution=weight,
                severity="medium",
                message=f"Face verification could not complete: {error_msg}"
            ))
            total_score += weight
        elif not is_match:
            weight = config.face_mismatch_weight
            factors.append(RiskFactor(
                factor_source="face_verification",
                factor_name="face_mismatch",
                weight=weight,
                score_contribution=weight,
                severity="critical",
                message="The presented face does not match the document photo."
            ))
            total_score += weight

    # 5. Compile Result
    # Capping at 100
    final_score = min(total_score, 100.0)
    risk_level, decision = determine_level_and_decision(final_score, config)
    
    # Auto-override: If there's any critical factor, force at least 'review' (or 'reject')
    has_critical = any(f.severity == "critical" for f in factors)
    if has_critical and decision == "approve":
        decision = "review"
        if risk_level == "low":
            risk_level = "medium"
            
    # Auto-override 2: Face mismatch is an absolute Reject in this simplified system
    if any(f.factor_name == "face_mismatch" for f in factors):
        decision = "reject"
        risk_level = "critical"

    summary_parts = []
    if final_score == 0:
        summary_parts.append("Clean document. All checks passed.")
    else:
        summary_parts.append(f"Identified {len(factors)} risk factor(s).")
        
    summary = " ".join(summary_parts)

    assessment_record = {
        "session_id": session_id,
        "risk_score": float(final_score),
        "risk_level": risk_level,
        "decision": decision,
        "summary": summary,
        "scoring_config": asdict(config)
    }

    # Persist to Supabase
    db_assessment = create_risk_assessment(db, assessment_record)
    
    db_factors = []
    if factors:
        factor_records = [f.to_db_dict(db_assessment["id"]) for f in factors]
        db_factors = create_risk_factors(db, factor_records)

    return {
        "assessment": db_assessment,
        "factors": db_factors
    }
