import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

from pathlib import Path
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, '..', 'backend'))
sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

def run_case(case_num, doc_path, face_path, description):
    print("=" * 80)
    print(f"CASE {case_num}: {description}")
    print(f"Document: {doc_path}")
    print(f"Face:     {face_path}")
    print("-" * 80)

    p_doc = Path(doc_path)
    p_face = Path(face_path)

    if not p_doc.exists() or not p_face.exists():
        print("ERROR: Missing files!")
        return {"case": case_num, "run1": "ERROR", "run2": "ERROR", "consistent": "-", "final": "MISSING FILES"}

    # 1. OCR Extract
    print("[1/3] Calling OCR Extract...")
    ocr_resp = client.post(
        "/api/ocr/extract",
        files={"file": (p_doc.name, p_doc.read_bytes(), "image/jpeg")},
        data={"document_type": "passport"}
    )
    if ocr_resp.status_code != 200:
        print(f"OCR FAILED (Input Qualification might have failed): {ocr_resp.text}")
        return {"case": case_num, "run1": "-", "run2": "-", "consistent": "-", "final": "INPUT GATE FAIL"}
        
    ocr_data = ocr_resp.json()
    session_id = ocr_data.get("processing", {}).get("session_id")
    if not session_id:
        print(f"OCR Finished without session. Result: {ocr_data.get('processing', {}).get('errors')}")
        return {"case": case_num, "run1": "-", "run2": "-", "consistent": "-", "final": "OCR ERROR"}
        
    print(f"OCR Success. Session ID: {session_id}")

    # 2. Face Verify
    print("[2/3] Calling Face Verify...")
    face_resp = client.post(
        "/api/face/verify",
        data={"session_id": session_id},
        files={
            "document_image": (p_doc.name, p_doc.read_bytes(), "image/jpeg"),
            "live_image": (p_face.name, p_face.read_bytes(), "image/jpeg"),
        }
    )
    if face_resp.status_code == 200:
        face_data = face_resp.json()
        if face_data.get("error_message"):
            err_msg = face_data['error_message'].encode('ascii', 'replace').decode('ascii')
            print(f"Face Verify Error: {err_msg}")
        else:
            print(f"Face Verify Success. Match: {face_data.get('is_match')}")
    else:
        print(f"Face Verify FAILED (Input Qualification might have failed): {face_resp.text}")
        return {"case": case_num, "run1": "-", "run2": "-", "consistent": "-", "final": "FACE GATE FAIL"}

    # 3. Risk Assess
    print("[3/3] Calling Risk Assess...")
    risk_resp = client.post(f"/api/risk/assess/{session_id}")
    if risk_resp.status_code == 200:
        risk_data = risk_resp.json()
        assessment = risk_data.get("assessment", {})
        debug_run1 = risk_data.get("debug_run1")
        debug_run2 = risk_data.get("debug_run2")
        
        run1_str = f"{debug_run1['decision'].upper()} ({debug_run1['risk_level']})" if debug_run1 else "NONE"
        run2_str = f"{debug_run2['decision'].upper()} ({debug_run2['risk_level']})" if debug_run2 else "NONE"
        
        final_str = f"{assessment.get('decision', 'UNKNOWN').upper()} ({assessment.get('risk_level', 'UNKNOWN')})"
        provider = assessment.get("ai_provider", "unknown")
        
        consistent = "YES" if (debug_run1 and debug_run2 and debug_run1['decision'] == debug_run2['decision'] and debug_run1['risk_level'] == debug_run2['risk_level']) else "NO"

        print("\n--- FINAL RESULT ---")
        print(f"Provider: {provider}")
        print(f"Run 1:    {run1_str}")
        print(f"Run 2:    {run2_str}")
        print(f"Final:    {final_str}")
        print(f"Summary:  {assessment.get('summary')}")
        
        return {"case": case_num, "run1": run1_str, "run2": run2_str, "consistent": consistent, "final": final_str}
    else:
        print(f"Risk Assess FAILED: {risk_resp.text}")
        return {"case": case_num, "run1": "ERROR", "run2": "ERROR", "consistent": "-", "final": "ERROR"}

def main():
    base_dir = os.path.join(os.path.dirname(__file__), '..')
    
    cases = [
        (
            1, 
            os.path.join(base_dir, "demo_data", "valid", "document.jpg"),
            os.path.join(base_dir, "demo_data", "valid", "matching_face.jpg"),
            "Valid document + matching face"
        ),
        (
            2, 
            os.path.join(base_dir, "demo_data", "mismatch", "document.jpg"),
            os.path.join(base_dir, "demo_data", "mismatch", "different_face.jpg"),
            "Valid document + different face"
        ),
        (
            3, 
            os.path.join(base_dir, "demo_data", "tampered", "document.jpg"),
            os.path.join(base_dir, "demo_data", "tampered", "matching_face.jpg"),
            "Tampered document + matching face"
        ),
        (
            4, 
            os.path.join(base_dir, "demo_data", "invalid", "invalid_document.jpg"),
            os.path.join(base_dir, "demo_data", "invalid", "invalid_face.jpg"),
            "Invalid document + invalid/unusable face"
        ),
        (
            5, 
            os.path.join(base_dir, "demo_data", "invalid", "valid_document_invalid_face.jpg"),
            os.path.join(base_dir, "demo_data", "invalid", "invalid_face_only.jpg"),
            "Valid document + invalid/unusable face"
        ),
        (
            6, 
            os.path.join(base_dir, "demo_data", "tampered", "document.jpg"),
            os.path.join(base_dir, "demo_data", "mismatch", "different_face.jpg"),
            "Conflicting: Tampered doc + Mismatch face"
        )
    ]
    
    results = []
    for case_num, doc, face, desc in cases:
        res = run_case(case_num, doc, face, desc)
        results.append(res)
        print("\n")

    print("\n" + "=" * 80)
    print(f"{'Case':<6} | {'Run 1':<20} | {'Run 2':<20} | {'Consistent?':<12} | {'Final Result'}")
    print("-" * 80)
    for r in results:
        print(f"{r['case']:<6} | {r['run1']:<20} | {r['run2']:<20} | {r['consistent']:<12} | {r['final']}")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    main()
