import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

from pathlib import Path
from app.services.ocr_pipeline import run_ocr_pipeline
from app.database.repositories import create_ocr_result, create_document
from app.core.database import get_db

def verify():
    print("Loading test image...")
    image_path = Path("backend/tests/test_data/synthetic_passport.jpg")
    if not image_path.exists():
        print(f"Error: image not found at {image_path}")
        return
        
    image_bytes = image_path.read_bytes()
    
    print("Running OCR Pipeline...")
    db = get_db()
    result = run_ocr_pipeline(image_bytes, db)
    
    print("\n--- OCR Pipeline Response ---")
    print(f"Session ID: {result.session_id}")
    print(f"MRZ Detected: {result.mrz_detected}")
    if result.mrz_detected:
        print(f"MRZ Line 1: {result.mrz_lines[0]}")
        print(f"MRZ Line 2: {result.mrz_lines[1]}")
    print(f"MRZ Checks Valid: {result.mrz_all_valid}")
    
    print("\nExtracted Fields:")
    fields = result.document_fields or {}
    for k, v in fields.items():
        print(f"  {k}: {v}")
        
    print("\nProcessing Info:")
    print(f"  OCR Processing Time: {result.ocr_processing_time_ms} ms")
    print(f"  Total Processing Time: {result.total_processing_time_ms} ms")
    print(f"  Errors: {result.errors}")

    print("\nWriting to Supabase via Repositories...")
    # It's already written by run_ocr_pipeline! Let's verify records.
    session_id = result.session_id
    
    # Verify records exist
    print(f"\n--- Verifying Supabase Records for Session: {session_id} ---")
    
    ocr_res = db.table("ocr_results").select("*").eq("session_id", session_id).execute()
    if ocr_res.data:
        print(f"Found ocr_results record (ID: {ocr_res.data[0]['id']})")
    else:
        print("ERROR: No ocr_results record found!")

    doc_res = db.table("documents").select("*").eq("session_id", session_id).execute()
    if doc_res.data:
        print(f"Found documents record (ID: {doc_res.data[0]['id']})")
    else:
        print("ERROR: No documents record found!")

if __name__ == "__main__":
    verify()
