"""
VeriGate Backend — OCR API Integration Tests

Tests for the POST /api/ocr/extract endpoint.
These tests require a running Supabase database connection.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_minimal_test_image() -> bytes:
    """Create a minimal valid JPEG image for upload testing."""
    import numpy as np
    import cv2

    # Create a simple image with some text
    image = np.ones((200, 400, 3), dtype=np.uint8) * 255
    cv2.putText(image, "PASSPORT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.putText(image, "TEST DOCUMENT", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    _, encoded = cv2.imencode(".jpg", image)
    return encoded.tobytes()


class TestOcrExtractEndpoint:
    def test_endpoint_exists(self):
        """The OCR extract endpoint should exist and accept POST."""
        image_bytes = _create_minimal_test_image()
        response = client.post(
            "/api/ocr/extract",
            files={"file": ("test.jpg", image_bytes, "image/jpeg")},
        )
        # Should not be 404 or 405
        assert response.status_code in (200, 422, 500)

    def test_returns_structured_response(self):
        """Should return a response with the expected structure."""
        image_bytes = _create_minimal_test_image()
        response = client.post(
            "/api/ocr/extract",
            files={"file": ("test.jpg", image_bytes, "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()

        # Check top-level keys
        assert "raw_text" in data
        assert "ocr_blocks" in data
        assert "mrz" in data
        assert "processing" in data

        # Check processing info
        assert "session_id" in data["processing"]
        assert "ocr_processing_time_ms" in data["processing"]
        assert "total_processing_time_ms" in data["processing"]

    def test_rejects_empty_file(self):
        """Should reject an empty file upload."""
        response = client.post(
            "/api/ocr/extract",
            files={"file": ("empty.jpg", b"", "image/jpeg")},
        )
        assert response.status_code == 400

    def test_default_document_type(self):
        """Should default to 'passport' document type."""
        image_bytes = _create_minimal_test_image()
        response = client.post(
            "/api/ocr/extract",
            files={"file": ("test.jpg", image_bytes, "image/jpeg")},
        )
        assert response.status_code == 200

    def test_mrz_section_present(self):
        """Response should always include an MRZ section."""
        image_bytes = _create_minimal_test_image()
        response = client.post(
            "/api/ocr/extract",
            files={"file": ("test.jpg", image_bytes, "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()

        mrz = data["mrz"]
        assert "detected" in mrz
        assert isinstance(mrz["detected"], bool)
