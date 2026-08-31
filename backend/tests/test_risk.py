import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch
from app.services.risk_scoring import assess_session_risk, RiskConfig, determine_level_and_decision
from app.database import repositories as repo

def test_determine_level_and_decision():
    config = RiskConfig()
    
    level, dec = determine_level_and_decision(0, config)
    assert level == "low"
    assert dec == "approve"
    
    level, dec = determine_level_and_decision(25, config)
    assert level == "medium"
    assert dec == "review"
    
    level, dec = determine_level_and_decision(60, config)
    assert level == "high"
    assert dec == "review"
    
    level, dec = determine_level_and_decision(85, config)
    assert level == "critical"
    assert dec == "reject"

@patch("app.services.risk_scoring.create_risk_assessment")
@patch("app.services.risk_scoring.create_risk_factors")
def test_assess_session_risk_clean(mock_create_factors, mock_create_assessment):
    mock_create_assessment.return_value = {"id": "mock_id"}
    mock_create_factors.return_value = []
    
    mock_db = MagicMock()
    # No validation failures
    val_res = MagicMock(data={"id": "v1"})
    checks_res = MagicMock(data=[
        {"check_name": "expiry_not_past", "category": "date", "status": "passed"}
    ])
    mock_db.table().select().eq().maybe_single().execute.return_value = val_res
    mock_db.table().select().eq().execute.return_value = checks_res
    
    res = assess_session_risk(str(uuid4()), mock_db)
    
    assert res["assessment"]["id"] == "mock_id"
    assert len(res["factors"]) == 0

@patch("app.services.risk_scoring.create_risk_assessment")
@patch("app.services.risk_scoring.create_risk_factors")
def test_assess_session_risk_face_mismatch(mock_create_factors, mock_create_assessment):
    mock_create_assessment.return_value = {"id": "mock_id"}
    mock_create_factors.return_value = [{"factor_name": "face_mismatch"}]
    
    mock_db = MagicMock()
    val_res = MagicMock(data={"id": "v1"})
    tamp_res = MagicMock(data=None)
    face_res = MagicMock(data={"is_match": False})

    mock_db.table().select().eq().maybe_single().execute.side_effect = [
        val_res,
        tamp_res,
        face_res
    ]
    mock_db.table().select().eq().execute.return_value = MagicMock(data=[])
    
    res = assess_session_risk(str(uuid4()), mock_db)
    
    assert len(res["factors"]) == 1
    assert res["factors"][0]["factor_name"] == "face_mismatch"


@patch("app.services.risk_scoring.create_risk_assessment")
@patch("app.services.risk_scoring.create_risk_factors")
def test_assess_session_risk_handles_missing_query_responses(mock_create_factors, mock_create_assessment):
    """Incomplete screenings must yield a risk result, not a None.data crash."""
    mock_create_assessment.return_value = {"id": "mock_id", "risk_score": 0.0}
    mock_create_factors.return_value = []
    mock_db = MagicMock()
    mock_db.table().select().eq().maybe_single().execute.return_value = None

    res = assess_session_risk(str(uuid4()), mock_db)

    assert res["assessment"]["id"] == "mock_id"
    assert res["factors"] == []


def test_get_risk_assessment_handles_missing_query_response():
    mock_db = MagicMock()
    mock_db.table().select().eq().maybe_single().execute.return_value = None

    assert repo.get_risk_assessment_by_session(mock_db, "session-id") is None


def test_get_risk_factors_handles_missing_query_response():
    mock_db = MagicMock()
    mock_db.table().select().eq().execute.return_value = None

    assert repo.get_risk_factors(mock_db, "risk-id") == []
