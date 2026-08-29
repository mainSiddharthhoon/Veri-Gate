"""
VeriGate Backend — Image Preprocessing Service

Prepares document images for optimal OCR accuracy.
Applies standard image processing techniques:
grayscale conversion, denoising, and adaptive thresholding.
"""

from __future__ import annotations

import cv2
import numpy as np


def preprocess_for_ocr(image_bytes: bytes) -> np.ndarray:
    """Convert raw image bytes into a preprocessed image optimized for OCR.

    Pipeline:
        1. Decode image from bytes
        2. Convert to grayscale
        3. Apply light denoising
        4. Apply adaptive thresholding for better text contrast

    Args:
        image_bytes: Raw image file content (JPEG, PNG, etc.)

    Returns:
        Preprocessed image as a numpy array (grayscale, uint8).

    Raises:
        ValueError: If the image bytes cannot be decoded.
    """
    # Decode image from bytes
    if len(image_bytes) == 0:
        raise ValueError("Could not decode image from provided bytes.")
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Could not decode image from provided bytes.")

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Light denoising — preserve text edges while reducing noise
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # Adaptive thresholding — works better than global threshold
    # for documents with uneven lighting
    binary = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=15,
        C=8,
    )

    return binary


def decode_image(image_bytes: bytes) -> np.ndarray:
    """Decode raw image bytes into a BGR numpy array (no preprocessing).

    Args:
        image_bytes: Raw image file content.

    Returns:
        Image as a BGR numpy array.

    Raises:
        ValueError: If the image bytes cannot be decoded.
    """
    if len(image_bytes) == 0:
        raise ValueError("Could not decode image from provided bytes.")
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Could not decode image from provided bytes.")

    return image


def encode_image_to_bytes(image: np.ndarray, fmt: str = ".jpg") -> bytes:
    """Encode a numpy image array to bytes.

    Args:
        image: Image as a numpy array.
        fmt: Output format (e.g., '.jpg', '.png').

    Returns:
        Encoded image bytes.
    """
    success, encoded = cv2.imencode(fmt, image)
    if not success:
        raise ValueError(f"Could not encode image to {fmt}")
    return encoded.tobytes()
