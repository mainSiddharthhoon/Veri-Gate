"""
Create a tampered synthetic passport for testing the tampering detection engine.

This script takes the clean synthetic passport, splices a low-quality face
over the original face, and injects "Adobe Photoshop" into the EXIF data.
"""

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
import piexif

def create_tampered_image():
    base_dir = Path(__file__).parent.parent
    clean_path = base_dir / "tests" / "test_data" / "synthetic_passport.jpg"
    out_path = base_dir / "tests" / "test_data" / "synthetic_passport_tampered.jpg"
    
    if not clean_path.exists():
        print(f"Error: Could not find {clean_path}")
        return
        
    img = Image.open(clean_path)
    
    # 1. Splice a manipulated face
    # We'll just grab an arbitrary face-like region from the passport,
    # blur it, compress it badly, and paste it back slightly offset,
    # which will trigger the ELA face region and global variance checks.
    
    # Approximate face bounding box based on the synthetic passport
    face_box = (60, 200, 260, 450)
    face = img.crop(face_box)
    
    import numpy as np
    
    # Add severe high-frequency noise to completely blow out the ELA variance
    face_arr = np.array(face)
    noise = np.random.normal(0, 50, face_arr.shape).astype(np.float32)
    face_arr = np.clip(face_arr + noise, 0, 255).astype(np.uint8)
    face = Image.fromarray(face_arr)
    
    # Compress it badly to create an ELA discrepancy
    buffer = io.BytesIO()
    face.save(buffer, format="JPEG", quality=30)
    buffer.seek(0)
    face_tampered = Image.open(buffer)
    
    # Paste it back
    img.paste(face_tampered, face_box)
    
    # 2. Inject EXIF metadata
    # 305 is the EXIF tag for Software
    exif_dict = {"0th": {piexif.ImageIFD.Software: "Adobe Photoshop CS6 (Windows)"}}
    exif_bytes = piexif.dump(exif_dict)
    
    # 3. Save
    img.save(out_path, format="JPEG", quality=95, exif=exif_bytes)
    print(f"Created tampered passport at {out_path}")


if __name__ == "__main__":
    create_tampered_image()
