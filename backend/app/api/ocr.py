"""
VeriGate Backend — OCR API

Endpoint for extracting text, MRZ data, and structured passport fields
from an uploaded document image.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from supabase import Client

from app.core.database import get_db
from app.schemas.ocr import (
    OcrExtractResponse,
    OcrBlockResponse,
    MrzDataResponse,
    MrzCheckResultResponse,
    ExtractedFieldsResponse,
    ProcessingInfoResponse,
)
from app.services.ocr_pipeline import run_ocr_pipeline
from app.services.ai_reasoning import qualify_inputs

router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.post("/extract", response_model=OcrExtractResponse)
async def extract_document(
    file: UploadFile = File(..., description="Document image (JPEG, PNG)"),
    live_image: UploadFile = File(..., description="Presented person face image"),
    document_type: str = Form("passport", description="Document type"),
    db: Client = Depends(get_db),
) -> OcrExtractResponse:
    """Extract text, MRZ, and structured fields from a document image.

    Accepts a passport image upload, runs OCR + MRZ parsing, extracts
    structured passport fields, and persists the results to the database.

    Returns the complete extraction result including raw OCR text,
    individual text blocks, MRZ data with check-digit validation,
    and extracted passport fields.
    """
    # Validate file type
    if file.content_type and file.content_type not in (
        "image/jpeg", "image/png", "image/jpg", "image/webp", "image/tiff",
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported document file type: {file.content_type}.",
        )

    # Read uploaded files
    image_bytes = await file.read()
    live_bytes = await live_image.read()
    
    if len(image_bytes) == 0 or len(live_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    # AI Input Qualification (Combined)
    qualification = qualify_inputs(image_bytes, live_bytes)
    if not qualification.input_valid:
        raise HTTPException(status_code=400, detail="Please provide a valid identity document and a clear photo of the person.")

    # Run the OCR pipeline
    pipeline_result = run_ocr_pipeline(
        image_bytes=image_bytes,
        db=db,
        document_type=document_type,
    )

    if pipeline_result.session_id:
        import os
        from app.database.repositories import update_screening_session
        os.makedirs("uploads", exist_ok=True)
        doc_path = f"uploads/{pipeline_result.session_id}_doc.jpg"
        with open(doc_path, "wb") as f:
            f.write(image_bytes)
        try:
            update_screening_session(db, pipeline_result.session_id, {"document_image_path": doc_path})
        except Exception as e:
            pass

    # Build response
    ocr_blocks = [
        OcrBlockResponse(
            text=b["text"],
            confidence=b["confidence"],
            bounding_box=b["bounding_box"],
        )
        for b in pipeline_result.ocr_blocks
    ]

    mrz = MrzDataResponse(
        detected=pipeline_result.mrz_detected,
        line_1=pipeline_result.mrz_line_1,
        line_2=pipeline_result.mrz_line_2,
        parsed=pipeline_result.mrz_parsed,
        check_results=[
            MrzCheckResultResponse(**c) for c in pipeline_result.mrz_check_results
        ],
        all_checks_valid=pipeline_result.mrz_all_valid,
    )

    extracted_fields = None
    if pipeline_result.document_fields:
        df = pipeline_result.document_fields
        extracted_fields = ExtractedFieldsResponse(
            document_type=df.get("document_type", "passport"),
            document_number=df.get("document_number"),
            issuing_country=df.get("issuing_country"),
            nationality=df.get("nationality"),
            surname=df.get("surname"),
            given_names=df.get("given_names"),
            date_of_birth=df.get("date_of_birth"),
            sex=df.get("sex"),
            date_of_issue=df.get("date_of_issue"),
            date_of_expiry=df.get("date_of_expiry"),
        )

    processing = ProcessingInfoResponse(
        session_id=pipeline_result.session_id,
        ocr_processing_time_ms=pipeline_result.ocr_processing_time_ms,
        total_processing_time_ms=pipeline_result.total_processing_time_ms,
        ocr_confidence=pipeline_result.ocr_confidence,
        errors=pipeline_result.errors,
    )

    return OcrExtractResponse(
        raw_text=pipeline_result.raw_text,
        ocr_blocks=ocr_blocks,
        extracted_fields=extracted_fields,
        mrz=mrz,
        processing=processing,
    )
