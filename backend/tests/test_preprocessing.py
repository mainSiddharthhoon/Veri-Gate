"""
VeriGate Backend — Preprocessing Tests

Tests for image preprocessing functions.
"""

import pytest
import numpy as np
import cv2

from app.services.preprocessing import (
    preprocess_for_ocr,
    decode_image,
    encode_image_to_bytes,
)


def _create_test_image_bytes(width: int = 200, height: int = 100) -> bytes:
    """Create a simple test image as JPEG bytes."""
    image = np.ones((height, width, 3), dtype=np.uint8) * 200
    # Add some text-like features
    cv2.putText(image, "TEST", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    _, encoded = cv2.imencode(".jpg", image)
    return encoded.tobytes()


class TestPreprocessForOcr:
    def test_returns_numpy_array(self):
        """Should return a numpy array."""
        image_bytes = _create_test_image_bytes()
        result = preprocess_for_ocr(image_bytes)
        assert isinstance(result, np.ndarray)

    def test_output_is_grayscale(self):
        """Output should be single-channel (grayscale)."""
        image_bytes = _create_test_image_bytes()
        result = preprocess_for_ocr(image_bytes)
        assert len(result.shape) == 2  # 2D = grayscale

    def test_output_dimensions_reasonable(self):
        """Output dimensions should match input."""
        image_bytes = _create_test_image_bytes(400, 300)
        result = preprocess_for_ocr(image_bytes)
        assert result.shape[0] == 300  # height
        assert result.shape[1] == 400  # width

    def test_output_is_binary(self):
        """After adaptive thresholding, values should be 0 or 255."""
        image_bytes = _create_test_image_bytes()
        result = preprocess_for_ocr(image_bytes)
        unique_values = np.unique(result)
        assert all(v in (0, 255) for v in unique_values)

    def test_invalid_bytes_raises(self):
        """Should raise ValueError for invalid image bytes."""
        with pytest.raises(ValueError, match="Could not decode"):
            preprocess_for_ocr(b"not an image")

    def test_empty_bytes_raises(self):
        """Should raise ValueError for empty bytes."""
        with pytest.raises(ValueError, match="Could not decode"):
            preprocess_for_ocr(b"")


class TestDecodeImage:
    def test_decode_valid_image(self):
        """Should decode valid JPEG bytes to BGR array."""
        image_bytes = _create_test_image_bytes()
        result = decode_image(image_bytes)
        assert isinstance(result, np.ndarray)
        assert len(result.shape) == 3  # 3D = color
        assert result.shape[2] == 3   # BGR channels

    def test_invalid_bytes_raises(self):
        """Should raise ValueError for invalid bytes."""
        with pytest.raises(ValueError, match="Could not decode"):
            decode_image(b"not an image")


class TestEncodeImage:
    def test_encode_to_jpg(self):
        """Should encode numpy array to JPEG bytes."""
        image = np.ones((100, 200, 3), dtype=np.uint8) * 128
        result = encode_image_to_bytes(image, ".jpg")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_encode_to_png(self):
        """Should encode numpy array to PNG bytes."""
        image = np.ones((100, 200, 3), dtype=np.uint8) * 128
        result = encode_image_to_bytes(image, ".png")
        assert isinstance(result, bytes)
        assert len(result) > 0
