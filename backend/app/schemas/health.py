"""
VeriGate Backend — Health Schemas
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response for the health check endpoint."""

    status: str = "ok"
    app_name: str
    version: str
    database_connected: bool
