"""
VeriGate Backend — MRZ Parser (ICAO 9303 TD3)

Parses the Machine Readable Zone of passport documents (TD3 format).
TD3 passports have two lines of 44 characters each.

Line 1: P<CTYSURNAME<<GIVEN<NAMES<<<<<<<<<<<<<<<<<<<<<<
Line 2: DOC_NUM_0 CTY DOB_0 S EXPIRY_0 PERSONAL______0 COMPOSITE

Check digits use the ICAO 7-3-1 weighted modulo-10 algorithm.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MrzCheckResult:
    """Result of a single MRZ check-digit validation."""
    field_name: str
    expected: int
    computed: int
    is_valid: bool


@dataclass
class MrzResult:
    """Parsed TD3 MRZ data."""
    # Raw lines
    line1: str
    line2: str

    # Parsed fields from line 1
    document_code: str = ""
    issuing_country: str = ""
    surname: str = ""
    given_names: str = ""

    # Parsed fields from line 2
    document_number: str = ""
    nationality: str = ""
    date_of_birth: str = ""      # YYMMDD
    sex: str = ""
    date_of_expiry: str = ""     # YYMMDD
    personal_number: str = ""

    # Parsed dates
    date_of_birth_parsed: date | None = None
    date_of_expiry_parsed: date | None = None

    # Check digit results
    check_results: list[MrzCheckResult] = field(default_factory=list)
    all_checks_valid: bool = False


# ---------------------------------------------------------------------------
# Character value mapping (ICAO 9303)
# ---------------------------------------------------------------------------

def _char_value(ch: str) -> int:
    """Convert an MRZ character to its numeric value.

    0-9 → 0-9, A-Z → 10-35, '<' (filler) → 0.
    """
    if ch == "<":
        return 0
    if ch.isdigit():
        return int(ch)
    if ch.isalpha():
        return ord(ch.upper()) - ord("A") + 10
    return 0


# ---------------------------------------------------------------------------
# Check digit computation
# ---------------------------------------------------------------------------

_WEIGHTS = [7, 3, 1]


def compute_check_digit(data: str) -> int:
    """Compute the ICAO 7-3-1 weighted modulo-10 check digit.

    Args:
        data: The MRZ field string to compute the check digit for.

    Returns:
        The check digit (0-9).
    """
    total = 0
    for i, ch in enumerate(data):
        total += _char_value(ch) * _WEIGHTS[i % 3]
    return total % 10


# ---------------------------------------------------------------------------
# MRZ line detection
# ---------------------------------------------------------------------------

# MRZ TD3: two lines of exactly 44 characters, uppercase + digits + '<'
_MRZ_LINE_PATTERN = re.compile(r"[A-Z0-9<]{44}")


def detect_mrz_lines(raw_text: str) -> tuple[str, str] | None:
    """Detect the two MRZ lines from raw OCR text.

    Looks for lines matching the TD3 pattern (44 chars of A-Z, 0-9, '<').
    Line 1 should start with 'P<' for passports.

    Args:
        raw_text: Full OCR text output.

    Returns:
        Tuple of (line1, line2) if found, None otherwise.
    """
    # Clean up the text — normalize whitespace, fix common OCR errors
    cleaned = raw_text.upper()

    # Find all potential MRZ lines (44-char sequences)
    candidates = _MRZ_LINE_PATTERN.findall(cleaned)

    if len(candidates) < 2:
        # Try harder: look line by line, stripping spaces
        lines = cleaned.split("\n")
        candidates = []
        for line in lines:
            stripped = line.replace(" ", "").strip()
            if len(stripped) == 44 and _MRZ_LINE_PATTERN.match(stripped):
                candidates.append(stripped)

    if len(candidates) < 2:
        return None

    # Find the passport MRZ: line 1 starts with 'P<'
    for i in range(len(candidates) - 1):
        if candidates[i].startswith("P"):
            return (candidates[i], candidates[i + 1])

    # Fallback: return last two candidates (MRZ is at the bottom)
    return (candidates[-2], candidates[-1])


# ---------------------------------------------------------------------------
# MRZ parsing
# ---------------------------------------------------------------------------

def _parse_mrz_date(yymmdd: str) -> date | None:
    """Parse an MRZ date (YYMMDD) into a Python date.

    Uses a pivot: years 00-30 → 2000-2030, years 31-99 → 1931-1999.
    """
    if len(yymmdd) != 6 or not yymmdd.isdigit():
        return None

    try:
        yy = int(yymmdd[0:2])
        mm = int(yymmdd[2:4])
        dd = int(yymmdd[4:6])

        # Pivot year for century
        year = 2000 + yy if yy <= 30 else 1900 + yy

        return date(year, mm, dd)
    except ValueError:
        return None


def _clean_name(raw: str) -> str:
    """Convert MRZ name field to human-readable form.

    'SMITH<<JAMES<EDWARD' → 'JAMES EDWARD' (given names)
    """
    return raw.replace("<", " ").strip()


def parse_td3_mrz(line1: str, line2: str) -> MrzResult:
    """Parse a TD3 (passport) MRZ from two 44-character lines.

    Args:
        line1: First MRZ line (44 chars).
        line2: Second MRZ line (44 chars).

    Returns:
        MrzResult with all parsed fields and check digit validations.
    """
    result = MrzResult(line1=line1, line2=line2)

    # --- Line 1 ---
    # Positions: [0:1]=doc_code, [1:2]=doc_type_extra, [2:5]=country
    # [5:44]=name (SURNAME<<GIVEN<NAMES)
    result.document_code = line1[0:2].replace("<", "")
    result.issuing_country = line1[2:5].replace("<", "")

    name_field = line1[5:44]
    name_parts = name_field.split("<<", 1)
    result.surname = _clean_name(name_parts[0])
    result.given_names = _clean_name(name_parts[1]) if len(name_parts) > 1 else ""

    # --- Line 2 ---
    # [0:9]=doc_number, [9]=check_digit, [10:13]=nationality
    # [13:19]=dob, [19]=check_digit, [20]=sex
    # [21:27]=expiry, [27]=check_digit
    # [28:42]=personal_number, [42]=check_digit
    # [43]=composite_check_digit
    result.document_number = line2[0:9].replace("<", "").strip()
    result.nationality = line2[10:13].replace("<", "")
    result.date_of_birth = line2[13:19]
    result.sex = line2[20:21]
    result.date_of_expiry = line2[21:27]
    result.personal_number = line2[28:42].replace("<", "").strip()

    # Parse dates
    result.date_of_birth_parsed = _parse_mrz_date(result.date_of_birth)
    result.date_of_expiry_parsed = _parse_mrz_date(result.date_of_expiry)

    # --- Check digits ---
    checks = []

    # 1. Document number check digit (position 9)
    doc_num_cd = int(line2[9]) if line2[9].isdigit() else -1
    doc_num_computed = compute_check_digit(line2[0:9])
    checks.append(MrzCheckResult(
        field_name="document_number",
        expected=doc_num_cd,
        computed=doc_num_computed,
        is_valid=(doc_num_cd == doc_num_computed),
    ))

    # 2. Date of birth check digit (position 19)
    dob_cd = int(line2[19]) if line2[19].isdigit() else -1
    dob_computed = compute_check_digit(line2[13:19])
    checks.append(MrzCheckResult(
        field_name="date_of_birth",
        expected=dob_cd,
        computed=dob_computed,
        is_valid=(dob_cd == dob_computed),
    ))

    # 3. Date of expiry check digit (position 27)
    exp_cd = int(line2[27]) if line2[27].isdigit() else -1
    exp_computed = compute_check_digit(line2[21:27])
    checks.append(MrzCheckResult(
        field_name="date_of_expiry",
        expected=exp_cd,
        computed=exp_computed,
        is_valid=(exp_cd == exp_computed),
    ))

    # 4. Personal number check digit (position 42)
    pn_cd = int(line2[42]) if line2[42].isdigit() else -1
    pn_computed = compute_check_digit(line2[28:42])
    checks.append(MrzCheckResult(
        field_name="personal_number",
        expected=pn_cd,
        computed=pn_computed,
        is_valid=(pn_cd == pn_computed),
    ))

    # 5. Composite check digit (position 43)
    # Covers: doc_number + cd + nationality is excluded + dob + cd + sex excluded + expiry + cd + personal + cd
    # Actually per ICAO: positions 0-9 + 13-19 + 21-42 (excludes nationality at 10-12 and sex at 20)
    composite_data = line2[0:10] + line2[13:20] + line2[21:43]
    comp_cd = int(line2[43]) if line2[43].isdigit() else -1
    comp_computed = compute_check_digit(composite_data)
    checks.append(MrzCheckResult(
        field_name="composite",
        expected=comp_cd,
        computed=comp_computed,
        is_valid=(comp_cd == comp_computed),
    ))

    result.check_results = checks
    result.all_checks_valid = all(c.is_valid for c in checks)

    return result
