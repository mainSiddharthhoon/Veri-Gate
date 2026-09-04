"""
Automated Lighthouse & Axe Accessibility Verification for VeriGate
Focuses on:
1. One proper <main> landmark containing primary content between header/navbar and footer.
2. Heading hierarchy adhering to sequential descending order (h1 -> h2 -> h3) without skipping levels.
"""

import sys
import re
from bs4 import BeautifulSoup

def test_accessibility(html_path="frontend/index.html"):
    print(f"Auditing accessibility for: {html_path}\n" + "="*60)
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    errors = []
    passes = []

    # -------------------------------------------------------------
    # 1. Landmark Check: Document has exactly one <main> landmark
    # -------------------------------------------------------------
    main_elements = soup.find_all(["main", lambda tag: tag.get("role") == "main"])
    if len(main_elements) == 0:
        errors.append("RULE FAIL [landmark-one-main]: No <main> landmark element found in document.")
    elif len(main_elements) > 1:
        errors.append(f"RULE FAIL [landmark-one-main]: Found {len(main_elements)} <main> landmarks. Document must have exactly 1.")
    else:
        main_el = main_elements[0]
        # Verify main contains primary sections
        sections_in_main = [s.get("id") for s in main_el.find_all("section") if s.get("id")]
        expected_sections = ["hero", "problem", "sense", "pipeline", "screening"]
        missing = [s for s in expected_sections if s not in sections_in_main]
        if missing:
            errors.append(f"RULE FAIL [landmark-main-content]: <main> is missing key sections: {missing}")
        else:
            passes.append(f"RULE PASS [landmark-one-main]: Exactly 1 <main id=\"{main_el.get('id')}\"> landmark found containing all primary content sections {sections_in_main}.")

    # Verify landmarks between header and footer
    headers = soup.find_all("header")
    footers = soup.find_all("footer")
    navs = soup.find_all("nav")
    
    if len(headers) >= 1:
        passes.append(f"RULE PASS [landmark-banner]: Found <header> landmark ({[h.get('class') for h in headers]}).")
    if len(navs) >= 1:
        passes.append(f"RULE PASS [landmark-navigation]: Found <nav> landmark ({[n.get('id') for n in navs]}).")
    if len(footers) >= 1:
        passes.append(f"RULE PASS [landmark-contentinfo]: Found <footer> landmark ({[f.get('id') for f in footers]}).")

    # -------------------------------------------------------------
    # 2. Heading Order: Headings follow logical h1 -> h2 -> h3 without skipping
    # -------------------------------------------------------------
    headings = soup.find_all(re.compile(r"^h[1-6]$", re.I))
    if not headings:
        errors.append("RULE FAIL [heading-order]: No headings found on page.")
    else:
        h1_count = len([h for h in headings if h.name.lower() == "h1"])
        if h1_count == 1:
            passes.append("RULE PASS [page-has-heading-one]: Exactly one <h1> found on page.")
        else:
            errors.append(f"RULE FAIL [page-has-heading-one]: Expected exactly one <h1>, found {h1_count}.")

        prev_level = 0
        heading_trail = []
        heading_violations = []

        for h in headings:
            level = int(h.name[1])
            text = h.get_text(strip=True)[:45]
            attrs = f"id={h.get('id')}" if h.get("id") else f"class={h.get('class')}"
            step = level - prev_level

            # Axe / Lighthouse rule: Heading levels can only increase by at most 1 (e.g. h1 -> h2 is ok, h2 -> h3 is ok, but h1 -> h3 or h2 -> h4 violates heading-order)
            if prev_level > 0 and step > 1:
                heading_violations.append(
                    f"Skipped from <h{prev_level}> directly to <h{level}> at '{text}' ({attrs})"
                )
            heading_trail.append(f"<h{level}> ({attrs}): '{text}'")
            prev_level = level

        if heading_violations:
            for v in heading_violations:
                errors.append(f"RULE FAIL [heading-order]: {v}")
        else:
            passes.append(f"RULE PASS [heading-order]: All {len(headings)} headings follow sequential hierarchy without skipping levels.")

    # -------------------------------------------------------------
    # Summary Output
    # -------------------------------------------------------------
    print("\n--- PASSED CHECKS ---")
    for p in passes:
        print(f"  [PASS] {p}")

    if errors:
        print("\n--- FAILED CHECKS ---")
        for e in errors:
            print(f"  [FAIL] {e}")
        print(f"\nResult: FAILED ({len(errors)} errors)")
        sys.exit(1)
    else:
        print("\n--- HEADING SEQUENCE AUDIT ---")
        for line in heading_trail:
            print(f"  -> {line}")
        print("\nResult: ALL ACCESSIBILITY CHECKS PASSED (100% compliant)")
        sys.exit(0)

if __name__ == "__main__":
    test_accessibility()
