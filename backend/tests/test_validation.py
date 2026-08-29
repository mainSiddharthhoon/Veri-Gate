"""
VeriGate Backend — Validation Service Unit Tests

Tests for the pure validation logic in app.services.validation.
No database access required — all tests use synthetic document dicts.
"""

import pytest
from datetime import date, timedelta

from app.services.validation import (
    validate_document,
    ValidationCheck,
    ValidationResult,
    _check_required_fields,
    _check_formats,
    _check_dates,
    _check_mrz,
    _check_reference,
)


# ---------------------------------------------------------------------------
# Test fixtures — synthetic document data
# ---------------------------------------------------------------------------

def _make_valid_document() -> dict:
    """Create a complete, valid passport document dict."""
    return {
        "document_type": "passport",
        "document_number": "AB1234567",
        "issuing_country": "GBR",
        "nationality": "GBR",
        "surname": "SMITH",
        "given_names": "JAMES EDWARD",
        "date_of_birth": "1985-03-15",
        "sex": "M",
        "date_of_issue": "2019-07-20",
        "date_of_expiry": "2029-07-20",
        "mrz_line_1": "P<GBRSMITH<<JAMES<EDWARD<<<<<<<<<<<<<<<<<<<<",
        "mrz_line_2": "AB12345671GBR8503150M2907206<<<<<<<<<<<<<<04",
    }


def _make_valid_mrz_parsed() -> dict:
    """Create valid parsed MRZ data matching the test document."""
    return {
        "document_code": "P",
        "issuing_country": "GBR",
        "surname": "SMITH",
        "given_names": "JAMES EDWARD",
        "document_number": "AB1234567",
        "nationality": "GBR",
        "date_of_birth": "850315",
        "sex": "M",
        "date_of_expiry": "290720",
        "personal_number": "",
        "all_checks_valid": True,
        "check_digits": {
            "document_number": {"expected": 1, "computed": 1, "valid": True},
            "date_of_birth": {"expected": 0, "computed": 0, "valid": True},
            "date_of_expiry": {"expected": 6, "computed": 6, "valid": True},
            "personal_number": {"expected": 0, "computed": 0, "valid": True},
            "composite": {"expected": 4, "computed": 4, "valid": True},
        },
    }


def _make_valid_reference() -> dict:
    """Create a valid reference document record."""
    return {
        "document_type": "passport",
        "document_number": "AB1234567",
        "issuing_country": "GBR",
        "holder_surname": "SMITH",
        "holder_given_names": "JAMES EDWARD",
        "date_of_birth": "1985-03-15",
        "date_of_expiry": "2029-07-20",
        "status": "valid",
    }


# ---------------------------------------------------------------------------
# Full validation — happy path
# ---------------------------------------------------------------------------

class TestFullValidation:
    def test_valid_document_passes_all(self):
        """A fully valid document should have is_valid=True and 0 failures."""
        doc = _make_valid_document()
        mrz = _make_valid_mrz_parsed()
        ref = _make_valid_reference()
        result = validate_document(doc, mrz, ref)

        assert result.is_valid is True
        assert result.checks_failed == 0
        assert result.checks_passed > 0
        assert len(result.checks) == 25

    def test_no_reference_still_valid(self):
        """A valid document without reference should still be valid (reference checks skipped)."""
        doc = _make_valid_document()
        mrz = _make_valid_mrz_parsed()
        result = validate_document(doc, mrz, None)

        assert result.is_valid is True
        assert result.checks_failed == 0
        # 4 database checks should be skipped
        db_checks = [c for c in result.checks if c.check_category == "database"]
        assert all(c.status == "skipped" for c in db_checks)


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------

class TestRequiredFields:
    def test_all_present(self):
        doc = _make_valid_document()
        checks = _check_required_fields(doc)
        assert len(checks) == 7
        assert all(c.status == "passed" for c in checks)

    def test_missing_document_number(self):
        doc = _make_valid_document()
        doc["document_number"] = None
        checks = _check_required_fields(doc)
        failed = [c for c in checks if c.status == "failed"]
        assert len(failed) == 1
        assert failed[0].check_name == "required_document_number"

    def test_missing_surname(self):
        doc = _make_valid_document()
        doc["surname"] = ""
        checks = _check_required_fields(doc)
        failed = [c for c in checks if c.status == "failed"]
        assert len(failed) == 1
        assert failed[0].check_name == "required_surname"

    def test_missing_multiple_fields(self):
        doc = _make_valid_document()
        doc["surname"] = None
        doc["nationality"] = None
        doc["sex"] = None
        checks = _check_required_fields(doc)
        failed = [c for c in checks if c.status == "failed"]
        assert len(failed) == 3

    def test_empty_string_is_missing(self):
        doc = _make_valid_document()
        doc["given_names"] = "   "
        checks = _check_required_fields(doc)
        failed = [c for c in checks if c.status == "failed"]
        assert len(failed) == 1
        assert failed[0].check_name == "required_given_names"


# ---------------------------------------------------------------------------
# Format checks
# ---------------------------------------------------------------------------

class TestFormatChecks:
    def test_valid_formats(self):
        doc = _make_valid_document()
        checks = _check_formats(doc)
        assert all(c.status == "passed" for c in checks)

    def test_invalid_document_number(self):
        doc = _make_valid_document()
        doc["document_number"] = "abc"  # too short, lowercase
        checks = _check_formats(doc)
        doc_num_check = next(c for c in checks if c.check_name == "document_number_format")
        assert doc_num_check.status == "failed"

    def test_valid_document_number_formats(self):
        """Various valid passport number formats."""
        for num in ["AB1234567", "XY999888", "123456", "ABCDEFGHI"]:
            doc = _make_valid_document()
            doc["document_number"] = num
            checks = _check_formats(doc)
            check = next(c for c in checks if c.check_name == "document_number_format")
            assert check.status == "passed", f"Expected {num} to be valid"

    def test_invalid_country_code(self):
        doc = _make_valid_document()
        doc["issuing_country"] = "GB"  # 2 chars, not 3
        checks = _check_formats(doc)
        country_check = next(c for c in checks if c.check_name == "country_code_format")
        assert country_check.status == "failed"

    def test_invalid_sex(self):
        doc = _make_valid_document()
        doc["sex"] = "Z"
        checks = _check_formats(doc)
        sex_check = next(c for c in checks if c.check_name == "sex_format")
        assert sex_check.status == "failed"

    def test_missing_field_skipped(self):
        doc = _make_valid_document()
        doc["document_number"] = None
        checks = _check_formats(doc)
        check = next(c for c in checks if c.check_name == "document_number_format")
        assert check.status == "skipped"


# ---------------------------------------------------------------------------
# Date checks
# ---------------------------------------------------------------------------

class TestDateChecks:
    def test_valid_dates(self):
        doc = _make_valid_document()
        checks = _check_dates(doc)
        passed = [c for c in checks if c.status == "passed"]
        assert len(passed) >= 4  # dob_not_future, dob_reasonable_age, expiry_not_past, expiry_not_too_far

    def test_future_dob_fails(self):
        doc = _make_valid_document()
        future = (date.today() + timedelta(days=365)).isoformat()
        doc["date_of_birth"] = future
        checks = _check_dates(doc)
        dob_check = next(c for c in checks if c.check_name == "dob_not_future")
        assert dob_check.status == "failed"

    def test_expired_document_fails(self):
        doc = _make_valid_document()
        long_ago = (date.today() - timedelta(days=365)).isoformat()
        doc["date_of_expiry"] = long_ago
        checks = _check_dates(doc)
        expiry_check = next(c for c in checks if c.check_name == "expiry_not_past")
        assert expiry_check.status == "failed"

    def test_recently_expired_warns(self):
        doc = _make_valid_document()
        recent = (date.today() - timedelta(days=30)).isoformat()
        doc["date_of_expiry"] = recent
        checks = _check_dates(doc)
        expiry_check = next(c for c in checks if c.check_name == "expiry_not_past")
        assert expiry_check.status == "warning"

    def test_far_future_expiry_warns(self):
        doc = _make_valid_document()
        far = (date.today() + timedelta(days=15 * 365)).isoformat()
        doc["date_of_expiry"] = far
        checks = _check_dates(doc)
        check = next(c for c in checks if c.check_name == "expiry_not_too_far")
        assert check.status == "warning"

    def test_issue_after_expiry_fails(self):
        doc = _make_valid_document()
        doc["date_of_issue"] = "2030-01-01"
        doc["date_of_expiry"] = "2029-07-20"
        checks = _check_dates(doc)
        check = next(c for c in checks if c.check_name == "issue_before_expiry")
        assert check.status == "failed"

    def test_no_issue_date_skipped(self):
        doc = _make_valid_document()
        doc["date_of_issue"] = None
        checks = _check_dates(doc)
        check = next(c for c in checks if c.check_name == "issue_before_expiry")
        assert check.status == "skipped"

    def test_missing_dob_skipped(self):
        doc = _make_valid_document()
        doc["date_of_birth"] = None
        checks = _check_dates(doc)
        dob_checks = [c for c in checks if "dob" in c.check_name]
        assert all(c.status == "skipped" for c in dob_checks)


# ---------------------------------------------------------------------------
# MRZ checks
# ---------------------------------------------------------------------------

class TestMrzChecks:
    def test_valid_mrz(self):
        doc = _make_valid_document()
        mrz = _make_valid_mrz_parsed()
        checks = _check_mrz(doc, mrz)
        assert all(c.status in ("passed", "skipped") for c in checks)

    def test_mrz_check_digit_failure(self):
        doc = _make_valid_document()
        mrz = _make_valid_mrz_parsed()
        mrz["all_checks_valid"] = False
        mrz["check_digits"]["document_number"]["valid"] = False
        checks = _check_mrz(doc, mrz)
        cd_check = next(c for c in checks if c.check_name == "mrz_check_digits")
        assert cd_check.status == "failed"

    def test_mrz_document_number_mismatch(self):
        doc = _make_valid_document()
        mrz = _make_valid_mrz_parsed()
        mrz["document_number"] = "ZZ9999999"
        checks = _check_mrz(doc, mrz)
        match_check = next(c for c in checks if c.check_name == "mrz_document_number_match")
        assert match_check.status == "failed"

    def test_mrz_nationality_mismatch(self):
        doc = _make_valid_document()
        mrz = _make_valid_mrz_parsed()
        mrz["nationality"] = "USA"
        checks = _check_mrz(doc, mrz)
        match_check = next(c for c in checks if c.check_name == "mrz_nationality_match")
        assert match_check.status == "failed"

    def test_mrz_name_mismatch(self):
        doc = _make_valid_document()
        mrz = _make_valid_mrz_parsed()
        mrz["surname"] = "JONES"
        checks = _check_mrz(doc, mrz)
        match_check = next(c for c in checks if c.check_name == "mrz_name_match")
        assert match_check.status == "failed"

    def test_no_mrz_parsed_skips_all(self):
        doc = _make_valid_document()
        checks = _check_mrz(doc, None)
        skipped = [c for c in checks if c.check_name.startswith("mrz_") and c.check_name != "mrz_structure"]
        assert all(c.status == "skipped" for c in skipped)

    def test_bad_mrz_structure(self):
        doc = _make_valid_document()
        doc["mrz_line_1"] = "TOO_SHORT"
        doc["mrz_line_2"] = "ALSO_SHORT"
        checks = _check_mrz(doc, None)
        struct_check = next(c for c in checks if c.check_name == "mrz_structure")
        assert struct_check.status == "failed"


# ---------------------------------------------------------------------------
# Reference database checks
# ---------------------------------------------------------------------------

class TestReferenceChecks:
    def test_valid_reference(self):
        doc = _make_valid_document()
        ref = _make_valid_reference()
        checks = _check_reference(doc, ref)
        assert all(c.status == "passed" for c in checks)

    def test_no_reference_skips_all(self):
        doc = _make_valid_document()
        checks = _check_reference(doc, None)
        assert all(c.status == "skipped" for c in checks)
        assert len(checks) == 4

    def test_stolen_reference_fails(self):
        doc = _make_valid_document()
        ref = _make_valid_reference()
        ref["status"] = "stolen"
        checks = _check_reference(doc, ref)
        status_check = next(c for c in checks if c.check_name == "reference_status")
        assert status_check.status == "failed"
        assert "stolen" in status_check.message.lower()

    def test_watchlist_reference_fails(self):
        doc = _make_valid_document()
        ref = _make_valid_reference()
        ref["status"] = "watchlist"
        checks = _check_reference(doc, ref)
        status_check = next(c for c in checks if c.check_name == "reference_status")
        assert status_check.status == "failed"

    def test_expired_reference_warns(self):
        doc = _make_valid_document()
        ref = _make_valid_reference()
        ref["status"] = "expired"
        checks = _check_reference(doc, ref)
        status_check = next(c for c in checks if c.check_name == "reference_status")
        assert status_check.status == "warning"

    def test_holder_name_mismatch_warns(self):
        doc = _make_valid_document()
        ref = _make_valid_reference()
        ref["holder_surname"] = "JONES"
        checks = _check_reference(doc, ref)
        holder_check = next(c for c in checks if c.check_name == "reference_holder_match")
        assert holder_check.status == "warning"

    def test_dob_mismatch_fails(self):
        doc = _make_valid_document()
        ref = _make_valid_reference()
        ref["date_of_birth"] = "1990-01-01"
        checks = _check_reference(doc, ref)
        dob_check = next(c for c in checks if c.check_name == "reference_dob_match")
        assert dob_check.status == "failed"


# ---------------------------------------------------------------------------
# Aggregate behavior
# ---------------------------------------------------------------------------

class TestAggregates:
    def test_warnings_dont_invalidate(self):
        """Warnings alone should not set is_valid to False."""
        doc = _make_valid_document()
        ref = _make_valid_reference()
        ref["status"] = "expired"  # This produces a warning
        result = validate_document(doc, _make_valid_mrz_parsed(), ref)
        assert result.is_valid is True
        assert result.checks_warned > 0

    def test_single_failure_invalidates(self):
        """A single failed check should set is_valid to False."""
        doc = _make_valid_document()
        ref = _make_valid_reference()
        ref["status"] = "stolen"  # This produces a failure
        result = validate_document(doc, _make_valid_mrz_parsed(), ref)
        assert result.is_valid is False
        assert result.checks_failed > 0

    def test_check_count_consistency(self):
        """passed + failed + warned + skipped should equal total checks."""
        doc = _make_valid_document()
        result = validate_document(doc, _make_valid_mrz_parsed(), None)
        total = result.checks_passed + result.checks_failed + result.checks_warned + result.checks_skipped
        assert total == len(result.checks)
