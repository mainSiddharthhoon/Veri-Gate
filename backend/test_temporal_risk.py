import os, sys, json
from dotenv import load_dotenv
load_dotenv('../.env')

from supabase import create_client
db = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_ANON_KEY'])

# get latest session_id
res = db.table('screening_sessions').select('id, document_image_path, person_image_path').order('created_at', desc=True).limit(1).execute()
session_id = res.data[0]['id']
doc_path = res.data[0]['document_image_path']
face_path = res.data[0]['person_image_path']
print(f'Using Session: {session_id}')

import os, shutil
os.makedirs('uploads', exist_ok=True)
real_doc = r"D:\new-download\VGX-260902-11-document.png"

from PIL import Image
if doc_path:
    img = Image.open(real_doc).convert('RGB')
    img.save(doc_path, 'JPEG')
if face_path:
    img = Image.open(real_doc).convert('RGB')
    img.save(face_path, 'JPEG')

import sys
sys.path.append('.')
from app.services.risk_scoring import _calculate_temporal_evidence
from app.services.ai_reasoning import assess_evidence

def run_test(scenario, dob, issue, expiry):
    print(f'\n======================================')
    print(f'--- TEST: {scenario} ---')
    print(f'======================================')
    
    # Mock document data
    doc_data = {
        'date_of_birth': dob,
        'date_of_issue': issue,
        'date_of_expiry': expiry
    }
    temporal_data = _calculate_temporal_evidence(doc_data)
    print("CALCULATED TEMPORAL DATA:", json.dumps(temporal_data, indent=2))
    
    # Mock OCR data to align with our tests (so Gemma doesn't get confused)
    ocr_data = {
        'date_of_birth': dob,
        'date_of_issue': issue,
        'date_of_expiry': expiry
    }
    
    try:
        with open(doc_path, 'rb') as f: doc_bytes = f.read()
        with open(face_path, 'rb') as f: face_bytes = f.read()
        
        result, _, _, _ = assess_evidence(
            document_image=doc_bytes,
            face_image=face_bytes,
            tampering_image=None,
            ocr_data=ocr_data,
            mrz_data={},
            validation_data=[],
            tampering_data={'suspicious': False},
            face_data={'match': True, 'distance': 0.1},
            temporal_data=temporal_data
        )
        print(f"Decision: {result.decision}")
        print(f"Risk Level: {result.risk_level}")
        print(f"Summary: {result.report}")
    except Exception as e:
        print(f'Error: {e}')

# Test 1: Future DOB -> MUST fail
run_test('Future DOB', '2050-01-01', '2020-01-01', '2030-01-01')

# Test 2: Expired document -> MUST fail
run_test('Expired Document', '1990-01-01', '2010-01-01', '2020-01-01')

# Test 3: Valid DOB and valid expiry -> MUST remain valid
run_test('Valid', '1990-01-01', '2020-01-01', '2030-01-01')

# Test 4: Old DOB -> Gemma must identify discrepancy
run_test('Old DOB Discrepancy', '1920-01-01', '2020-01-01', '2030-01-01')

# Test 5: Document with no issue date -> MUST NOT automatically fail
run_test('No Issue Date', '1990-01-01', None, '2030-01-01')

# Test 6: Document with no expiry date -> MUST NOT automatically fail
run_test('No Expiry Date', '1990-01-01', '2020-01-01', None)


