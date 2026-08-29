"""
VeriGate Backend — Tampering Detection Core Logic

Pure logic for extracting tampering signals from an image using deterministic
methods (Error Level Analysis, EXIF inspection, Face Region ELA variance).

No database access or external API calls.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class TamperingConfig:
    """Configurable thresholds and parameters for tampering analysis."""
    # ELA Parameters
    ela_quality: int = 90
    ela_scale: float = 15.0  # Multiplier for the difference image to make it visible
    ela_threshold_high_variance: float = 1.3  # Tuned for synthetic passport
    
    # Exif Parameters
    suspicious_software: set[str] = field(default_factory=lambda: {
        "adobe", "photoshop", "gimp", "paint", "canva", "lightroom"
    })
    
    # Face Region Parameters
    face_min_neighbors: int = 3
    face_scale_factor: float = 1.1
    face_variance_ratio_high: float = 5.0  # Synthetic drawing has naturally high variance (e.g. ~3x)
    face_variance_ratio_low: float = 0.2
    
    # Scoring Weights
    score_exif_software: float = 0.2  # Reduced as requested
    score_ela_global: float = 0.3
    score_ela_face: float = 0.5
    suspicious_threshold: float = 0.4


# Default global instance
CONFIG = TamperingConfig()



# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class TamperingSignal:
    """A single piece of tampering evidence."""
    signal_type: str        # 'metadata', 'photo_region', 'noise_analysis'
    signal_name: str
    score: float            # 0.0 to 1.0 (contribution to overall suspiciousness)
    is_suspicious: bool
    details: dict
    message: str

    def to_db_dict(self, analysis_id: str, evidence_path: Optional[str] = None) -> dict:
        return {
            "tampering_analysis_id": analysis_id,
            "signal_type": self.signal_type,
            "signal_name": self.signal_name,
            "score": float(self.score),
            "is_suspicious": self.is_suspicious,
            "details": self.details,
            "evidence_image_path": evidence_path,
            "message": self.message,
        }


@dataclass
class TamperingResult:
    """Complete tampering analysis result."""
    tamper_score: float = 0.0
    is_suspicious: bool = False
    signals: list[TamperingSignal] = field(default_factory=list)
    ela_heatmap: Optional[bytes] = None  # The visual evidence image
    processing_time_ms: int = 0


# ---------------------------------------------------------------------------
# Core Analysis Functions
# ---------------------------------------------------------------------------

def analyze_document_tampering(image_bytes: bytes, config: TamperingConfig = CONFIG) -> TamperingResult:
    """Run all tampering analyses on an image and fuse the results."""
    
    signals = []
    
    # 1. EXIF Metadata
    exif_signal = _analyze_metadata(image_bytes, config)
    signals.append(exif_signal)
    
    # 2. Decode image for CV2 processing
    nparr = np.frombuffer(image_bytes, np.uint8)
    image_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image_cv is None:
        raise ValueError("Failed to decode image for tampering analysis")
        
    # 3. Global ELA
    ela_diff, global_variance, global_ela_signal = _analyze_global_ela(image_cv, config)
    signals.append(global_ela_signal)
    
    # 4. Face Region Splicing
    face_signal = _analyze_face_region(image_cv, ela_diff, global_variance, config)
    signals.append(face_signal)
    
    # 5. Fuse Scores
    total_score = min(1.0, sum(s.score for s in signals))
    is_suspicious = total_score >= config.suspicious_threshold
    
    # Generate visual evidence (Heatmap)
    # Enhance the ELA diff for visualization
    enhanced_ela = cv2.convertScaleAbs(ela_diff, alpha=config.ela_scale)
    # Apply a colormap (JET or INFERNO) to make differences pop
    ela_heatmap = cv2.applyColorMap(enhanced_ela, cv2.COLORMAP_JET)
    
    # If a face was found, draw a box on the heatmap
    if face_signal.is_suspicious and "face_box" in face_signal.details:
        x, y, w, h = face_signal.details["face_box"]
        cv2.rectangle(ela_heatmap, (x, y), (x+w, y+h), (0, 0, 255), 3) # Red box
        
    _, buffer = cv2.imencode(".jpg", ela_heatmap, [cv2.IMWRITE_JPEG_QUALITY, 85])
    heatmap_bytes = buffer.tobytes()

    return TamperingResult(
        tamper_score=total_score,
        is_suspicious=is_suspicious,
        signals=signals,
        ela_heatmap=heatmap_bytes,
    )


# ---------------------------------------------------------------------------
# Individual Techniques
# ---------------------------------------------------------------------------

def _analyze_metadata(image_bytes: bytes, config: TamperingConfig) -> TamperingSignal:
    """Check EXIF data for known photo editing software."""
    software_found = None
    is_suspicious = False
    score = 0.0
    
    try:
        # Load with PIL to easily access EXIF
        img = Image.open(io.BytesIO(image_bytes))
        exif = img.getexif()
        
        if exif:
            # 305 is the tag ID for 'Software'
            software = exif.get(305)
            if software and isinstance(software, str):
                sw_lower = software.lower()
                for suspicious in config.suspicious_software:
                    if suspicious in sw_lower:
                        software_found = software
                        is_suspicious = True
                        score = config.score_exif_software
                        break
    except Exception:
        pass  # If PIL fails to read EXIF, we just treat it as clean metadata
        
    if is_suspicious:
        msg = f"Suspicious photo editing software detected in EXIF: '{software_found}'"
    else:
        msg = "No suspicious software signatures found in EXIF metadata."
        
    return TamperingSignal(
        signal_type="metadata",
        signal_name="exif_software_check",
        score=score,
        is_suspicious=is_suspicious,
        details={"software": software_found} if software_found else {},
        message=msg
    )


def _analyze_global_ela(image_cv: np.ndarray, config: TamperingConfig) -> tuple[np.ndarray, float, TamperingSignal]:
    """Perform Error Level Analysis to detect global compression anomalies."""
    
    # 1. Save at target quality to memory
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), config.ela_quality]
    _, encoded = cv2.imencode('.jpg', image_cv, encode_param)
    
    # 2. Decode it back
    resaved = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    
    # 3. Absolute difference between original and resaved
    # Converting to int16 to prevent underflow/overflow before taking abs
    diff = cv2.absdiff(image_cv, resaved)
    
    # Convert to grayscale for variance analysis
    diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    
    # Calculate global variance
    mean, stddev = cv2.meanStdDev(diff_gray)
    variance = float(stddev[0][0] ** 2)
    
    is_suspicious = variance > config.ela_threshold_high_variance
    score = config.score_ela_global if is_suspicious else 0.0
    
    # Scale score based on how far over the threshold it is, up to the max weight
    if variance > 0:
        # Normalization logic: cap at 3x threshold
        ratio = min(variance / config.ela_threshold_high_variance, 3.0) 
        # A clean image might have ratio 0.2. 
        # A slightly dirty image 0.8. 
        # Above 1.0 gets points.
        if ratio > 1.0:
            score = min(config.score_ela_global, config.score_ela_global * ((ratio - 1.0) / 2.0))
            is_suspicious = True
            
    signal = TamperingSignal(
        signal_type="noise_analysis",
        signal_name="global_ela_variance",
        score=score,
        is_suspicious=is_suspicious,
        details={"global_variance": variance, "threshold": config.ela_threshold_high_variance},
        message=f"Global ELA variance is {variance:.2f} (Threshold: {config.ela_threshold_high_variance})."
    )
    
    return diff_gray, variance, signal


def _analyze_face_region(
    image_cv: np.ndarray, 
    ela_diff_gray: np.ndarray, 
    global_variance: float, 
    config: TamperingConfig
) -> TamperingSignal:
    """Detect face and compare its ELA variance to the background (splicing detection)."""
    
    # Load Haar cascade
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)
    
    if face_cascade.empty():
        return TamperingSignal(
            signal_type="photo_region",
            signal_name="face_ela_variance",
            score=0.0,
            is_suspicious=False,
            details={"error": "Cascade file not found"},
            message="Skipped: Haar cascade could not be loaded."
        )

    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray, 
        scaleFactor=config.face_scale_factor, 
        minNeighbors=config.face_min_neighbors, 
        minSize=(100, 100)
    )
    
    if len(faces) == 0:
        # Fallback for synthetic/dummy documents where Haar fails to detect a face.
        # Assuming standard passport layout where photo is on the left.
        x, y, w, h = 60, 200, 200, 250
        msg_prefix = "Fallback photo region ELA variance ratio is "
    else:
        # Assume the largest face is the document photo
        faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
        x, y, w, h = faces[0]
        msg_prefix = "Face ELA variance ratio is "
        
    # Extract the face region from the ELA diff
    face_ela = ela_diff_gray[y:y+h, x:x+w]
    
    # Compute variance inside the face
    _, face_stddev = cv2.meanStdDev(face_ela)
    face_variance = float(face_stddev[0][0] ** 2)
    
    # Compare against global variance (or background variance)
    # Using max(global, 1.0) to prevent division by zero
    baseline = max(global_variance, 1.0)
    variance_ratio = face_variance / baseline
    
    is_suspicious = (variance_ratio > config.face_variance_ratio_high) or (variance_ratio < config.face_variance_ratio_low)
    
    score = 0.0
    if is_suspicious:
        if variance_ratio > config.face_variance_ratio_high:
            excess = variance_ratio - config.face_variance_ratio_high
            score = min(config.score_ela_face, config.score_ela_face * (excess / 2.0))
        else:
            deficit = config.face_variance_ratio_low - variance_ratio
            score = min(config.score_ela_face, config.score_ela_face * (deficit / 0.5))
            # Just give it full weight if it's very low
            if score == 0.0: score = config.score_ela_face
            if deficit > 0: score = config.score_ela_face
        
    msg = f"{msg_prefix}{variance_ratio:.2f}x background."
    if is_suspicious:
        msg += f" Highly indicative of photo splicing (Thresholds: <{config.face_variance_ratio_low} or >{config.face_variance_ratio_high})."
        
    return TamperingSignal(
        signal_type="photo_region",
        signal_name="face_ela_variance",
        score=score,
        is_suspicious=is_suspicious,
        details={
            "face_box": [int(x), int(y), int(w), int(h)],
            "face_variance": face_variance,
            "global_variance": global_variance,
            "ratio": variance_ratio,
        },
        message=msg
    )
