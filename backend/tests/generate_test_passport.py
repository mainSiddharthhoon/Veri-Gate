"""
Synthetic passport image generator for testing.

Creates a simple passport-like image with known MRZ lines that can be
verified against expected values. This is NOT a real document — it's
a minimal test fixture with text that PaddleOCR can read.
"""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np


# Known test MRZ lines — matches the seed data for SMITH, JAMES EDWARD
TEST_MRZ_LINE_1 = "P<GBRSMITH<<JAMES<EDWARD<<<<<<<<<<<<<<<<<<<<"
TEST_MRZ_LINE_2 = "AB12345671GBR8503150M2907206<<<<<<<<<<<<<<04"

# Expected parsed values from this MRZ
EXPECTED_FIELDS = {
    "document_code": "P",
    "issuing_country": "GBR",
    "surname": "SMITH",
    "given_names": "JAMES EDWARD",
    "document_number": "AB1234567",
    "nationality": "GBR",
    "date_of_birth": "850315",
    "sex": "M",
    "date_of_expiry": "290720",
    "personal_number": "",
}


def generate_synthetic_passport(output_path: str | Path | None = None) -> np.ndarray:
    """Generate a synthetic passport-like image for OCR testing.

    Creates a white image with passport-style text fields and MRZ lines
    in a monospaced font. The image is designed to be readable by PaddleOCR.

    Args:
        output_path: Optional path to save the image. If None, only returns the array.

    Returns:
        The generated image as a BGR numpy array.
    """
    # Image dimensions (roughly passport-sized at 300 DPI proportions)
    width, height = 1200, 850
    image = np.ones((height, width, 3), dtype=np.uint8) * 255  # White background

    # Colors
    black = (0, 0, 0)
    dark_gray = (60, 60, 60)
    blue = (180, 60, 30)

    # --- Header ---
    cv2.putText(image, "PASSPORT", (400, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, blue, 3)
    cv2.putText(image, "UNITED KINGDOM OF GREAT BRITAIN", (250, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, dark_gray, 2)

    # --- VIZ Fields ---
    y_start = 180
    line_height = 45
    fields = [
        ("Surname / Nom", "SMITH"),
        ("Given Names / Prenoms", "JAMES EDWARD"),
        ("Nationality / Nationalite", "BRITISH"),
        ("Date of Birth / Date de naissance", "15 MAR 1985"),
        ("Sex / Sexe", "M"),
        ("Place of Birth / Lieu de naissance", "LONDON"),
        ("Date of Issue / Date de delivrance", "20 JUL 2019"),
        ("Date of Expiry / Date d'expiration", "20 JUL 2029"),
        ("Passport No. / No. de passeport", "AB1234567"),
    ]

    for i, (label, value) in enumerate(fields):
        y = y_start + i * line_height
        cv2.putText(image, label, (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, dark_gray, 1)
        cv2.putText(image, value, (50, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, black, 2)

    # --- Photo placeholder ---
    cv2.rectangle(image, (900, 160), (1130, 420), dark_gray, 2)
    cv2.putText(image, "PHOTO", (970, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.7, dark_gray, 2)

    # --- MRZ Zone (bottom of passport) ---
    # Draw MRZ background (slightly darker)
    cv2.rectangle(image, (0, 680), (width, height), (240, 240, 240), -1)

    # MRZ text — use a monospaced-like rendering
    # OpenCV doesn't have true monospace, so we space characters manually
    mrz_y1 = 740
    mrz_y2 = 790
    mrz_x_start = 30
    char_width = 25  # Approximate monospace width

    # Draw MRZ lines character by character for better OCR readability
    for i, ch in enumerate(TEST_MRZ_LINE_1):
        x = mrz_x_start + i * char_width
        cv2.putText(image, ch, (x, mrz_y1), cv2.FONT_HERSHEY_SIMPLEX, 0.75, black, 2)

    for i, ch in enumerate(TEST_MRZ_LINE_2):
        x = mrz_x_start + i * char_width
        cv2.putText(image, ch, (x, mrz_y2), cv2.FONT_HERSHEY_SIMPLEX, 0.75, black, 2)

    # Save if path provided
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), image)

    return image


# Default test image path
_TEST_DATA_DIR = Path(__file__).parent / "test_data"
DEFAULT_TEST_IMAGE = _TEST_DATA_DIR / "synthetic_passport.jpg"


def get_test_image_path() -> Path:
    """Get the path to the synthetic test passport image.

    Generates the image if it doesn't exist.
    """
    if not DEFAULT_TEST_IMAGE.exists():
        generate_synthetic_passport(DEFAULT_TEST_IMAGE)
    return DEFAULT_TEST_IMAGE


def get_test_image_bytes() -> bytes:
    """Get the synthetic test passport image as bytes."""
    path = get_test_image_path()
    return path.read_bytes()
