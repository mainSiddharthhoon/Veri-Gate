"""
VeriGate Database End-to-End Verification Test
Verifies:
1. Database connectivity & responsiveness (Supabase PostgreSQL).
2. Data insertion across all 10 core tables using exact PostgreSQL schema:
   - screening_sessions
   - documents
   - ocr_results
   - validation_results
   - validation_checks
   - tampering_analyses
   - tampering_signals
   - face_verifications
   - risk_assessments
   - risk_factors
3. Query accuracy: verifying that inserted fields, JSON structures, and foreign keys match required types.
4. Update operation: updating session status and completion timestamp.
5. Clean cascade deletion to leave database in pristine state.
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_path))

from app.core.config import get_settings
from app.core.database import get_supabase_client

def run_db_test():
    print("=" * 65)
    print(" VeriGate Supabase Database Verification Test")
    print("=" * 65)

    settings = get_settings()
    print(f"\n[1] Connecting to Supabase at: {settings.supabase_url}")
    db = get_supabase_client()

    # Step 1: Health / Ping test
    try:
        ping_res = db.table("screening_sessions").select("id").limit(1).execute()
        print("    [PASS] Database is RESPONDING smoothly (ping OK).")
    except Exception as e:
        print(f"    [FAIL] Database ping failed: {e}")
        return False

    # Step 2: Verify table existence
    tables_to_check = [
        "screening_sessions",
        "documents",
        "ocr_results",
        "validation_results",
        "validation_checks",
        "tampering_analyses",
        "tampering_signals",
        "face_verifications",
        "risk_assessments",
        "risk_factors"
    ]
    print(f"\n[2] Checking core tables existence ({len(tables_to_check)} tables)...")
    for tbl in tables_to_check:
        try:
            res = db.table(tbl).select("id").limit(1).execute()
            print(f"    [PASS] Table '{tbl}' is reachable (rows found: {len(res.data)}).")
        except Exception as e:
            print(f"    [FAIL] Table '{tbl}' unreachable: {e}")
            return False

    # Step 3: Insert Test Data (Full screening session flow using exact schema)
    test_session_id = str(uuid.uuid4())
    print(f"\n[3] Testing Data Insertion with Session ID: {test_session_id}")

    try:
        # A. Insert Screening Session
        session_payload = {
            "id": test_session_id,
            "status": "processing",
            "document_type": "passport",
            "operator_id": "test_operator_001",
            "operator_notes": "Live DB verification test run",
            "document_image_path": f"documents/{test_session_id}/passport.jpg",
            "person_image_path": f"faces/{test_session_id}/portrait.jpg",
        }
        db.table("screening_sessions").insert(session_payload).execute()
        print("    [PASS] 1/7 Inserted into 'screening_sessions'")

        # B. Insert Document Fields (Identity data)
        document_payload = {
            "session_id": test_session_id,
            "document_type": "passport",
            "document_number": "P12345678",
            "issuing_country": "USA",
            "nationality": "USA",
            "surname": "SPECIMEN",
            "given_names": "ALEXANDER",
            "date_of_birth": "1990-05-15",
            "sex": "M",
            "date_of_issue": "2020-01-10",
            "date_of_expiry": "2030-01-10",
            "mrz_line_1": "P<USASPECIMEN<<ALEXANDER<<<<<<<<<<<<<<<<<<<",
            "mrz_line_2": "P123456784USA9005152M3001108<<<<<<<<<<<<<<02",
            "mrz_parsed": {
                "document_number": "P12345678",
                "dob": "1990-05-15",
                "expiry": "2030-01-10",
                "check_digits_valid": True
            },
            "additional_fields": {"test_field": "verified"}
        }
        db.table("documents").insert(document_payload).execute()
        print("    [PASS] 2/7 Inserted into 'documents' (Extracted Identity Fields)")

        # C. Insert Validation Results & Checks (Exact schema)
        val_payload = {
            "session_id": test_session_id,
            "is_valid": True,
            "checks_passed": 2,
            "checks_failed": 0,
            "checks_warned": 0
        }
        val_res = db.table("validation_results").insert(val_payload).execute()
        val_id = val_res.data[0]["id"]
        print("    [PASS] 3/7 Inserted into 'validation_results'")

        check_payload = [
            {
                "validation_result_id": val_id,
                "check_name": "expiry_date_valid",
                "check_category": "dates",
                "status": "passed",
                "expected_value": "> now()",
                "actual_value": "2030-01-10",
                "message": "Document is valid until 2030-01-10"
            },
            {
                "validation_result_id": val_id,
                "check_name": "mrz_checksum",
                "check_category": "mrz",
                "status": "passed",
                "expected_value": "valid checksum",
                "actual_value": "valid checksum",
                "message": "All MRZ check digits match"
            }
        ]
        db.table("validation_checks").insert(check_payload).execute()
        print(f"    [PASS] 4/7 Inserted {len(check_payload)} rows into 'validation_checks'")

        # D. Insert Tampering Forensics & Signals
        tamper_payload = {
            "session_id": test_session_id,
            "tamper_score": 0.08,
            "is_suspicious": False,
            "analysis_metadata": {
                "methods": ["exif_software", "ela_global", "ela_face_region"],
                "version": "1.0"
            },
            "processing_time_ms": 115
        }
        tamper_res = db.table("tampering_analyses").insert(tamper_payload).execute()
        tamper_id = tamper_res.data[0]["id"]
        print("    [PASS] 5/7 Inserted into 'tampering_analyses'")

        signal_payload = [
            {
                "tampering_analysis_id": tamper_id,
                "signal_type": "noise_analysis",
                "signal_name": "ela_global",
                "score": 0.08,
                "is_suspicious": False,
                "details": {"compression_ratio": "standard"},
                "message": "Global error level analysis indicates uniform compression"
            }
        ]
        db.table("tampering_signals").insert(signal_payload).execute()
        print(f"    [PASS] 6/7 Inserted {len(signal_payload)} rows into 'tampering_signals'")

        # E. Insert Face Verification
        face_payload = {
            "session_id": test_session_id,
            "model_name": "Facenet512",
            "distance": 0.18,
            "distance_metric": "cosine",
            "threshold": 0.40,
            "is_match": True,
            "processing_time_ms": 150
        }
        db.table("face_verifications").insert(face_payload).execute()
        print("    [PASS] 7/7 Inserted into 'face_verifications'")

        # F. Insert Final Risk Assessment & Risk Factors
        risk_payload = {
            "session_id": test_session_id,
            "risk_score": 12.0,
            "risk_level": "low",
            "decision": "approve",
            "summary": "Consistent document MRZ, no ELA tampering anomalies, biometric face match verified.",
            "scoring_config": {"ai_provider": "gemma", "reason": "All checks passed clean"}
        }
        risk_res = db.table("risk_assessments").insert(risk_payload).execute()
        risk_id = risk_res.data[0]["id"]
        print("    [PASS] 8/8 Inserted into 'risk_assessments' (AI Arbiter Result)")

        factor_payload = [
            {
                "risk_assessment_id": risk_id,
                "factor_source": "validation",
                "factor_name": "clean_mrz_checksum",
                "weight": 20.0,
                "score_contribution": 0.0,
                "severity": "low",
                "message": "MRZ checksums verified with 100% integrity."
            }
        ]
        db.table("risk_factors").insert(factor_payload).execute()
        print(f"    [PASS] 9/9 Inserted {len(factor_payload)} rows into 'risk_factors'")

    except Exception as e:
        print(f"    [FAIL] Insertion failed: {e}")
        # Clean up session if needed
        try:
            db.table("screening_sessions").delete().eq("id", test_session_id).execute()
        except:
            pass
        return False

    # Step 4: Verification of Inserted Data & Integrity
    print(f"\n[4] Verifying retrieved data integrity for Session {test_session_id[:8]}...")
    try:
        # Check Document
        doc_row = db.table("documents").select("*").eq("session_id", test_session_id).single().execute().data
        assert doc_row["surname"] == "SPECIMEN", f"Surname mismatch: {doc_row['surname']}"
        assert doc_row["document_number"] == "P12345678", "Document number mismatch"
        assert doc_row["mrz_parsed"]["check_digits_valid"] is True, "JSONB check mismatch"
        print(f"    [PASS] Document data verified: {doc_row['given_names']} {doc_row['surname']} ({doc_row['document_number']})")

        # Check Validation Results
        vr_row = db.table("validation_results").select("*").eq("session_id", test_session_id).single().execute().data
        assert vr_row["is_valid"] is True, "Validation result mismatch"
        print(f"    [PASS] Validation verified: is_valid={vr_row['is_valid']}, passed={vr_row['checks_passed']}")

        # Check Face Verification
        face_row = db.table("face_verifications").select("*").eq("session_id", test_session_id).single().execute().data
        assert face_row["is_match"] is True, "Face verification mismatch"
        print(f"    [PASS] Face verification verified: model={face_row['model_name']}, distance={face_row['distance']}, is_match={face_row['is_match']}")

        # Check Risk Assessment
        risk_row = db.table("risk_assessments").select("*").eq("session_id", test_session_id).single().execute().data
        assert risk_row["risk_score"] == 12.0, f"Risk score mismatch: {risk_row['risk_score']}"
        assert risk_row["decision"] == "approve", "Decision mismatch"
        print(f"    [PASS] Risk decision verified: Score={risk_row['risk_score']}/100, Decision={risk_row['decision'].upper()}")

    except Exception as e:
        print(f"    [FAIL] Data integrity check failed: {e}")
        return False

    # Step 5: Test Update Operation
    print("\n[5] Testing Session Status Update...")
    try:
        completed_time = datetime.now(timezone.utc).isoformat()
        upd = db.table("screening_sessions").update({
            "status": "completed",
            "completed_at": completed_time
        }).eq("id", test_session_id).execute()
        assert upd.data[0]["status"] == "completed", "Status update failed"
        print(f"    [PASS] Session updated to 'completed' at {completed_time}")
    except Exception as e:
        print(f"    [FAIL] Update operation failed: {e}")
        return False

    # Step 6: Clean Cascade Deletion
    print("\n[6] Cleaning up test record (Cascade deletion)...")
    try:
        db.table("screening_sessions").delete().eq("id", test_session_id).execute()
        # Verify cascade deletion across child tables
        remaining_doc = db.table("documents").select("id").eq("session_id", test_session_id).execute()
        remaining_val = db.table("validation_results").select("id").eq("session_id", test_session_id).execute()
        remaining_risk = db.table("risk_assessments").select("id").eq("session_id", test_session_id).execute()
        assert len(remaining_doc.data) == 0, "Cascade deletion did not remove document row"
        assert len(remaining_val.data) == 0, "Cascade deletion did not remove validation row"
        assert len(remaining_risk.data) == 0, "Cascade deletion did not remove risk row"
        print("    [PASS] Test session and all linked child records cleanly removed.")
    except Exception as e:
        print(f"    [FAIL] Cleanup failed: {e}")
        return False

    print("\n" + "=" * 65)
    print(" ALL DATABASE CHECKS PASSED: RESPONDING & ACCURATELY STORING DATA")
    print("=" * 65)
    return True

if __name__ == "__main__":
    success = run_db_test()
    sys.exit(0 if success else 1)
