import sys
import json
import time
from pathlib import Path
from PIL import Image
import io

# Setup path
sys.path.append(str(Path(__file__).parent))

from app.services.ai_reasoning import qualify_inputs, assess_evidence

TEST_DATA_DIR = Path(__file__).parent / "tests" / "test_data"
PASSPORT_IMAGE = TEST_DATA_DIR / "synthetic_passport.jpg"

def get_image_bytes(path):
    with open(path, "rb") as f:
        return f.read()

def get_dummy_image():
    img = Image.new('RGB', (100, 100), color = 'red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()

def run_tests():
    print("Loading images...")
    valid_image = get_image_bytes(PASSPORT_IMAGE)
    invalid_image = get_dummy_image()

    print("\n==============================================")
    print("TEST 1: Gemma Input Qualification (VALID)")
    print("==============================================")
    t0 = time.time()
    try:
        res = qualify_inputs(valid_image, valid_image)
        latency = time.time() - t0
        print(f"Latency: {latency:.2f}s")
        print(f"Result: {res.model_dump_json(indent=2)}")
        assert res.input_valid is True, "Expected valid qualification"
    except Exception as e:
        print(f"Test 1 Failed: {e}")

    print("\n==============================================")
    print("TEST 2: Gemma Input Qualification (INVALID)")
    print("==============================================")
    t0 = time.time()
    try:
        res = qualify_inputs(invalid_image, invalid_image)
        latency = time.time() - t0
        print(f"Latency: {latency:.2f}s")
        print(f"Result: {res.model_dump_json(indent=2)}")
        assert res.input_valid is False, "Expected invalid qualification"
    except Exception as e:
        print(f"Test 2 Failed: {e}")

    print("\n==============================================")
    print("TEST 3: Gemma Main Investigation (VALID)")
    print("==============================================")
    
    ocr_data = {"document_number": "123456789", "name": "JOHN DOE"}
    mrz_data = {"document_number": "123456789", "valid": True}
    validation_data = [{"check": "Expiration", "passed": True}]
    tampering_data = {"suspicious": False}
    face_data = {"is_match": True, "distance": 0.1, "threshold": 0.4}

    t0 = time.time()
    try:
        final_assessment, run1, run2, provider = assess_evidence(
            valid_image,
            valid_image,
            None,
            ocr_data,
            mrz_data,
            validation_data,
            tampering_data,
            face_data
        )
        latency = time.time() - t0
        print(f"Latency: {latency:.2f}s")
        print(f"Provider used: {provider}")
        print(f"Result: {final_assessment.model_dump_json(indent=2)}")
        assert provider == "gemma", "Expected provider to be gemma, fallback occurred!"
    except Exception as e:
        print(f"Test 3 Failed: {e}")

if __name__ == "__main__":
    run_tests()
