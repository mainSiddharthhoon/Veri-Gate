from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from supabase import Client

from app.core.database import get_db
from app.schemas.face import FaceVerificationResponse
from app.services.face_core import verify_faces
from app.database.repositories import create_face_verification

router = APIRouter(prefix="/face", tags=["face"])
logger = logging.getLogger(__name__)

@router.post("/verify", response_model=FaceVerificationResponse)
async def verify_face_endpoint(
    document_image: UploadFile = File(...),
    live_image: UploadFile = File(...),
    session_id: Optional[UUID] = Form(None),
    db: Client = Depends(get_db)
):
    """
    Compare the face extracted from the document with the live presented face.
    """
    doc_bytes = await document_image.read()
    live_bytes = await live_image.read()
    
    if not doc_bytes or not live_bytes:
        raise HTTPException(status_code=400, detail="Both document and live images are required.")
    
    # Run verification (this is synchronous/blocking, so in production we might use a threadpool)
    result_dict = verify_faces(doc_bytes, live_bytes, crop_document=True)
    
    if session_id:
        result_dict["session_id"] = str(session_id)
        
        import os
        from app.database.repositories import update_screening_session
        os.makedirs("uploads", exist_ok=True)
        face_path = f"uploads/{session_id}_face.jpg"
        with open(face_path, "wb") as f:
            f.write(live_bytes)
        try:
            update_screening_session(db, str(session_id), {"person_image_path": face_path})
        except Exception as e:
            pass

        try:
            # Store the result in the database
            create_face_verification(db, result_dict)
        except Exception as e:
            logger.error(f"Failed to save face verification result: {e}")
            # We don't fail the request just because DB insertion failed, but log it
            
    return FaceVerificationResponse(**result_dict)
