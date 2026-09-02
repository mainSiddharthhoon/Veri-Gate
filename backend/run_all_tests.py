import os
import glob
from pathlib import Path
import httpx
import json

API_URL = "http://127.0.0.1:8000"

def run_all():
    base_dir = Path(r"D:\Hackahon- Projects\Veri-Gate\testing-data")
    folders = []
    
    # gather valid tests
    valid_dir = base_dir / "valid"
    if valid_dir.exists():
        for d in valid_dir.iterdir():
            if d.is_dir():
                folders.append(("valid", d))
                
    # gather invalid tests
    invalid_dir = base_dir / "invalid"
    if invalid_dir.exists():
        for d in invalid_dir.iterdir():
            if d.is_dir():
                folders.append(("invalid", d))
                
    md_output = "# Veri-Gate E2E Test Results\n\n"
    md_output += "This artifact contains the results of running all the test fixtures located in the `testing-data/` folder against the VeriGate local verification pipeline.\n\n---\n\n"
    
    for category, d in folders:
        test_name = f"{category}/{d.name}"
        print(f"Running test: {test_name}")
        
        expected_file = d / "expected-outcome.txt"
        expected_text = expected_file.read_text(encoding="utf-8").strip() if expected_file.exists() else "No expected outcome provided."
        
        # find images
        doc_img = None
        face_img = None
        
        for file in d.glob("*.*"):
            if file.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                if file.stem.startswith("document"):
                    doc_img = file
                else:
                    if face_img is None:
                        face_img = file
                    
        if not doc_img or not face_img:
            md_output += f"## ⚠️ Test: {test_name}\n"
            md_output += f"**Error**: Missing document or face image.\n\n---\n\n"
            continue
            
        try:
            with httpx.Client(timeout=120) as client:
                doc_bytes = doc_img.read_bytes()
                face_bytes = face_img.read_bytes()
                
                # Phase 1: OCR
                print("  - Running OCR...")
                resp_ocr = client.post(
                    f"{API_URL}/api/ocr/extract",
                    files={
                        "file": (doc_img.name, doc_bytes, "image/jpeg"),
                        "live_image": (face_img.name, face_bytes, "image/jpeg")
                    },
                    data={"document_type": "passport"}
                )
                if resp_ocr.status_code != 200:
                    raise Exception(f"OCR failed: {resp_ocr.text}")
                    
                session_id = resp_ocr.json()["processing"]["session_id"]
                
                # Phase 2: Face
                print("  - Running Face Verification...")
                resp_face = client.post(
                    f"{API_URL}/api/face/verify",
                    data={"session_id": session_id},
                    files={
                        "document_image": (doc_img.name, doc_bytes, "image/jpeg"),
                        "live_image": (face_img.name, face_bytes, "image/jpeg")
                    }
                )
                if resp_face.status_code != 200:
                    raise Exception(f"Face verify failed: {resp_face.text}")
                    
                # Phase 3: Risk
                print("  - Running Risk Assessment...")
                resp_risk = client.post(f"{API_URL}/api/risk/assess/{session_id}")
                if resp_risk.status_code != 200:
                    raise Exception(f"Risk assess failed: {resp_risk.text}")
                    
                risk_data = resp_risk.json()["assessment"]
                
                md_output += f"## 🧪 Test: `{test_name}`\n\n"
                md_output += f"**Expected Outcome**: {expected_text}\n\n"
                md_output += f"**Actual Decision**: `{risk_data.get('decision', 'UNKNOWN').upper()}`\n"
                md_output += f"**Risk Level**: `{risk_data.get('risk_level', 'UNKNOWN').upper()}`\n"
                md_output += f"**Score**: {risk_data.get('risk_score', 'UNKNOWN')}/100\n\n"
                md_output += f"**Summary**: {risk_data.get('summary', '')}\n\n"
                
                # Basic sanity check text
                passed_logically = "✅ Logically Passed (Matched Expectation Category)" if category == "valid" and risk_data.get('decision') == "approve" else \
                                   "✅ Logically Passed (Matched Expectation Category)" if category == "invalid" and risk_data.get('decision') in ["reject", "review"] else \
                                   "❌ Logical Mismatch"
                                   
                md_output += f"**Match Result**: {passed_logically}\n\n"
                md_output += "---\n\n"
                
        except Exception as e:
            md_output += f"## ❌ Test: {test_name}\n"
            md_output += f"**Expected Outcome**: {expected_text}\n\n"
            md_output += f"**Error**: `{str(e)}`\n\n"
            md_output += "---\n\n"

    # Write the artifact
    out_path = Path(r"C:\Users\Arvindbhai\.gemini\antigravity-ide\brain\c83dd204-0809-4fd9-8780-d7dc014e7a61\test_results.md")
    out_path.write_text(md_output, encoding="utf-8")
    print(f"\nTests complete. Wrote {out_path}")

if __name__ == "__main__":
    run_all()
