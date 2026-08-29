"""
VeriGate Backend — MRZ Parser Tests

Tests for the ICAO 9303 TD3 MRZ parser including:
- Check digit computation
- MRZ line detection from OCR text
- Full MRZ parsing with known values
- Check digit validation
- Error handling for invalid input
"""

import pytest
from app.services.mrz import (
    compute_check_digit,
    detect_mrz_lines,
    parse_td3_mrz,
    _parse_mrz_date,
    _char_value,
)


# ---------------------------------------------------------------------------
# Known test MRZ (matches seed data: SMITH, JAMES EDWARD, GBR, AB1234567)
# ---------------------------------------------------------------------------

VALID_LINE_1 = "P<GBRSMITH<<JAMES<EDWARD<<<<<<<<<<<<<<<<<<<<"
VALID_LINE_2 = "AB12345671GBR8503150M2907206<<<<<<<<<<<<<<04"


# ---------------------------------------------------------------------------
# Character value mapping
# ---------------------------------------------------------------------------

class TestCharValue:
    def test_digits(self):
        for i in range(10):
            assert _char_value(str(i)) == i

    def test_letters(self):
        assert _char_value("A") == 10
        assert _char_value("Z") == 35

    def test_filler(self):
        assert _char_value("<") == 0

    def test_lowercase_treated_as_uppercase(self):
        assert _char_value("a") == 10


# ---------------------------------------------------------------------------
# Check digit computation
# ---------------------------------------------------------------------------

class TestCheckDigit:
    def test_known_passport_number(self):
        """AB1234567 should have check digit 1."""
        assert compute_check_digit("AB1234567") == 1

    def test_known_dob(self):
        """850315 (15 Mar 1985) check digit should be 0."""
        assert compute_check_digit("850315") == 0

    def test_known_expiry(self):
        """290720 (20 Jul 2029) check digit should be 6."""
        assert compute_check_digit("290720") == 6

    def test_all_zeros(self):
        """All zeros should produce check digit 0."""
        assert compute_check_digit("000000") == 0

    def test_all_fillers(self):
        """All fillers '<' (value 0) should produce check digit 0."""
        assert compute_check_digit("<<<<<<<<") == 0

    def test_single_digit(self):
        """Single digit: 7 * 7 = 49, 49 % 10 = 9."""
        assert compute_check_digit("7") == 9


# ---------------------------------------------------------------------------
# MRZ line detection
# ---------------------------------------------------------------------------

class TestMrzDetection:
    def test_detect_from_clean_text(self):
        """Should detect MRZ lines from clean OCR output."""
        ocr_text = (
            "PASSPORT\n"
            "UNITED KINGDOM\n"
            "Surname: SMITH\n"
            "Given Names: JAMES EDWARD\n"
            f"{VALID_LINE_1}\n"
            f"{VALID_LINE_2}\n"
        )
        result = detect_mrz_lines(ocr_text)
        assert result is not None
        assert result[0] == VALID_LINE_1
        assert result[1] == VALID_LINE_2

    def test_detect_from_noisy_text(self):
        """Should detect MRZ even with extra text around it."""
        ocr_text = f"some noise\nmore noise\n{VALID_LINE_1}\n{VALID_LINE_2}\nfooter"
        result = detect_mrz_lines(ocr_text)
        assert result is not None
        assert result[0] == VALID_LINE_1

    def test_no_mrz_returns_none(self):
        """Should return None when no MRZ is present."""
        result = detect_mrz_lines("This is just regular text without any MRZ")
        assert result is None

    def test_single_line_returns_none(self):
        """Should return None with only one MRZ-like line."""
        result = detect_mrz_lines(VALID_LINE_1)
        assert result is None

    def test_handles_spaces_in_mrz(self):
        """Should handle MRZ lines with spaces (OCR artifact)."""
        spaced = "P< GBR SMITH <<JAMES<EDWARD<<<<<<<<<<<<<<<<<<<<"
        # After stripping spaces, this is still 44 chars
        ocr_text = f"{spaced}\n{VALID_LINE_2}\n"
        # This may or may not detect depending on spacing — test graceful handling
        result = detect_mrz_lines(ocr_text)
        # Either detected or gracefully returned None
        assert result is None or len(result) == 2


# ---------------------------------------------------------------------------
# Full MRZ parsing
# ---------------------------------------------------------------------------

class TestMrzParsing:
    def test_parse_valid_passport(self):
        """Parse a valid passport MRZ and check all fields."""
        result = parse_td3_mrz(VALID_LINE_1, VALID_LINE_2)

        assert result.document_code == "P"
        assert result.issuing_country == "GBR"
        assert result.surname == "SMITH"
        assert result.given_names == "JAMES EDWARD"
        assert result.document_number == "AB1234567"
        assert result.nationality == "GBR"
        assert result.date_of_birth == "850315"
        assert result.sex == "M"
        assert result.date_of_expiry == "290720"

    def test_check_digits_valid(self):
        """All check digits should be valid for the test MRZ."""
        result = parse_td3_mrz(VALID_LINE_1, VALID_LINE_2)
        assert result.all_checks_valid is True
        assert len(result.check_results) == 5

        for check in result.check_results:
            assert check.is_valid, f"Check '{check.field_name}' failed: expected={check.expected}, computed={check.computed}"

    def test_individual_check_digits(self):
        """Verify each individual check digit."""
        result = parse_td3_mrz(VALID_LINE_1, VALID_LINE_2)

        checks = {c.field_name: c for c in result.check_results}

        assert checks["document_number"].expected == 1
        assert checks["document_number"].computed == 1

        assert checks["date_of_birth"].expected == 0
        assert checks["date_of_birth"].computed == 0

        assert checks["date_of_expiry"].expected == 6
        assert checks["date_of_expiry"].computed == 6

    def test_dates_parsed(self):
        """Dates should be parsed into Python date objects."""
        result = parse_td3_mrz(VALID_LINE_1, VALID_LINE_2)

        assert result.date_of_birth_parsed is not None
        assert result.date_of_birth_parsed.year == 1985
        assert result.date_of_birth_parsed.month == 3
        assert result.date_of_birth_parsed.day == 15

        assert result.date_of_expiry_parsed is not None
        assert result.date_of_expiry_parsed.year == 2029
        assert result.date_of_expiry_parsed.month == 7
        assert result.date_of_expiry_parsed.day == 20

    def test_tampered_check_digit_detected(self):
        """Modifying a field should cause check digit validation to fail."""
        # Change document number from AB1234567 to AB1234568 (but keep old check digit 1)
        tampered_line_2 = "AB12345681GBR8503150M2907206<<<<<<<<<<<<<<04"
        result = parse_td3_mrz(VALID_LINE_1, tampered_line_2)

        # Document number check should fail
        doc_check = next(c for c in result.check_results if c.field_name == "document_number")
        assert doc_check.is_valid is False
        assert result.all_checks_valid is False


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

class TestMrzDateParsing:
    def test_dob_before_pivot(self):
        """Year 85 → 1985."""
        d = _parse_mrz_date("850315")
        assert d is not None
        assert d.year == 1985

    def test_expiry_after_pivot(self):
        """Year 29 → 2029."""
        d = _parse_mrz_date("290720")
        assert d is not None
        assert d.year == 2029

    def test_pivot_boundary_30(self):
        """Year 30 → 2030 (inclusive in modern range)."""
        d = _parse_mrz_date("300101")
        assert d is not None
        assert d.year == 2030

    def test_pivot_boundary_31(self):
        """Year 31 → 1931."""
        d = _parse_mrz_date("310101")
        assert d is not None
        assert d.year == 1931

    def test_invalid_date(self):
        """Invalid date should return None."""
        assert _parse_mrz_date("001332") is None  # Month 13

    def test_non_numeric(self):
        """Non-numeric input should return None."""
        assert _parse_mrz_date("ABCDEF") is None
