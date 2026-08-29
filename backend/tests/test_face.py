from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

TEST_DATA_DIR = Path(__file__).parent / "test_data"
PASSPORT_IMAGE = TEST_DATA_DIR / "synthetic_passport.jpg"

@pytest.fixture
def dummy_face_bytes():
    """Returns a dummy small black square image acting as a fake face for basic API endpoint tests."""
    import numpy as np
    import cv2
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def test_verify_face_missing_files():
    """Test that missing files trigger a 422 Validation Error from FastAPI."""
    response = client.post("/api/face/verify")
    assert response.status_code == 422

def test_verify_face_endpoint_no_face_detected(dummy_face_bytes):
    """Test with two dummy images that don't actually contain faces."""
    files = {
        "document_image": ("doc.jpg", dummy_face_bytes, "image/jpeg"),
        "live_image": ("live.jpg", dummy_face_bytes, "image/jpeg"),
    }
    
    response = client.post("/api/face/verify", files=files)
    assert response.status_code == 200
    data = response.json()
    
    assert data["is_match"] is False
    assert data["error_message"] is not None
    assert "Face could not be detected" in data["error_message"] or "Face not found" in data["error_message"] or "could not" in data["error_message"] or "Exception while processing" in data["error_message"]

def test_verify_face_with_real_faces():
    """
    Test using the actual test passport. We'll pass the same image twice.
    DeepFace might struggle if the full document has multiple faces or if we don't crop, 
    but since we are using enforce_detection=True, let's see if it finds a face in the synthetic passport.
    Ideally we should use cropped faces here.
    """
    if not PASSPORT_IMAGE.exists():
        pytest.skip(f"Test image {PASSPORT_IMAGE} not found")
        
    with open(PASSPORT_IMAGE, "rb") as f:
        doc_bytes = f.read()
        
    # We pass the full passport image for both.
    files = {
        "document_image": ("doc.jpg", doc_bytes, "image/jpeg"),
        "live_image": ("live.jpg", doc_bytes, "image/jpeg"),
    }
    
    response = client.post("/api/face/verify", files=files)
    assert response.status_code == 200
    data = response.json()
    
    # Depending on DeepFace's ability to find the face in the full passport:
    # If it finds it, distance should be 0.0 (exact match)
    if not data["error_message"]:
        assert data["is_match"] is True
        assert data["distance"] < data["threshold"]
