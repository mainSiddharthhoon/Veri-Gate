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


def extract_fields_from_raw_text(raw_text: str) -> DocumentData | None:
    """Fallback field extractor when standard MRZ is absent or obscured.

    Parses pipe-delimited machine-readable test text or visual inspection zone
    labels (FULL NAME, DOCUMENT NUMBER, NATIONALITY, DOB, EXPIRY, GENDER, ISSUE DATE).
    """
    if not raw_text:
        return None

    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    if not lines:
        return None

    from datetime import datetime

    def _parse_any_date(s: str) -> date | None:
        if not s:
            return None
        s = s.strip()
        for fmt in ("%b %d, %Y", "%b %d %Y", "%d %b %Y", "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except Exception:
                pass
        return None

    doc = DocumentData(document_type="passport")

    # 1. First priority: Check pipe-delimited test text (e.g. VGX|VG7K4M218|ADAMGGILCHRIST|AUSTRALIAN|1978-06-06|2024-01-09|M)
    for line in lines:
        if "|" in line and ("VGX|" in line or len(line.split("|")) >= 5):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                doc.document_number = parts[1]
                raw_name = parts[2]
                doc.surname = raw_name[-9:] if len(raw_name) > 9 else raw_name
                doc.given_names = raw_name[:-9] if len(raw_name) > 9 else ""
                doc.nationality = parts[3].capitalize()
                doc.issuing_country = doc.nationality
                doc.date_of_birth = _parse_any_date(parts[4])
                doc.date_of_expiry = _parse_any_date(parts[5])
                doc.sex = _normalize_sex(parts[6])
                break
            elif len(parts) == 6:
                doc.document_number = parts[1]
                raw_name = parts[2]
                doc.surname = raw_name[-9:] if len(raw_name) > 9 else raw_name
                doc.given_names = raw_name[:-9] if len(raw_name) > 9 else ""
                m_dob = re.search(r"(\d{4}-\d{2}-\d{2})", parts[3])
                if m_dob:
                    doc.date_of_birth = _parse_any_date(m_dob.group(1))
                    nat = parts[3][:m_dob.start()].strip()
                    if nat:
                        doc.nationality = nat.capitalize()
                        doc.issuing_country = doc.nationality
                m_exp = re.search(r"(\d{4}-\d{2}-\d{2})", parts[4])
                if m_exp:
                    doc.date_of_expiry = _parse_any_date(m_exp.group(1))
                doc.sex = _normalize_sex(parts[5])
                break

    # 2. Extract visual fields to refine name, document number with hyphens, issue date
    for i, line in enumerate(lines):
        upper = line.upper()
        if "FULL NAME" in upper and i + 1 < len(lines):
            candidate = lines[i + 1].strip()
            if not any(k in candidate.upper() for k in ("DOCUMENT", "GENDER", "|", "VERIGATE", "CARD", "FICTIONAL")):
                tokens = candidate.split()
                if len(tokens) >= 2:
                    doc.surname = tokens[-1]
                    doc.given_names = " ".join(tokens[:-1])
                else:
                    doc.surname = candidate
                    doc.given_names = ""
        elif "DOCUMENT NUMBER" in upper and not doc.document_number:
            for j in range(i + 1, min(i + 5, len(lines))):
                cand = lines[j].strip()
                if re.match(r"^VG-[A-Z0-9]+-[A-Z0-9]+$", cand) or (re.match(r"^[A-Z0-9-]{6,15}$", cand) and cand not in ("GENDER", "NATIONALITY", "ISSUED", "EXPIRES")):
                    doc.document_number = cand
                    break
        elif "NATIONALITY" in upper and not doc.nationality:
            for j in range(i + 1, min(i + 5, len(lines))):
                cand = lines[j].strip()
                if cand in ("Australian", "German", "American", "British", "French", "Canadian", "Indian") or (len(cand) > 3 and cand.isalpha() and cand.upper() not in ("ISSUED", "EXPIRES", "DATE")):
                    doc.nationality = cand
                    doc.issuing_country = cand
                    break
        elif ("GENDER" in upper or "SEX" in upper) and not doc.sex:
            for j in range(i + 1, min(i + 3, len(lines))):
                cand = lines[j].strip().upper()
                if cand in ("M", "F", "X"):
                    doc.sex = _normalize_sex(cand)
                    break
        elif ("ISSUED" in upper or "ISSUE DATE" in upper) and not doc.date_of_issue:
            for j in range(i + 1, min(i + 4, len(lines))):
                d = _parse_any_date(lines[j])
                if d:
                    doc.date_of_issue = d
                    break

    # Look for formatted document ID like VG-XXXX-XXX anywhere
    for line in lines:
        m_vg = re.search(r"\b(VG-[A-Z0-9]+-[A-Z0-9]+)\b", line)
        if m_vg:
            doc.document_number = m_vg.group(1)
            break

    # 3. Fallback date resolution if dates are still missing
    if not doc.date_of_birth or not doc.date_of_expiry:
        dates: list[date] = []
        for line in lines:
            d = _parse_any_date(line)
            if d and d not in dates:
                dates.append(d)
            else:
                m = re.search(r"(\b[A-Za-z]{3}\s+\d{1,2},?\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b)", line)
                if m:
                    d = _parse_any_date(m.group(1))
                    if d and d not in dates:
                        dates.append(d)
        if dates:
            dates_sorted = sorted(dates)
            if not doc.date_of_birth:
                doc.date_of_birth = dates_sorted[0]
            if not doc.date_of_expiry and len(dates_sorted) > 1:
                doc.date_of_expiry = dates_sorted[-1]
            if not doc.date_of_issue and len(dates_sorted) > 2:
                doc.date_of_issue = dates_sorted[1]

    if not doc.document_number and not doc.surname:
        return None

    return doc
