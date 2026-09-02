import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
import time
from pathlib import Path
from pprint import pprint

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, '..', 'backend'))
sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_test(name, doc_path, face_path):
    print("=" * 80)
    print(f"TEST: {name}")
    print("=" * 80)
    
    p_doc = Path(doc_path)
    p_face = Path(face_path)
    
    if not p_doc.exists() or not p_face.exists():
        print("ERROR: Missing files")
        return

    start_time = time.time()
    
    print("[1] Running Input Qualification + OCR")
    ocr_resp = client.post(
        "/api/ocr/extract",
        files={
            "file": (p_doc.name, p_doc.read_bytes(), "image/jpeg"),
            "live_image": (p_face.name, p_face.read_bytes(), "image/jpeg"),
        },
        data={"document_type": "passport"}
    )
    
    print(f"HTTP Status: {ocr_resp.status_code}")
    
    if ocr_resp.status_code != 200:
        print(f"Qualification Failed (Expected for Invalid): {ocr_resp.text}")
        print(f"Total Latency: {time.time() - start_time:.2f}s")
        return
        
    ocr_data = ocr_resp.json()
    session_id = ocr_data.get("processing", {}).get("session_id")
    print(f"Qualification Passed. Session ID: {session_id}")
    
    if "input qualification - valid" in name.lower():
        print(f"Total Latency: {time.time() - start_time:.2f}s")
        return
        
    print("[2] Running Face Verification")
    face_resp = client.post(
        "/api/face/verify",
        data={"session_id": session_id},
        files={
            "document_image": (p_doc.name, p_doc.read_bytes(), "image/jpeg"),
            "live_image": (p_face.name, p_face.read_bytes(), "image/jpeg"),
        }
    )
    
    print("[3] Running Risk Assessment (Main AI Investigation)")
    risk_start = time.time()
    risk_resp = client.post(f"/api/risk/assess/{session_id}")
    risk_latency = time.time() - risk_start
    
    print(f"Risk HTTP Status: {risk_resp.status_code}")
    
    if risk_resp.status_code == 200:
        risk_data = risk_resp.json()
        print(f"Main AI Investigation Latency: {risk_latency:.2f}s")
        print("\nStructured Result:")
        pprint(risk_data.get("assessment", {}))
    else:
        print(f"Risk Assessment Error: {risk_resp.text}")
        
    print(f"\nTotal Pipeline Latency: {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    base = Path(current_dir).parent / "demo_data"
    
    run_test(
        "Ollama input qualification - Valid",
        base / "valid" / "document.jpg",
        base / "valid" / "matching_face.jpg"
    )
    
    # run_test(
    #     "Ollama input qualification - Invalid",
    #     base / "invalid" / "invalid_document.jpg",
    #     base / "invalid" / "invalid_face.jpg"
    # )
    
    run_test(
        "Ollama main investigation - Valid",
        base / "valid" / "document.jpg",
        base / "valid" / "matching_face.jpg"
    )
