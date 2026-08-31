import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import asyncio
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db

client = TestClient(app)

def verify():
    print("Loading test image...")
    image_path = Path("tests/test_data/synthetic_passport.jpg")
    if not image_path.exists():
        print(f"Error: image not found at {image_path}")
        return
        
    image_bytes = image_path.read_bytes()
    
    print("Calling OCR extract endpoint...")
    response = client.post(
        "/api/ocr/extract",
        files={"file": ("synthetic_passport.jpg", image_bytes, "image/jpeg")},
        data={"document_type": "passport"}
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code != 200:
        print(f"Response: {response.text}")
        return
        
    data = response.json()
    print("\n--- OCR API Response ---")
    print(f"MRZ Detected: {data['mrz']['detected']}")
    print(f"MRZ Line 1: {data['mrz']['line_1']}")
    print(f"MRZ Line 2: {data['mrz']['line_2']}")
    print(f"MRZ Checks Valid: {data['mrz']['all_checks_valid']}")
    
    print("\nExtracted Fields:")
    fields = data.get("extracted_fields") or {}
    for k, v in fields.items():
        print(f"  {k}: {v}")
        
    print("\nProcessing Info:")
    proc = data.get("processing") or {}
    session_id = proc.get("session_id")
    print(f"  Session ID: {session_id}")
    print(f"  OCR Processing Time: {proc.get('ocr_processing_time_ms')} ms")
    print(f"  Total Processing Time: {proc.get('total_processing_time_ms')} ms")
    print(f"  Errors: {proc.get('errors')}")

    # Verify Supabase records
    if session_id:
        print(f"\n--- Verifying Supabase Records for Session: {session_id} ---")
        db = get_db()
        
        # Check ocr_results
        ocr_res = db.table("ocr_results").select("*").eq("session_id", session_id).execute()
        if ocr_res.data:
            print(f"Found ocr_results record (ID: {ocr_res.data[0]['id']})")
            print(f"  Confidence Score: {ocr_res.data[0]['confidence_score']}")
            print(f"  Raw Text Length: {len(ocr_res.data[0]['raw_text'])}")
        else:
            print("ERROR: No ocr_results record found!")

        # Check documents
        doc_res = db.table("documents").select("*").eq("session_id", session_id).execute()
        if doc_res.data:
            print(f"Found documents record (ID: {doc_res.data[0]['id']})")
            print(f"  Document Number: {doc_res.data[0]['document_number']}")
            print(f"  Surname: {doc_res.data[0]['surname']}")
        else:
            print("ERROR: No documents record found!")

        # Check validation_results (Phase 3)
        val_res = db.table("validation_results").select("*").eq("session_id", session_id).execute()
        if val_res.data:
            vr = val_res.data[0]
            print(f"Found validation_results record (ID: {vr['id']})")
            print(f"  Is Valid: {vr['is_valid']}")
            print(f"  Checks Passed: {vr['checks_passed']}")
            print(f"  Checks Failed: {vr['checks_failed']}")
            print(f"  Checks Warned: {vr['checks_warned']}")

            # Check validation_checks
            checks_res = db.table("validation_checks").select("*").eq("validation_result_id", vr['id']).execute()
            if checks_res.data:
                print(f"Found {len(checks_res.data)} validation_checks record(s)")
                for chk in checks_res.data:
                    status_str = {"passed": "[PASS]", "failed": "[FAIL]", "warning": "[WARN]", "skipped": "[SKIP]"}.get(chk['status'], "[????]")
                    print(f"  {status_str} [{chk['check_category']}] {chk['check_name']}: {chk['status']} - {chk['message']}")
            else:
                print("ERROR: No validation_checks records found!")
        else:
            print("ERROR: No validation_results record found!")

        # Check audit log
        audit_res = db.table("audit_log").select("*").eq("session_id", session_id).execute()
        if audit_res.data:
            print(f"Found {len(audit_res.data)} audit_log record(s)")
            for entry in audit_res.data:
                print(f"  Event Type: {entry['event_type']}")
        else:
            print("ERROR: No audit_log record found!")

        # Check tampering analysis
        print("-" * 50)
        print("4. TAMPERING ANALYSIS")
        print("-" * 50)
        
        tampering = db.table("tampering_analyses").select("*").eq("session_id", session_id).maybe_single().execute()
        if tampering.data:
            t_data = tampering.data
            print(f"Tamper Score:  {t_data['tamper_score']:.2f}")
            print(f"Suspicious:    {t_data['is_suspicious']}")
            
            signals = db.table("tampering_signals").select("*").eq("tampering_analysis_id", t_data["id"]).execute()
            for sig in signals.data:
                print(f"  - [{sig['signal_type']}] {sig['signal_name']}: score={sig['score']:.2f} -> {sig['message']}")
                if sig.get('evidence_image_path'):
                    print(f"    Evidence -> {sig['evidence_image_path']}")
        else:
            print("No tampering analysis found for this session.")

        # ---------------------------------------------------------
        # Phase 5: Face Verification
        # ---------------------------------------------------------
        print("\n[Phase 5] Running Face Verification...")
        
        # Now the backend handles cropping server-side
        doc_face_bytes = image_bytes
        live_face_bytes = image_bytes

        face_response = client.post(
            "/api/face/verify",
            data={"session_id": session_id},
            files={
                "document_image": ("doc_face.jpg", doc_face_bytes, "image/jpeg"),
                "live_image": ("live_face.jpg", live_face_bytes, "image/jpeg"),
            }
        )
        
        if face_response.status_code == 200:
            face_data = face_response.json()
            if face_data.get("error_message"):
                print(f"[WARN] Face Verification returned an error: {face_data['error_message']}")
            else:
                match = "YES" if face_data.get("is_match") else "NO"
                print(f"[OK] Face Verification complete.")
                print(f"   Match: {match}")
                print(f"   Distance: {face_data.get('distance', 0.0):.4f} (Threshold: {face_data.get('threshold', 0.0):.4f})")
                print(f"   Model: {face_data.get('model_name')}")
        else:
            print(f"[FAIL] Face Verification failed: {face_response.text}")

        # ---------------------------------------------------------
        # Phase 6: Risk Scoring
        # ---------------------------------------------------------
        print("\n[Phase 6] Running Risk Scoring...")
        risk_response = client.post(f"/api/risk/assess/{session_id}")
        
        if risk_response.status_code == 200:
            risk_data = risk_response.json()
            assessment = risk_data.get("assessment", {})
            factors = risk_data.get("factors", [])
            
            print(f"[OK] Risk Scoring complete.")
            print(f"   Score: {assessment.get('risk_score')}")
            print(f"   Level: {assessment.get('risk_level')}")
            print(f"   Decision: {assessment.get('decision')}")
            print(f"   Summary: {assessment.get('summary')}")
            print("   Factors:")
            for f in factors:
                print(f"      - [{f['severity']}] {f['factor_name']} (Source: {f['factor_source']}) -> +{f['score_contribution']}")
                print(f"        Reason: {f['message']}")
        else:
            print(f"[FAIL] Risk Scoring failed: {risk_response.text}")
            
        print("-" * 50)
        print("Verification Completed Successfully.")

if __name__ == "__main__":
    verify()
