"""
VeriGate Backend — Screening Schemas

Pydantic models for screening request/response payloads.
These define the API contract for the future screening workflow.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DocumentType(str, Enum):
    PASSPORT = "passport"
    VISA = "visa"
    NATIONAL_ID = "national_id"
    DRIVING_LICENSE = "driving_license"
    PERMIT = "permit"


class SessionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Decision(str, Enum):
    APPROVE = "approve"
    REVIEW = "review"
    REJECT = "reject"


class CheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ScreeningCreateRequest(BaseModel):
    """Request to create a new screening session.

    In the full implementation, document_image and person_image will be
    file uploads. For now, this schema accepts storage paths as strings.
    """

    document_type: DocumentType = DocumentType.PASSPORT
    operator_id: Optional[str] = None
    operator_notes: Optional[str] = None
    # Placeholder — will become UploadFile in the real implementation
    document_image_path: str = Field(..., description="Path to the uploaded document image")
    person_image_path: str = Field(..., description="Path to the uploaded person/selfie image")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class DocumentFields(BaseModel):
    """Extracted document fields."""

    document_type: DocumentType
    document_number: Optional[str] = None
    issuing_country: Optional[str] = None
    nationality: Optional[str] = None
    surname: Optional[str] = None
    given_names: Optional[str] = None
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None
    date_of_issue: Optional[date] = None
    date_of_expiry: Optional[date] = None
    mrz_line_1: Optional[str] = None
    mrz_line_2: Optional[str] = None


class ValidationCheckResult(BaseModel):
    """A single validation check result."""

    check_name: str
    check_category: str
    status: CheckStatus
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    message: Optional[str] = None


class ValidationSummary(BaseModel):
    """Validation results summary."""

    is_valid: bool
    checks_passed: int = 0
    checks_failed: int = 0
    checks_warned: int = 0
    checks: list[ValidationCheckResult] = []


class TamperingSignalResult(BaseModel):
    """A single tampering evidence signal."""

    signal_type: str
    signal_name: str
    score: float
    is_suspicious: bool
    message: Optional[str] = None


class TamperingSummary(BaseModel):
    """Tampering analysis summary."""

    tamper_score: float
    is_suspicious: bool
    signals: list[TamperingSignalResult] = []


class FaceVerificationResult(BaseModel):
    """Face verification result."""

    model_name: str
    distance: Optional[float] = None
    distance_metric: Optional[str] = None
    threshold: Optional[float] = None
    is_match: bool
    error_message: Optional[str] = None


class RiskFactorResult(BaseModel):
    """A single risk factor contributing to the score."""

    factor_source: str
    factor_name: str
    weight: float
    score_contribution: float
    severity: str
    message: Optional[str] = None


class RiskAssessmentResult(BaseModel):
    """Final risk assessment."""

    risk_score: float
    risk_level: RiskLevel
    decision: Decision
    summary: Optional[str] = None
    factors: list[RiskFactorResult] = []


class ScreeningResponse(BaseModel):
    """Complete screening session response."""

    id: str
    status: SessionStatus
    document_type: DocumentType
    created_at: datetime
    completed_at: Optional[datetime] = None

    # Analysis results (populated as the pipeline completes)
    document: Optional[DocumentFields] = None
    validation: Optional[ValidationSummary] = None
    tampering: Optional[TamperingSummary] = None
    face_verification: Optional[FaceVerificationResult] = None
    risk_assessment: Optional[RiskAssessmentResult] = None


class ScreeningListItem(BaseModel):
    """Summary item for listing screening sessions."""

    id: str
    status: SessionStatus
    document_type: DocumentType
    created_at: datetime
    completed_at: Optional[datetime] = None
    risk_score: Optional[float] = None
    risk_level: Optional[RiskLevel] = None
    decision: Optional[Decision] = None
