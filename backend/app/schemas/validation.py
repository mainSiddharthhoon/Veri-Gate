"""
VeriGate Backend — Validation Schemas

Pydantic models for the validation API request/response.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ValidationCheckResponse(BaseModel):
    """A single validation check result."""
    check_name: str
    check_category: str
    status: str
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    message: str


class ValidationResponse(BaseModel):
    """Complete response from the validation endpoint."""
    session_id: str
    is_valid: bool
    checks_passed: int = 0
    checks_failed: int = 0
    checks_warned: int = 0
    checks_skipped: int = 0
    checks: list[ValidationCheckResponse] = []
    processing_time_ms: int = 0
