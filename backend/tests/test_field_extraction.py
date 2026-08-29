"""
VeriGate Backend — Field Extraction Tests

Tests for extracting structured passport fields from MRZ data.
"""

import pytest
from datetime import date

from app.services.mrz import parse_td3_mrz
from app.services.field_extraction import (
    extract_passport_fields,
    _normalize_sex,
    _extract_date_of_issue,
    DocumentData,
)


# Known valid MRZ lines
VALID_LINE_1 = "P<GBRSMITH<<JAMES<EDWARD<<<<<<<<<<<<<<<<<<<<"
VALID_LINE_2 = "AB12345671GBR8503150M2907206<<<<<<<<<<<<<<04"


class TestExtractPassportFields:
    def test_basic_extraction(self):
        """Extract fields from valid MRZ result."""
        mrz = parse_td3_mrz(VALID_LINE_1, VALID_LINE_2)
        doc = extract_passport_fields(mrz)

        assert doc.document_type == "passport"
        assert doc.document_number == "AB1234567"
        assert doc.issuing_country == "GBR"
        assert doc.nationality == "GBR"
        assert doc.surname == "SMITH"
        assert doc.given_names == "JAMES EDWARD"
        assert doc.sex == "M"

    def test_dates_extracted(self):
        """DOB and expiry should be parsed as date objects."""
        mrz = parse_td3_mrz(VALID_LINE_1, VALID_LINE_2)
        doc = extract_passport_fields(mrz)

        assert doc.date_of_birth == date(1985, 3, 15)
        assert doc.date_of_expiry == date(2029, 7, 20)

    def test_mrz_lines_preserved(self):
        """Raw MRZ lines should be stored."""
        mrz = parse_td3_mrz(VALID_LINE_1, VALID_LINE_2)
        doc = extract_passport_fields(mrz)

        assert doc.mrz_line_1 == VALID_LINE_1
        assert doc.mrz_line_2 == VALID_LINE_2

    def test_mrz_parsed_dict(self):
        """mrz_parsed should be a dict with check digit info."""
        mrz = parse_td3_mrz(VALID_LINE_1, VALID_LINE_2)
        doc = extract_passport_fields(mrz)

        assert doc.mrz_parsed is not None
        assert doc.mrz_parsed["document_number"] == "AB1234567"
        assert "check_digits" in doc.mrz_parsed
        assert doc.mrz_parsed["all_checks_valid"] is True

    def test_to_db_dict(self):
        """to_db_dict should produce a Supabase-ready dict."""
        mrz = parse_td3_mrz(VALID_LINE_1, VALID_LINE_2)
        doc = extract_passport_fields(mrz)
        db_dict = doc.to_db_dict("test-session-123")

        assert db_dict["session_id"] == "test-session-123"
        assert db_dict["document_type"] == "passport"
        assert db_dict["document_number"] == "AB1234567"
        assert db_dict["date_of_birth"] == "1985-03-15"
        assert db_dict["date_of_expiry"] == "2029-07-20"
        assert db_dict["mrz_parsed"] is not None

    def test_date_of_issue_not_in_mrz(self):
        """Date of issue is not in MRZ — should be None without VIZ text."""
        mrz = parse_td3_mrz(VALID_LINE_1, VALID_LINE_2)
        doc = extract_passport_fields(mrz, raw_text="")
        assert doc.date_of_issue is None


class TestNormalizeSex:
    def test_valid_values(self):
        assert _normalize_sex("M") == "M"
        assert _normalize_sex("F") == "F"
        assert _normalize_sex("X") == "X"

    def test_lowercase(self):
        assert _normalize_sex("m") == "M"

    def test_invalid(self):
        assert _normalize_sex("Z") is None
        assert _normalize_sex("") is None


class TestExtractDateOfIssue:
    def test_with_date_of_issue_text(self):
        """Should extract date from 'Date of Issue: DD/MM/YYYY' pattern."""
        text = "some text\nDate of Issue: 20/07/2019\nmore text"
        result = _extract_date_of_issue(text)
        assert result == date(2019, 7, 20)

    def test_with_issued_keyword(self):
        """Should extract date from 'Issued: DD-MM-YYYY' pattern."""
        text = "Issued: 20-07-2019"
        result = _extract_date_of_issue(text)
        assert result == date(2019, 7, 20)

    def test_iso_format(self):
        """Should extract date from 'Date of Issue: YYYY-MM-DD' pattern."""
        text = "Date of Issue: 2019-07-20"
        result = _extract_date_of_issue(text)
        assert result == date(2019, 7, 20)

    def test_no_date_found(self):
        """Should return None when no date pattern is found."""
        result = _extract_date_of_issue("No date here")
        assert result is None

    def test_empty_text(self):
        """Should return None for empty text."""
        result = _extract_date_of_issue("")
        assert result is None
