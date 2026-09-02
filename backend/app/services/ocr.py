"""
VeriGate Backend — OCR Service

Wraps PaddleOCR for text extraction from document images.
The OCR engine is lazy-loaded as a singleton to avoid re-initialization overhead.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes for OCR results
# ---------------------------------------------------------------------------

@dataclass
class OcrBlock:
    """A single OCR text detection with bounding box and confidence."""
    text: str
    confidence: float
    bounding_box: list[list[float]]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]


@dataclass
class OcrRawResult:
    """Complete OCR result from a single image."""
    blocks: list[OcrBlock] = field(default_factory=list)
    raw_text: str = ""
    average_confidence: float = 0.0
    processing_time_ms: int = 0


# ---------------------------------------------------------------------------
# OCR Engine — lazy singleton
# ---------------------------------------------------------------------------

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

_ocr_engine = None

def _get_ocr_engine():
    """Get or create the PaddleOCR engine (singleton)."""
    global _ocr_engine
    if _ocr_engine is None:
        if PaddleOCR is None:
            raise ImportError("paddleocr is not installed.")
        logger.info("Initializing PaddleOCR engine (first use)...")
        _ocr_engine = PaddleOCR(
            use_angle_cls=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            enable_mkldnn=False,
            lang="en",           # English for passport documents
        )
        logger.info("PaddleOCR engine initialized.")
        logger.info("PaddleOCR engine initialized.")
    return _ocr_engine


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_ocr(image: np.ndarray) -> OcrRawResult:
    """Run PaddleOCR on an image and return structured results.

    Args:
        image: Image as a numpy array (BGR or grayscale).

    Returns:
        OcrRawResult containing all detected text blocks with
        bounding boxes, confidence scores, and aggregated text.
    """
    import cv2
    
    # Downscale image to prevent OpenCV OutOfMemoryError on constrained systems
    h, w = image.shape[:2]
    max_dim = 1024
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        image = cv2.resize(image, (int(w * scale), int(h * scale)))

    engine = _get_ocr_engine()

    start = time.time()
    raw_results = engine.ocr(image)
    elapsed_ms = int((time.time() - start) * 1000)

    blocks = []
    all_text_parts = []
    total_confidence = 0.0

    if raw_results and raw_results[0]:
        first_page = raw_results[0]
        if isinstance(first_page, dict):
            # PaddleOCR 3.7+ format
            texts = first_page.get('rec_texts', [])
            scores = first_page.get('rec_scores', [])
            polys = first_page.get('rec_polys', [])
            for i in range(len(texts)):
                blocks.append(OcrBlock(
                    text=texts[i],
                    confidence=round(scores[i], 4),
                    bounding_box=polys[i].tolist() if hasattr(polys[i], "tolist") else polys[i],
                ))
                all_text_parts.append(texts[i])
                total_confidence += scores[i]
        else:
            # PaddleOCR 2.x format
            for detection in first_page:
                bbox = detection[0]
                text = detection[1][0]
                confidence = detection[1][1]
    
                blocks.append(OcrBlock(
                    text=text,
                    confidence=round(confidence, 4),
                    bounding_box=bbox,
                ))
                all_text_parts.append(text)
                total_confidence += confidence

    avg_conf = (total_confidence / len(blocks)) if blocks else 0.0

    return OcrRawResult(
        blocks=blocks,
        raw_text="\n".join(all_text_parts),
        average_confidence=round(avg_conf, 4),
        processing_time_ms=elapsed_ms,
    )


def extract_raw_text(ocr_result: OcrRawResult) -> str:
    """Get the concatenated raw text from an OCR result.

    Args:
        ocr_result: OCR result to extract text from.

    Returns:
        All detected text joined with newlines.
    """
    return ocr_result.raw_text
