"""
VeriGate Backend — Tampering Service Unit Tests
"""

from pathlib import Path
import pytest
from app.services.tampering_core import analyze_document_tampering, CONFIG


def get_image_bytes(filename: str) -> bytes:
    path = Path(__file__).parent / "test_data" / filename
    return path.read_bytes()


def test_clean_synthetic_passport():
    """A clean passport should have a low tamper score and is_suspicious=False."""
    image_bytes = get_image_bytes("synthetic_passport.jpg")
    
    result = analyze_document_tampering(image_bytes)
    
    # We do not expect exactly 0.0 because compression can cause some variance,
    # but it should be below the suspicious threshold.
    assert result.is_suspicious is False
    assert result.tamper_score < CONFIG.suspicious_threshold
    
    # Check that signals look clean
    exif_signal = next(s for s in result.signals if s.signal_name == "exif_software_check")
    assert exif_signal.is_suspicious is False
    
    ela_global_signal = next(s for s in result.signals if s.signal_name == "global_ela_variance")
    assert ela_global_signal.is_suspicious is False

    face_signal = next(s for s in result.signals if s.signal_name == "face_ela_variance")
    assert face_signal.is_suspicious is False


def test_tampered_synthetic_passport():
    """A tampered passport with spliced face and EXIF manipulation should be flagged."""
    image_bytes = get_image_bytes("synthetic_passport_tampered.jpg")
    
    result = analyze_document_tampering(image_bytes)
    
    # We verify the score is meaningfully higher than 0.0
    assert result.tamper_score > 0.1
    
    # We expect EXIF to flag Adobe Photoshop
    exif_signal = next(s for s in result.signals if s.signal_name == "exif_software_check")
    assert exif_signal.is_suspicious is True
    assert exif_signal.score == CONFIG.score_exif_software
    assert "photoshop" in str(exif_signal.details.get("software", "")).lower()

    # The heavily blurred and re-compressed face should trigger either global or local ELA variance
    ela_global_signal = next(s for s in result.signals if s.signal_name == "global_ela_variance")
    face_signal = next(s for s in result.signals if s.signal_name == "face_ela_variance")
    
    # At least one of the ELA checks must catch the splice
    assert (ela_global_signal.is_suspicious or face_signal.is_suspicious) is True

    # Check evidence image is generated
    assert result.ela_heatmap is not None
    assert len(result.ela_heatmap) > 0
