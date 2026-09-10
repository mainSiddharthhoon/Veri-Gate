import sys
import json
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

def run_fixture(folder_path: str):
    d = Path(folder_path)
    category = d.parent.name
    test_name = f"{category}/{d.name}"
    
    expected_file = d / "expected-outcome.txt"
    expected_text = expected_file.read_text(encoding="utf-8").strip() if expected_file.exists() else "No expected outcome provided."
    
    doc_img = None
    face_img = None
    
    for file in sorted(d.glob("*.*"), key=lambda f: f.stat().st_size):
        if file.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            if "document" in file.stem.lower():
                doc_img = file
            else:
                if face_img is None:
                    face_img = file
                
    if not doc_img or not face_img:
        result = {
            "test_name": test_name,
            "expected_text": expected_text,
            "error": "Missing document or face image.",
            "decision": "ERROR",
            "risk_level": "ERROR",
            "risk_score": 100,
            "summary": "Missing document or face image.",
            "match_result": "❌ Error"
        }
        print(f"RESULT_JSON:{json.dumps(result)}")
        return
        
    client = TestClient(app)
    doc_bytes = doc_img.read_bytes()
    face_bytes = face_img.read_bytes()
    
    doc_mime = "image/png" if doc_img.suffix.lower() == ".png" else "image/jpeg"
    face_mime = "image/png" if face_img.suffix.lower() == ".png" else "image/jpeg"
    
    # Phase 1: OCR
    resp_ocr = client.post(
        "/api/ocr/extract",
        files={
            "file": (doc_img.name, doc_bytes, doc_mime),
            "live_image": (face_img.name, face_bytes, face_mime)
        },
        data={"document_type": "passport"}
    )
    
    if resp_ocr.status_code == 400 and category == "invalid":
        err_detail = resp_ocr.json().get("detail", resp_ocr.text)
        result = {
            "test_name": test_name,
            "expected_text": expected_text,
            "decision": "REJECT",
            "risk_level": "HIGH",
            "risk_score": 100,
            "summary": f"Disqualified at input qualification gate: {err_detail}",
            "match_result": "✅ Logically Passed (Matched Expectation Category)"
        }
        print(f"RESULT_JSON:{json.dumps(result)}")
        return
    elif resp_ocr.status_code != 200:
        result = {
            "test_name": test_name,
            "expected_text": expected_text,
            "error": f"OCR failed ({resp_ocr.status_code}): {resp_ocr.text}",
            "decision": "ERROR",
            "risk_level": "ERROR",
            "risk_score": 100,
            "summary": f"OCR failed: {resp_ocr.text}",
            "match_result": "❌ Error"
        }
        print(f"RESULT_JSON:{json.dumps(result)}")
        return
        
    session_id = resp_ocr.json()["processing"]["session_id"]
    
    # Phase 2: Face
    resp_face = client.post(
        "/api/face/verify",
        data={"session_id": session_id},
        files={
            "document_image": (doc_img.name, doc_bytes, doc_mime),
            "live_image": (face_img.name, face_bytes, face_mime)
        }
    )
    
    # Phase 3: Risk
    resp_risk = client.post(f"/api/risk/assess/{session_id}")
    if resp_risk.status_code != 200:
        result = {
            "test_name": test_name,
            "expected_text": expected_text,
            "error": f"Risk assess failed ({resp_risk.status_code}): {resp_risk.text}",
            "decision": "ERROR",
            "risk_level": "ERROR",
            "risk_score": 100,
            "summary": f"Risk assess failed: {resp_risk.text}",
            "match_result": "❌ Error"
        }
        print(f"RESULT_JSON:{json.dumps(result)}")
        return
        
    risk_data = resp_risk.json()["assessment"]
    decision = risk_data.get("decision", "UNKNOWN")
    passed_logically = "✅ Logically Passed (Matched Expectation Category)" if category == "valid" and decision == "approve" else \
                       "✅ Logically Passed (Matched Expectation Category)" if category == "invalid" and decision in ["reject", "review"] else \
                       "❌ Logical Mismatch"
                       
    result = {
        "test_name": test_name,
        "expected_text": expected_text,
        "decision": decision.upper(),
        "risk_level": risk_data.get("risk_level", "UNKNOWN").upper(),
        "risk_score": risk_data.get("risk_score", 0),
        "summary": risk_data.get("summary", ""),
        "match_result": passed_logically
    }
    print(f"RESULT_JSON:{json.dumps(result)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_fixture(sys.argv[1])
