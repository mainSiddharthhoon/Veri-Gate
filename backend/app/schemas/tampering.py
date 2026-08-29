"""
VeriGate Backend — Tampering Schemas

Pydantic models for the tampering analysis API.
"""

from typing import Optional

from pydantic import BaseModel


class TamperingSignalResponse(BaseModel):
    """A single piece of tampering evidence."""
    signal_type: str
    signal_name: str
    score: float
    is_suspicious: bool
    details: dict
    evidence_image_path: Optional[str] = None
    message: str


class TamperingResponse(BaseModel):
    """Complete response from the tampering endpoint."""
    session_id: str
    tamper_score: float
    is_suspicious: bool
    signals: list[TamperingSignalResponse] = []
    processing_time_ms: int = 0
