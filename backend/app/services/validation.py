"""
VeriGate Backend — Document Validation Service

Pure validation logic for passport documents. Takes structured document data
and returns explainable validation results with individual check outcomes.

All checks are deterministic — no ML or external API calls.
Each check produces a ValidationCheck with status, values, and human-readable message.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ValidationCheck:
    """A single validation check result."""
    check_name: str
    check_category: str   # 'fields' | 'format' | 'dates' | 'mrz' | 'database'
    status: str           # 'passed' | 'failed' | 'warning' | 'skipped'
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    message: str = ""

    def to_db_dict(self, validation_result_id: str) -> dict:
        """Convert to a dict suitable for Supabase insert."""
        return {
            "validation_result_id": validation_result_id,
            "check_name": self.check_name,
            "check_category": self.check_category,
            "status": self.status,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "message": self.message,
        }


@dataclass
class ValidationResult:
    """Complete validation result with all individual checks."""
    is_valid: bool = True
    checks: list[ValidationCheck] = field(default_factory=list)
    checks_passed: int = 0
    checks_failed: int = 0
    checks_warned: int = 0
    checks_skipped: int = 0


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DOCUMENT_NUMBER_PATTERN = re.compile(r"^[A-Z0-9]{6,9}$")
_COUNTRY_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")
_MRZ_LINE_PATTERN = re.compile(r"^[A-Z0-9<]{44}$")
_VALID_SEX_VALUES = {"M", "F", "X"}

# Passport validity is typically max 10 years
_MAX_PASSPORT_VALIDITY_YEARS = 11
_RECENT_EXPIRY_GRACE_DAYS = 180  # 6 months


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def validate_document(
    document: dict,
    mrz_parsed: dict | None = None,
    reference: dict | None = None,
) -> ValidationResult:
    """Validate a document's fields, format, dates, MRZ, and reference status.

    Args:
        document: Extracted document fields (from the `documents` table).
        mrz_parsed: Parsed MRZ data (from `documents.mrz_parsed` JSONB column).
        reference: Reference document record (from `reference_documents` table),
                   or None if not found.

    Returns:
        ValidationResult with all individual checks and aggregate counts.
    """
    checks: list[ValidationCheck] = []

    # Run all check categories
    checks.extend(_check_required_fields(document))
    checks.extend(_check_formats(document))
    checks.extend(_check_dates(document))
    checks.extend(_check_mrz(document, mrz_parsed))
    checks.extend(_check_reference(document, reference))

    # Compute aggregates
    passed = sum(1 for c in checks if c.status == "passed")
    failed = sum(1 for c in checks if c.status == "failed")
    warned = sum(1 for c in checks if c.status == "warning")
    skipped = sum(1 for c in checks if c.status == "skipped")

    return ValidationResult(
        is_valid=(failed == 0),
        checks=checks,
        checks_passed=passed,
        checks_failed=failed,
        checks_warned=warned,
        checks_skipped=skipped,
    )


# ---------------------------------------------------------------------------
# Category 1: Required fields
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = [
    ("document_number", "Passport/document number"),
    ("surname", "Surname"),
    ("given_names", "Given names"),
    ("nationality", "Nationality"),
    ("date_of_birth", "Date of birth"),
    ("sex", "Sex"),
    ("date_of_expiry", "Date of expiry"),
]


def _check_required_fields(doc: dict) -> list[ValidationCheck]:
    """Check that all required passport fields are present and non-empty."""
    checks = []
    for field_name, label in _REQUIRED_FIELDS:
        value = doc.get(field_name)
        present = value is not None and str(value).strip() != ""
        checks.append(ValidationCheck(
            check_name=f"required_{field_name}",
            check_category="fields",
            status="passed" if present else "failed",
            expected_value="present",
            actual_value="present" if present else "missing",
            message=f"{label} is present." if present else f"{label} is missing.",
        ))
    return checks


# ---------------------------------------------------------------------------
# Category 2: Format checks
# ---------------------------------------------------------------------------

def _check_formats(doc: dict) -> list[ValidationCheck]:
    """Check field format validity."""
    checks = []

    # Document number format
    doc_num = doc.get("document_number") or ""
    doc_num_clean = doc_num.strip().upper()
    if doc_num_clean:
        valid = bool(_DOCUMENT_NUMBER_PATTERN.match(doc_num_clean))
        checks.append(ValidationCheck(
            check_name="document_number_format",
            check_category="format",
            status="passed" if valid else "failed",
            expected_value="6-9 alphanumeric characters",
            actual_value=doc_num_clean,
            message=(
                "Document number format is valid."
                if valid else
                f"Document number '{doc_num_clean}' does not match expected format (6-9 alphanumeric characters)."
            ),
        ))
    else:
        checks.append(ValidationCheck(
            check_name="document_number_format",
            check_category="format",
            status="skipped",
            message="Document number format check skipped — field is missing.",
        ))

    # Issuing country code format
    country = doc.get("issuing_country") or ""
    country_clean = country.strip().upper()
    if country_clean:
        valid = bool(_COUNTRY_CODE_PATTERN.match(country_clean))
        checks.append(ValidationCheck(
            check_name="country_code_format",
            check_category="format",
            status="passed" if valid else "failed",
            expected_value="3 uppercase letters (ISO 3166-1 alpha-3)",
            actual_value=country_clean,
            message=(
                "Issuing country code format is valid."
                if valid else
                f"Issuing country code '{country_clean}' is not a valid 3-letter code."
            ),
        ))
    else:
        checks.append(ValidationCheck(
            check_name="country_code_format",
            check_category="format",
            status="skipped",
            message="Country code format check skipped — field is missing.",
        ))

    # Nationality code format
    nationality = doc.get("nationality") or ""
    nat_clean = nationality.strip().upper()
    if nat_clean:
        valid = bool(_COUNTRY_CODE_PATTERN.match(nat_clean))
        checks.append(ValidationCheck(
            check_name="nationality_code_format",
            check_category="format",
            status="passed" if valid else "failed",
            expected_value="3 uppercase letters (ISO 3166-1 alpha-3)",
            actual_value=nat_clean,
            message=(
                "Nationality code format is valid."
                if valid else
                f"Nationality code '{nat_clean}' is not a valid 3-letter code."
            ),
        ))
    else:
        checks.append(ValidationCheck(
            check_name="nationality_code_format",
            check_category="format",
            status="skipped",
            message="Nationality code format check skipped — field is missing.",
        ))

    # Sex format
    sex = doc.get("sex") or ""
    sex_clean = sex.strip().upper()
    if sex_clean:
        valid = sex_clean in _VALID_SEX_VALUES
        checks.append(ValidationCheck(
            check_name="sex_format",
            check_category="format",
            status="passed" if valid else "failed",
            expected_value="M, F, or X",
            actual_value=sex_clean,
            message=(
                "Sex field format is valid."
                if valid else
                f"Sex field '{sex_clean}' is not one of M, F, X."
            ),
        ))
    else:
        checks.append(ValidationCheck(
            check_name="sex_format",
            check_category="format",
            status="skipped",
            message="Sex format check skipped — field is missing.",
        ))

    return checks


# ---------------------------------------------------------------------------
# Category 3: Date checks
# ---------------------------------------------------------------------------

def _parse_date_value(value) -> date | None:
    """Parse a date value that may be a date object or ISO string."""
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def _check_dates(doc: dict) -> list[ValidationCheck]:
    """Check date validity and consistency."""
    checks = []
    today = date.today()

    dob = _parse_date_value(doc.get("date_of_birth"))
    expiry = _parse_date_value(doc.get("date_of_expiry"))
    issue = _parse_date_value(doc.get("date_of_issue"))

    # DOB not in the future
    if dob:
        if dob > today:
            checks.append(ValidationCheck(
                check_name="dob_not_future",
                check_category="dates",
                status="failed",
                expected_value=f"<= {today.isoformat()}",
                actual_value=dob.isoformat(),
                message=f"Date of birth {dob.isoformat()} is in the future.",
            ))
        else:
            checks.append(ValidationCheck(
                check_name="dob_not_future",
                check_category="dates",
                status="passed",
                expected_value=f"<= {today.isoformat()}",
                actual_value=dob.isoformat(),
                message="Date of birth is not in the future.",
            ))
    else:
        checks.append(ValidationCheck(
            check_name="dob_not_future",
            check_category="dates",
            status="skipped",
            message="Date of birth check skipped — field is missing or invalid.",
        ))

    # DOB reasonable age
    if dob and dob <= today:
        age_days = (today - dob).days
        age_years = age_days / 365.25
        if age_years < 0 or age_years > 150:
            checks.append(ValidationCheck(
                check_name="dob_reasonable_age",
                check_category="dates",
                status="failed",
                expected_value="0-150 years",
                actual_value=f"{age_years:.1f} years",
                message=f"Computed age {age_years:.1f} years is outside reasonable range.",
            ))
        elif age_years < 1 or age_years > 120:
            checks.append(ValidationCheck(
                check_name="dob_reasonable_age",
                check_category="dates",
                status="warning",
                expected_value="1-120 years",
                actual_value=f"{age_years:.1f} years",
                message=f"Computed age {age_years:.1f} years is unusual but within limits.",
            ))
        else:
            checks.append(ValidationCheck(
                check_name="dob_reasonable_age",
                check_category="dates",
                status="passed",
                expected_value="1-120 years",
                actual_value=f"{age_years:.1f} years",
                message=f"Computed age {age_years:.1f} years is within reasonable range.",
            ))
    elif dob is None:
        checks.append(ValidationCheck(
            check_name="dob_reasonable_age",
            check_category="dates",
            status="skipped",
            message="Age reasonableness check skipped — date of birth is missing.",
        ))

    # Expiry date
    if expiry:
        grace_cutoff = today - timedelta(days=_RECENT_EXPIRY_GRACE_DAYS)
        if expiry >= today:
            checks.append(ValidationCheck(
                check_name="expiry_not_past",
                check_category="dates",
                status="passed",
                expected_value=f">= {today.isoformat()}",
                actual_value=expiry.isoformat(),
                message="Document has not expired.",
            ))
        elif expiry >= grace_cutoff:
            checks.append(ValidationCheck(
                check_name="expiry_not_past",
                check_category="dates",
                status="warning",
                expected_value=f">= {today.isoformat()}",
                actual_value=expiry.isoformat(),
                message=f"Document expired recently ({expiry.isoformat()}), within {_RECENT_EXPIRY_GRACE_DAYS}-day grace period.",
            ))
        else:
            checks.append(ValidationCheck(
                check_name="expiry_not_past",
                check_category="dates",
                status="failed",
                expected_value=f">= {today.isoformat()}",
                actual_value=expiry.isoformat(),
                message=f"Document expired on {expiry.isoformat()}.",
            ))
    else:
        checks.append(ValidationCheck(
            check_name="expiry_not_past",
            check_category="dates",
            status="skipped",
            message="Expiry date check skipped — field is missing.",
        ))

    # Expiry not too far in the future
    if expiry and expiry >= today:
        max_future = today + timedelta(days=_MAX_PASSPORT_VALIDITY_YEARS * 365)
        if expiry > max_future:
            checks.append(ValidationCheck(
                check_name="expiry_not_too_far",
                check_category="dates",
                status="warning",
                expected_value=f"<= {max_future.isoformat()}",
                actual_value=expiry.isoformat(),
                message=f"Expiry date {expiry.isoformat()} is more than {_MAX_PASSPORT_VALIDITY_YEARS} years in the future.",
            ))
        else:
            checks.append(ValidationCheck(
                check_name="expiry_not_too_far",
                check_category="dates",
                status="passed",
                expected_value=f"<= {max_future.isoformat()}",
                actual_value=expiry.isoformat(),
                message="Expiry date is within reasonable future range.",
            ))
    elif expiry is None:
        checks.append(ValidationCheck(
            check_name="expiry_not_too_far",
            check_category="dates",
            status="skipped",
            message="Expiry future check skipped — field is missing.",
        ))

    # Issue date before expiry
    if issue and expiry:
        if issue < expiry:
            checks.append(ValidationCheck(
                check_name="issue_before_expiry",
                check_category="dates",
                status="passed",
                expected_value=f"issue ({issue.isoformat()}) < expiry ({expiry.isoformat()})",
                actual_value="correct order",
                message="Date of issue is before date of expiry.",
            ))
        else:
            checks.append(ValidationCheck(
                check_name="issue_before_expiry",
                check_category="dates",
                status="failed",
                expected_value=f"issue < expiry",
                actual_value=f"issue={issue.isoformat()}, expiry={expiry.isoformat()}",
                message=f"Date of issue ({issue.isoformat()}) is not before date of expiry ({expiry.isoformat()}).",
            ))
    else:
        checks.append(ValidationCheck(
            check_name="issue_before_expiry",
            check_category="dates",
            status="skipped",
            message="Issue/expiry order check skipped — one or both dates are missing.",
        ))

    return checks


# ---------------------------------------------------------------------------
# Category 4: MRZ checks
# ---------------------------------------------------------------------------

def _check_mrz(doc: dict, mrz_parsed: dict | None) -> list[ValidationCheck]:
    """Check MRZ integrity and consistency with extracted fields."""
    checks = []

    mrz_line_1 = doc.get("mrz_line_1") or ""
    mrz_line_2 = doc.get("mrz_line_2") or ""

    # MRZ structure
    line1_valid = bool(_MRZ_LINE_PATTERN.match(mrz_line_1))
    line2_valid = bool(_MRZ_LINE_PATTERN.match(mrz_line_2))
    if mrz_line_1 and mrz_line_2:
        if line1_valid and line2_valid:
            checks.append(ValidationCheck(
                check_name="mrz_structure",
                check_category="mrz",
                status="passed",
                message="MRZ lines are well-formed (44 characters, valid character set).",
            ))
        else:
            details = []
            if not line1_valid:
                details.append(f"Line 1 length={len(mrz_line_1)}")
            if not line2_valid:
                details.append(f"Line 2 length={len(mrz_line_2)}")
            checks.append(ValidationCheck(
                check_name="mrz_structure",
                check_category="mrz",
                status="failed",
                actual_value="; ".join(details),
                expected_value="Two lines of 44 chars [A-Z0-9<]",
                message=f"MRZ structure is invalid: {'; '.join(details)}.",
            ))
    else:
        checks.append(ValidationCheck(
            check_name="mrz_structure",
            check_category="mrz",
            status="skipped",
            message="MRZ structure check skipped — MRZ lines not available.",
        ))

    # MRZ check digits
    if mrz_parsed:
        all_valid = mrz_parsed.get("all_checks_valid", False)
        check_digits = mrz_parsed.get("check_digits", {})
        if all_valid:
            checks.append(ValidationCheck(
                check_name="mrz_check_digits",
                check_category="mrz",
                status="passed",
                message="All MRZ check digits are valid.",
            ))
        else:
            failed_fields = [
                name for name, info in check_digits.items()
                if isinstance(info, dict) and not info.get("valid", True)
            ]
            checks.append(ValidationCheck(
                check_name="mrz_check_digits",
                check_category="mrz",
                status="failed",
                actual_value=f"Failed: {', '.join(failed_fields)}" if failed_fields else "invalid",
                expected_value="all valid",
                message=f"MRZ check digit validation failed for: {', '.join(failed_fields)}." if failed_fields else "MRZ check digit validation failed.",
            ))
    else:
        checks.append(ValidationCheck(
            check_name="mrz_check_digits",
            check_category="mrz",
            status="skipped",
            message="MRZ check digit validation skipped — parsed MRZ data not available.",
        ))

    # MRZ field consistency checks
    if mrz_parsed:
        # Document number match
        mrz_doc_num = (mrz_parsed.get("document_number") or "").strip().upper()
        ext_doc_num = (doc.get("document_number") or "").strip().upper()
        if mrz_doc_num and ext_doc_num:
            match = mrz_doc_num == ext_doc_num
            checks.append(ValidationCheck(
                check_name="mrz_document_number_match",
                check_category="mrz",
                status="passed" if match else "failed",
                expected_value=mrz_doc_num,
                actual_value=ext_doc_num,
                message=(
                    "MRZ document number matches extracted document number."
                    if match else
                    f"MRZ document number '{mrz_doc_num}' does not match extracted '{ext_doc_num}'."
                ),
            ))
        else:
            checks.append(ValidationCheck(
                check_name="mrz_document_number_match",
                check_category="mrz",
                status="skipped",
                message="MRZ document number match skipped — one or both values missing.",
            ))

        # Nationality match
        mrz_nat = (mrz_parsed.get("nationality") or "").strip().upper()
        ext_nat = (doc.get("nationality") or "").strip().upper()
        if mrz_nat and ext_nat:
            match = mrz_nat == ext_nat
            checks.append(ValidationCheck(
                check_name="mrz_nationality_match",
                check_category="mrz",
                status="passed" if match else "failed",
                expected_value=mrz_nat,
                actual_value=ext_nat,
                message=(
                    "MRZ nationality matches extracted nationality."
                    if match else
                    f"MRZ nationality '{mrz_nat}' does not match extracted '{ext_nat}'."
                ),
            ))
        else:
            checks.append(ValidationCheck(
                check_name="mrz_nationality_match",
                check_category="mrz",
                status="skipped",
                message="MRZ nationality match skipped — one or both values missing.",
            ))

        # Name match (surname, case-insensitive)
        mrz_surname = (mrz_parsed.get("surname") or "").strip().upper()
        ext_surname = (doc.get("surname") or "").strip().upper()
        if mrz_surname and ext_surname:
            match = mrz_surname == ext_surname
            checks.append(ValidationCheck(
                check_name="mrz_name_match",
                check_category="mrz",
                status="passed" if match else "failed",
                expected_value=mrz_surname,
                actual_value=ext_surname,
                message=(
                    "MRZ surname matches extracted surname."
                    if match else
                    f"MRZ surname '{mrz_surname}' does not match extracted '{ext_surname}'."
                ),
            ))
        else:
            checks.append(ValidationCheck(
                check_name="mrz_name_match",
                check_category="mrz",
                status="skipped",
                message="MRZ name match skipped — one or both values missing.",
            ))
    else:
        # No MRZ parsed data — skip all field consistency checks
        for check_name in ("mrz_document_number_match", "mrz_nationality_match", "mrz_name_match"):
            checks.append(ValidationCheck(
                check_name=check_name,
                check_category="mrz",
                status="skipped",
                message=f"{check_name} skipped — parsed MRZ data not available.",
            ))

    return checks


# ---------------------------------------------------------------------------
# Category 5: Reference database checks
# ---------------------------------------------------------------------------

_BAD_STATUSES = {"stolen", "revoked", "lost", "watchlist"}


def _check_reference(doc: dict, reference: dict | None) -> list[ValidationCheck]:
    """Check document against reference database records."""
    checks = []

    if reference is None:
        checks.append(ValidationCheck(
            check_name="reference_lookup",
            check_category="database",
            status="skipped",
            message="Document not found in reference database — lookup skipped.",
        ))
        # Skip all dependent checks
        for name in ("reference_status", "reference_holder_match", "reference_dob_match"):
            checks.append(ValidationCheck(
                check_name=name,
                check_category="database",
                status="skipped",
                message=f"{name} skipped — no reference document found.",
            ))
        return checks

    # Reference found
    ref_status = (reference.get("status") or "").lower()
    checks.append(ValidationCheck(
        check_name="reference_lookup",
        check_category="database",
        status="passed",
        actual_value=ref_status,
        message=f"Document found in reference database with status: {ref_status}.",
    ))

    # Reference status
    if ref_status == "valid":
        checks.append(ValidationCheck(
            check_name="reference_status",
            check_category="database",
            status="passed",
            expected_value="valid",
            actual_value=ref_status,
            message="Reference document status is valid.",
        ))
    elif ref_status == "expired":
        checks.append(ValidationCheck(
            check_name="reference_status",
            check_category="database",
            status="warning",
            expected_value="valid",
            actual_value=ref_status,
            message="Reference document is marked as expired.",
        ))
    elif ref_status in _BAD_STATUSES:
        checks.append(ValidationCheck(
            check_name="reference_status",
            check_category="database",
            status="failed",
            expected_value="valid",
            actual_value=ref_status,
            message=f"ALERT: Reference document is marked as {ref_status}.",
        ))
    else:
        checks.append(ValidationCheck(
            check_name="reference_status",
            check_category="database",
            status="warning",
            expected_value="valid",
            actual_value=ref_status,
            message=f"Reference document has unexpected status: {ref_status}.",
        ))

    # Holder name match
    ref_surname = (reference.get("holder_surname") or "").strip().upper()
    ext_surname = (doc.get("surname") or "").strip().upper()
    ref_given = (reference.get("holder_given_names") or "").strip().upper()
    ext_given = (doc.get("given_names") or "").strip().upper()

    if ref_surname or ref_given:
        surname_match = ref_surname == ext_surname if ref_surname else True
        given_match = ref_given == ext_given if ref_given else True
        if surname_match and given_match:
            checks.append(ValidationCheck(
                check_name="reference_holder_match",
                check_category="database",
                status="passed",
                expected_value=f"{ref_surname}, {ref_given}",
                actual_value=f"{ext_surname}, {ext_given}",
                message="Holder name matches reference database.",
            ))
        else:
            checks.append(ValidationCheck(
                check_name="reference_holder_match",
                check_category="database",
                status="warning",
                expected_value=f"{ref_surname}, {ref_given}",
                actual_value=f"{ext_surname}, {ext_given}",
                message=f"Holder name mismatch: reference='{ref_surname}, {ref_given}', extracted='{ext_surname}, {ext_given}'.",
            ))
    else:
        checks.append(ValidationCheck(
            check_name="reference_holder_match",
            check_category="database",
            status="skipped",
            message="Holder name match skipped — reference has no name data.",
        ))

    # DOB match
    ref_dob = _parse_date_value(reference.get("date_of_birth"))
    ext_dob = _parse_date_value(doc.get("date_of_birth"))
    if ref_dob and ext_dob:
        match = ref_dob == ext_dob
        checks.append(ValidationCheck(
            check_name="reference_dob_match",
            check_category="database",
            status="passed" if match else "failed",
            expected_value=ref_dob.isoformat(),
            actual_value=ext_dob.isoformat(),
            message=(
                "Date of birth matches reference database."
                if match else
                f"Date of birth mismatch: reference={ref_dob.isoformat()}, extracted={ext_dob.isoformat()}."
            ),
        ))
    else:
        checks.append(ValidationCheck(
            check_name="reference_dob_match",
            check_category="database",
            status="skipped",
            message="DOB match skipped — one or both DOB values missing.",
        ))

    return checks
