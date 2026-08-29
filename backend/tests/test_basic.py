"""
VeriGate Backend — Tests
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test that the health endpoint returns 200 OK and reports database connection."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database_connected"] is True


def test_list_reference_documents():
    """Test that the backend can read from the reference_documents table."""
    # This requires database connectivity to the actual Supabase instance
    from app.core.database import get_supabase_client
    from app.database import repositories

    db = get_supabase_client()
    docs = repositories.list_reference_documents(db, limit=5)
    
    assert isinstance(docs, list)
    assert len(docs) > 0  # We have 5 seed records
    assert "document_type" in docs[0]


def test_list_screening_sessions():
    """Test that the backend can read from the screening_sessions table."""
    from app.core.database import get_supabase_client
    from app.database import repositories

    db = get_supabase_client()
    sessions = repositories.list_screening_sessions(db, limit=5)
    
    assert isinstance(sessions, list)
    assert len(sessions) > 0  # We have 2 seed records
    assert "status" in sessions[0]
