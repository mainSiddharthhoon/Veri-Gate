"""
VeriGate Backend — Validation API Integration Tests

Tests for the validation API endpoints.
These tests require a running Supabase database connection.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# The seeded completed session ID from 002_seed_data.sql
SEEDED_SESSION_ID = "b0000001-0000-4000-8000-000000000001"
NONEXISTENT_SESSION_ID = "00000000-0000-0000-0000-000000000000"


class TestValidationRunEndpoint:
    def test_run_validation_on_seeded_session(self):
        """Running validation on the seeded session should succeed."""
        response = client.post(f"/api/validation/run/{SEEDED_SESSION_ID}")
        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == SEEDED_SESSION_ID
        assert "is_valid" in data
        assert "checks_passed" in data
        assert "checks_failed" in data
        assert "checks_warned" in data
        assert isinstance(data["checks"], list)
        assert len(data["checks"]) > 0

    def test_run_validation_structured_checks(self):
        """Each check should have the required fields."""
        response = client.post(f"/api/validation/run/{SEEDED_SESSION_ID}")
        assert response.status_code == 200
        data = response.json()

        for check in data["checks"]:
            assert "check_name" in check
            assert "check_category" in check
            assert "status" in check
            assert check["status"] in ("passed", "failed", "warning", "skipped")
            assert "message" in check

    def test_run_validation_nonexistent_session(self):
        """Should return 404 for a nonexistent session."""
        response = client.post(f"/api/validation/run/{NONEXISTENT_SESSION_ID}")
        assert response.status_code == 404

    def test_run_validation_has_all_categories(self):
        """The response should include checks from all 5 categories."""
        response = client.post(f"/api/validation/run/{SEEDED_SESSION_ID}")
        assert response.status_code == 200
        data = response.json()

        categories = {c["check_category"] for c in data["checks"]}
        expected_categories = {"fields", "format", "dates", "mrz", "database"}
        assert categories == expected_categories


class TestValidationGetEndpoint:
    def test_get_validation_for_seeded_session(self):
        """Should retrieve existing validation results for the seeded session."""
        # The seeded session already has validation_results from 002_seed_data.sql
        response = client.get(f"/api/validation/{SEEDED_SESSION_ID}")
        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == SEEDED_SESSION_ID
        assert "is_valid" in data
        assert isinstance(data["checks"], list)

    def test_get_validation_nonexistent(self):
        """Should return 404 for a session with no validation results."""
        response = client.get(f"/api/validation/{NONEXISTENT_SESSION_ID}")
        assert response.status_code == 404
