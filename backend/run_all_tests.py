import os
import json
import time
from pathlib import Path
import httpx
from fpdf import FPDF

API_URL = "http://127.0.0.1:8000"

def safe_get(d, keys, default="N/A"):
    curr = d
    for k in keys:
        if isinstance(curr, dict) and k in curr:
            curr = curr[k]
        else:
            return default
    return curr

class PDFReport(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Veri-Gate E2E Test Report", ln=True, align="C")
        self.ln(5)

    def chapter_title(self, title):
        self.set_font("Arial", "B", 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, ln=True, fill=True)
        self.ln(2)

    def chapter_body(self, text):
        self.set_font("Arial", "", 10)
        # Handle unicode encoding for FPDF
        clean_text = str(text).encode('latin-1', 'replace').decode('latin-1')
        self.multi_cell(0, 6, clean_text)
        self.ln(2)

def run_all():
    base_dir = Path(r"D:\Hackahon- Projects\Veri-Gate\testing-data")
    folders = []
    
    for category in ["valid", "invalid"]:
        cat_dir = base_dir / category
        if cat_dir.exists():
            for d in cat_dir.iterdir():
                if d.is_dir():
                    folders.append((category, d))
                    
    results_json = []
    
    pdf = PDFReport()
    pdf.add_page()
    
    for category, d in folders:
        test_name = f"{category}/{d.name}"
        print(f"\n========================================================")
        print(f"Running test: {test_name}")
        
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
            print(f"Skipping {test_name}: missing images.")
            continue

        test_result = {
            "test_name": test_name,
            "expected_outcome": expected_text,
            "category": category,
        }

        pdf.chapter_title(f"Test: {test_name}")
        pdf.chapter_body(f"Expected: {expected_text}")

        import subprocess
        print("  - Starting fresh backend server for test...")
        server_proc = subprocess.Popen(
            [r"d:\Hackahon- Projects\Veri-Gate\venv\Scripts\python.exe", "start_server.py"],
            cwd=r"d:\Hackahon- Projects\Veri-Gate\backend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for server readiness
        for _ in range(60):
            try:
                resp = httpx.get(f"{API_URL}/api/health", timeout=1.0)
                if resp.status_code == 200:
                    break
            except:
                time.sleep(1)
        else:
            print("  - Server failed to start in time!")

        try:
            with httpx.Client(timeout=120) as client:
                doc_bytes = doc_img.read_bytes()
                face_bytes = face_img.read_bytes()
                
                print("  - Running OCR...")
                resp_ocr = client.post(
                    f"{API_URL}/api/ocr/extract",
                    files={
                        "file": (doc_img.name, doc_bytes, "image/jpeg"),
                        "live_image": (face_img.name, face_bytes, "image/jpeg")
                    },
                    data={"document_type": "passport"}
                )
                
                if resp_ocr.status_code == 400 and category == "invalid":
                    err_detail = resp_ocr.json().get("detail", resp_ocr.text)
                    test_result.update({
                        "decision": "reject",
                        "risk_level": "high",
                        "risk_score": 100,
                        "summary": f"Disqualified at input qualification gate: {err_detail}",
                        "match_result": "PASS"
                    })
                    results_json.append(test_result)
                    pdf.chapter_body(f"Actual Decision: REJECT\nRisk Level: HIGH\nScore: 100/100\nSummary: {test_result['summary']}\nMatch Result: PASS")
                    pdf.ln(5)
                    time.sleep(1)
                    continue
                elif resp_ocr.status_code != 200:
                    raise Exception(f"OCR failed: {resp_ocr.text}")
                    
                ocr_data = resp_ocr.json()
                session_id = ocr_data["processing"]["session_id"]
                test_result["session_id"] = session_id
                
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
                    
                print("  - Running Risk Assessment...")
                resp_risk = client.post(f"{API_URL}/api/risk/assess/{session_id}")
                if resp_risk.status_code != 200:
                    raise Exception(f"Risk assess failed: {resp_risk.text}")
                
                risk_data = resp_risk.json().get("assessment", {})
                
                # Fetch full screening details
                print("  - Fetching Screening Details...")
                resp_screen = client.get(f"{API_URL}/api/screening/{session_id}")
                full_screen = resp_screen.json() if resp_screen.status_code == 200 else {}
                
                factors = risk_data.get("risk_factors", [])
                
                test_result.update({
                    "decision": risk_data.get('decision', 'UNKNOWN'),
                    "risk_level": risk_data.get('risk_level', 'UNKNOWN'),
                    "risk_score": risk_data.get('risk_score', 'UNKNOWN'),
                    "summary": risk_data.get('report', risk_data.get('summary', '')),
                    "ai_provider": risk_data.get("ai_provider", "N/A"),
                    "ai_model": risk_data.get("ai_model", "N/A"),
                    "identity_details": full_screen.get("extracted_data", {}),
                    "document_validation_status": safe_get(full_screen, ["document_validation", "status"]),
                    "validation_checks": safe_get(full_screen, ["document_validation", "checks"]),
                    "mrz_result": full_screen.get("mrz_data", {}),
                    "face_verification": full_screen.get("face_verification", {}),
                    "tampering_result": full_screen.get("tampering", {}),
                    "risk_factors": factors
                })
                
                actual_dec = risk_data.get('decision', 'UNKNOWN').lower()
                passed_logically = "PASS" if category == "valid" and actual_dec == "approve" else \
                                   "PASS" if category == "invalid" and actual_dec in ["reject", "review"] else \
                                   "FAIL"
                                   
                test_result["match_result"] = passed_logically
                results_json.append(test_result)
                
                print(f"[SESSION {session_id}] [FINAL] {actual_dec.upper()} • {test_result['risk_level'].upper()} • {test_result['risk_score']}/100")
                
                pdf.chapter_body(
                    f"Session ID: {session_id}\n"
                    f"Actual Decision: {test_result['decision'].upper()}\n"
                    f"Risk Level: {test_result['risk_level'].upper()}\n"
                    f"Score: {test_result['risk_score']}/100\n"
                    f"AI Provider: {test_result['ai_provider']} ({test_result['ai_model']})\n"
                    f"Summary: {test_result['summary']}\n"
                    f"Match Result: {passed_logically}"
                )
                
                pdf.set_font("Arial", "I", 10)
                pdf.multi_cell(0, 6, "Details: " + json.dumps({
                    "face": test_result["face_verification"],
                    "validation": test_result["document_validation_status"],
                    "tampering": test_result["tampering_result"].get("tampering_detected", "N/A"),
                    "factors": factors
                }).encode('latin-1', 'replace').decode('latin-1'))
                pdf.ln(5)
                time.sleep(1)
                
        except Exception as e:
            err_msg = str(e)
            test_result["error"] = err_msg
            test_result["match_result"] = "ERROR"
            results_json.append(test_result)
            pdf.chapter_body(f"Error: {err_msg}")
            pdf.ln(5)
        finally:
            print("  - Stopping server...")
            server_proc.terminate()
            server_proc.wait()

    reports_dir = Path("d:/Hackahon- Projects/Veri-Gate/backend/test-results/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = reports_dir / "combined_report.json"
    json_path.write_text(json.dumps(results_json, indent=2), encoding="utf-8")
    
    pdf_path = reports_dir / "combined_report.pdf"
    try:
        pdf.output(str(pdf_path))
    except Exception as e:
        print(f"PDF generation error: {e}")
        
    print(f"\nTests complete. Reports saved to {reports_dir}")

if __name__ == "__main__":
    run_all()
