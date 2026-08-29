"""
VeriGate Backend — OCR Schemas

Pydantic models for the OCR extraction API request/response.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Response sub-models
# ---------------------------------------------------------------------------

class OcrBlockResponse(BaseModel):
    """A single OCR text detection."""
    text: str
    confidence: float
    bounding_box: list[list[float]]


class MrzCheckResultResponse(BaseModel):
    """Result of a single MRZ check-digit validation."""
    field_name: str
    expected: int
    computed: int
    is_valid: bool


class MrzDataResponse(BaseModel):
    """Parsed MRZ data."""
    line_1: Optional[str] = None
    line_2: Optional[str] = None
    detected: bool = False
    parsed: Optional[dict] = None
    check_results: list[MrzCheckResultResponse] = []
    all_checks_valid: bool = False


class ExtractedFieldsResponse(BaseModel):
    """Extracted document fields."""
    document_type: str = "passport"
    document_number: Optional[str] = None
    issuing_country: Optional[str] = None
    nationality: Optional[str] = None
    surname: Optional[str] = None
    given_names: Optional[str] = None
    date_of_birth: Optional[str] = None
    sex: Optional[str] = None
    date_of_issue: Optional[str] = None
    date_of_expiry: Optional[str] = None


class ProcessingInfoResponse(BaseModel):
    """Processing metadata."""
    session_id: Optional[str] = None
    ocr_processing_time_ms: int = 0
    total_processing_time_ms: int = 0
    ocr_confidence: float = 0.0
    errors: list[str] = []


# ---------------------------------------------------------------------------
# Main response
# ---------------------------------------------------------------------------

class OcrExtractResponse(BaseModel):
    """Complete response from the OCR extraction endpoint."""
    raw_text: str = ""
    ocr_blocks: list[OcrBlockResponse] = []
    extracted_fields: Optional[ExtractedFieldsResponse] = None
    mrz: MrzDataResponse = Field(default_factory=MrzDataResponse)
    processing: ProcessingInfoResponse = Field(default_factory=ProcessingInfoResponse)
