"""
VeriGate Backend — API Router

Aggregates all API route modules under /api.
"""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.screening import router as screening_router
from app.api.ocr import router as ocr_router
from app.api.validation import router as validation_router
from app.api.tampering import router as tampering_router
from app.api.face import router as face_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(screening_router)
api_router.include_router(ocr_router)
api_router.include_router(validation_router)
api_router.include_router(tampering_router)
api_router.include_router(face_router)

