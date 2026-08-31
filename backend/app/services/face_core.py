from __future__ import annotations

import io
import time
import logging
from typing import Dict, Any, Tuple

import cv2
import numpy as np
from PIL import Image
logger = logging.getLogger(__name__)

# Note: Using opencv backend since it's lightweight and we already have cv2.
# Models like retinaface are more robust but require more dependencies.
DETECTOR_BACKEND = "opencv"
DEFAULT_MODEL = "Facenet512"

def _load_image_from_bytes(image_bytes: bytes, crop_face: bool = False) -> np.ndarray:
    """Load image bytes into an RGB numpy array for DeepFace."""
    image = Image.open(io.BytesIO(image_bytes))
    image = image.convert("RGB")
    # Convert to BGR format for cv2 / deepface
    img_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    if crop_face:
        # For the hackathon synthetic passport, use a known photo region.
        # A more robust system would use a lightweight face detector (like RetinaFace or Haar Cascades)
        # to find the document photo bounding box dynamically before passing to DeepFace.
        h, w = img_bgr.shape[:2]
        if h >= 330 and w >= 240:
            img_bgr = img_bgr[80:330, 40:240]
            
    return img_bgr

def verify_faces(doc_img_bytes: bytes, live_img_bytes: bytes, model_name: str = DEFAULT_MODEL, crop_document: bool = False) -> Dict[str, Any]:
    """
    Compare document face with live face using DeepFace.
    Returns structured dict ready to match FaceVerificationResponse.
    """
    start_time = time.perf_counter()
    
    result = {
        "is_match": False,
        "distance": None,
        "threshold": None,
        "model_name": model_name,
        "distance_metric": "cosine",  # DeepFace defaults to cosine for Facenet
        "error_message": None,
        "processing_time_ms": 0,
    }

    try:
        from deepface import DeepFace

        doc_img = _load_image_from_bytes(doc_img_bytes, crop_face=crop_document)
        live_img = _load_image_from_bytes(live_img_bytes, crop_face=False)
        
        # enforce_detection=True throws ValueError if it can't find a face
        df_result = DeepFace.verify(
            img1_path=doc_img,
            img2_path=live_img,
            model_name=model_name,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=True,
            align=True,
        )
        
        result["is_match"] = bool(df_result.get("verified", False))
        result["distance"] = float(df_result.get("distance", 0.0))
        result["threshold"] = float(df_result.get("threshold", 0.0))
        
        # Optional: check if DeepFace returned a different metric
        if "distance_metric" in df_result:
            result["distance_metric"] = df_result["distance_metric"]

    except ValueError as e:
        # DeepFace raises ValueError when it cannot detect a face
        logger.warning(f"Face verification failed: {e}")
        result["error_message"] = str(e)
    except Exception as e:
        logger.error(f"Unexpected error during face verification: {e}")
        result["error_message"] = f"Internal error: {e}"
        
    result["processing_time_ms"] = int((time.perf_counter() - start_time) * 1000)
    return result
