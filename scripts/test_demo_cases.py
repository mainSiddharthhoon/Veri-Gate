import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

from pathlib import Path
from fastapi.testclient import TestClient

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
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
        return

    # 1. OCR Extract
    print("[1/3] Calling OCR Extract...")
    ocr_resp = client.post(
        "/api/ocr/extract",
        files={"file": (p_doc.name, p_doc.read_bytes(), "image/jpeg")},
        data={"document_type": "passport"}
    )
    if ocr_resp.status_code != 200:
        print(f"OCR FAILED: {ocr_resp.text}")
        return
        
    ocr_data = ocr_resp.json()
    session_id = ocr_data.get("processing", {}).get("session_id")
    if not session_id:
        # Invalid input case
        print(f"OCR Finished. Result: {ocr_data.get('processing', {}).get('errors')}")
        return
        
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
            print(f"Face Verify Error: {face_data['error_message']}")
        else:
            print(f"Face Verify Success. Match: {face_data.get('is_match')}")
    else:
        print(f"Face Verify FAILED: {face_resp.text}")

    # 3. Risk Assess
    print("[3/3] Calling Risk Assess...")
    risk_resp = client.post(f"/api/risk/assess/{session_id}")
    if risk_resp.status_code == 200:
        risk_data = risk_resp.json()
        assessment = risk_data.get("assessment", {})
        print("\n--- FINAL RESULT ---")
        print(f"Score:    {assessment.get('risk_score')}")
        print(f"Level:    {assessment.get('risk_level')}")
        print(f"Decision: {assessment.get('decision')}")
        print(f"Summary:  {assessment.get('summary')}")
        for f in risk_data.get("factors", []):
            print(f"  - [{f['severity']}] {f['factor_name']} (+{f['score_contribution']}): {f['message']}")
    else:
        print(f"Risk Assess FAILED: {risk_resp.text}")
    print("\n")

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
        )
    ]
    
    for case_num, doc, face, desc in cases:
        run_case(case_num, doc, face, desc)

if __name__ == '__main__':
    main()
