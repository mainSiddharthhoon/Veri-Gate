from __future__ import annotations

from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class FaceVerificationResponse(BaseModel):
    session_id: Optional[UUID] = None
    is_match: bool
    distance: Optional[float] = None
    threshold: Optional[float] = None
    model_name: str
    distance_metric: Optional[str] = None
    error_message: Optional[str] = None
    processing_time_ms: int
