"""
VeriGate Backend — Field Extraction Service

Extracts structured passport fields from MRZ data and raw OCR text.
MRZ is the primary data source; VIZ (Visual Inspection Zone) text
from OCR is used as a fallback for fields not in the MRZ.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.services.mrz import MrzResult


@dataclass
class DocumentData:
    """Structured passport fields ready for database storage."""
    document_type: str = "passport"
    document_number: Optional[str] = None
    issuing_country: Optional[str] = None
    nationality: Optional[str] = None
    surname: Optional[str] = None
    given_names: Optional[str] = None
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None
    date_of_issue: Optional[date] = None
    date_of_expiry: Optional[date] = None
    mrz_line_1: Optional[str] = None
    mrz_line_2: Optional[str] = None
    mrz_parsed: Optional[dict] = None

    def to_db_dict(self, session_id: str) -> dict:
        """Convert to a dict suitable for Supabase insert."""
        data = {
            "session_id": session_id,
            "document_type": self.document_type,
            "document_number": self.document_number,
            "issuing_country": self.issuing_country,
            "nationality": self.nationality,
            "surname": self.surname,
            "given_names": self.given_names,
            "sex": self.sex,
            "mrz_line_1": self.mrz_line_1,
            "mrz_line_2": self.mrz_line_2,
            "mrz_parsed": self.mrz_parsed,
        }
        # Dates need to be converted to ISO strings for JSON serialization
        if self.date_of_birth:
            data["date_of_birth"] = self.date_of_birth.isoformat()
        if self.date_of_issue:
            data["date_of_issue"] = self.date_of_issue.isoformat()
        if self.date_of_expiry:
            data["date_of_expiry"] = self.date_of_expiry.isoformat()

        return data


def extract_passport_fields(mrz_result: MrzResult, raw_text: str = "") -> DocumentData:
    """Extract structured passport fields from MRZ and OCR data.

    MRZ is the primary source for most fields. Date of issue is NOT
    present in the MRZ and is extracted from VIZ text if possible.

    Args:
        mrz_result: Parsed MRZ data.
        raw_text: Raw OCR text for VIZ fallback extraction.

    Returns:
        DocumentData with structured fields.
    """
    doc = DocumentData(
        document_type="passport",
        document_number=mrz_result.document_number or None,
        issuing_country=mrz_result.issuing_country or None,
        nationality=mrz_result.nationality or None,
        surname=mrz_result.surname or None,
        given_names=mrz_result.given_names or None,
        date_of_birth=mrz_result.date_of_birth_parsed,
        sex=_normalize_sex(mrz_result.sex),
        date_of_expiry=mrz_result.date_of_expiry_parsed,
        mrz_line_1=mrz_result.line1,
        mrz_line_2=mrz_result.line2,
        mrz_parsed=_mrz_to_dict(mrz_result),
    )

    # Try to extract date of issue from VIZ text (not in MRZ)
    doc.date_of_issue = _extract_date_of_issue(raw_text)

    return doc


def _normalize_sex(sex: str) -> str | None:
    """Normalize sex field to match database CHECK constraint (M, F, X)."""
    sex = sex.upper().strip()
    if sex in ("M", "F", "X"):
        return sex
    return None


def _mrz_to_dict(mrz: MrzResult) -> dict:
    """Convert MRZ result to a JSON-serializable dict for mrz_parsed column."""
    return {
        "document_code": mrz.document_code,
        "issuing_country": mrz.issuing_country,
        "surname": mrz.surname,
        "given_names": mrz.given_names,
        "document_number": mrz.document_number,
        "nationality": mrz.nationality,
        "date_of_birth": mrz.date_of_birth,
        "sex": mrz.sex,
        "date_of_expiry": mrz.date_of_expiry,
        "personal_number": mrz.personal_number,
        "check_digits": {
            c.field_name: {
                "expected": c.expected,
                "computed": c.computed,
                "valid": c.is_valid,
            }
            for c in mrz.check_results
        },
        "all_checks_valid": mrz.all_checks_valid,
    }


def _extract_date_of_issue(raw_text: str) -> date | None:
    """Try to extract the date of issue from VIZ OCR text.

    Looks for patterns near keywords like 'date of issue', 'issued', etc.
    This is best-effort — the date of issue is not in the MRZ.

    Returns:
        Parsed date or None if not found.
    """
    if not raw_text:
        return None

    text = raw_text.upper()

    # Look for date patterns near "issue" keyword
    # Common formats: DD/MM/YYYY, DD-MM-YYYY, DD MMM YYYY, YYYY-MM-DD
    issue_patterns = [
        r"(?:DATE\s*OF\s*ISSUE|ISSUED?|ISSUE\s*DATE)[:\s]*(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})",
        r"(?:DATE\s*OF\s*ISSUE|ISSUED?|ISSUE\s*DATE)[:\s]*(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})",
    ]

    for pattern in issue_patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            try:
                if len(groups[0]) == 4:
                    # YYYY-MM-DD format
                    return date(int(groups[0]), int(groups[1]), int(groups[2]))
                else:
                    # DD/MM/YYYY format
                    return date(int(groups[2]), int(groups[1]), int(groups[0]))
            except ValueError:
                continue

    return None
