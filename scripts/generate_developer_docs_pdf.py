"""
VeriGate Developer Documentation PDF Generator
Generates a publication-grade, developer-oriented technical PDF manual
based strictly on the grounded 22-section VeriGate architecture documentation.
Uses fpdf2 with Latin-1 safe ASCII/Latin formatting.
"""

import sys
from pathlib import Path
from fpdf import FPDF


def clean_text(text: str) -> str:
    """Replaces Unicode characters not supported by standard Latin-1 Helvetica."""
    replacements = {
        "\u2014": " -- ",  # em-dash
        "\u2013": "-",     # en-dash
        "\u2018": "'",     # left single quote
        "\u2019": "'",     # right single quote
        "\u201c": '"',     # left double quote
        "\u201d": '"',     # right double quote
        "\u2022": "-",     # bullet point
        "\u2192": "->",    # right arrow
        "\u2190": "<-",    # left arrow
        "\u2193": "|",     # down arrow
        "\u2502": "|",     # box vertical
        "\u2500": "-",     # box horizontal
        "\u250c": "+",     # box top-left
        "\u2510": "+",     # box top-right
        "\u2514": "+",     # box bottom-left
        "\u2518": "+",     # box bottom-right
        "\u251c": "+",     # box vertical-right
        "\u2524": "+",     # box vertical-left
        "\u252c": "+",     # box horizontal-down
        "\u2534": "+",     # box horizontal-up
        "\u253c": "+",     # box cross
        "\u25ba": ">",
        "\u25b6": ">",
        "\u00a0": " ",     # non-breaking space
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    # Filter any remaining non-latin1 characters
    return text.encode("latin-1", errors="replace").decode("latin-1")


class VeriGatePDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=16)
        self.set_margins(16, 16, 16)

    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "B", 7.8)
            self.set_text_color(100, 116, 139)  # Slate 500
            self.cell(110, 6, clean_text("VERIGATE -- IDENTITY VERIFICATION INTELLIGENCE"), align="L")
            self.cell(68, 6, "DEVELOPER DOCUMENTATION", align="R", new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(226, 232, 240)  # Slate 200
            self.set_line_width(0.3)
            self.line(16, 15, 194, 15)
            self.ln(3)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(148, 163, 184)  # Slate 400
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.line(16, 284, 194, 284)
        self.cell(120, 5, "VeriGate Identity Verification Intelligence | Developer Reference Manual", align="L")
        page_str = f"Page {self.page_no()} of {{nb}}"
        self.cell(58, 5, page_str, align="R")

    def section_title(self, num_str, title_str):
        if self.get_y() > 248:
            self.add_page()
        self.ln(3)
        self.set_fill_color(15, 23, 42)  # Dark Navy Slate #0f172a
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 9.8)
        display_title = f"  {num_str}. {title_str.upper()}" if num_str else f"  {title_str.upper()}"
        self.cell(0, 7.0, clean_text(display_title), fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def sub_title(self, title_str):
        if self.get_y() > 255:
            self.add_page()
        self.set_font("Helvetica", "B", 9.0)
        self.set_text_color(225, 29, 72)  # Crimson Rose #e11d48
        self.cell(0, 5.0, clean_text(title_str), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_p(self, text):
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(51, 65, 85)  # Slate 700
        self.multi_cell(0, 4.2, clean_text(text))
        self.ln(1.5)

    def bullet_point(self, prefix, text=""):
        if self.get_y() > 260:
            self.add_page()
        self.set_font("Helvetica", "B", 8.4)
        self.set_text_color(15, 23, 42)
        self.cell(5, 4.0, "- ")
        if prefix:
            self.cell(self.get_string_width(clean_text(prefix)) + 1, 4.0, clean_text(prefix))
        if text:
            self.set_font("Helvetica", "", 8.4)
            self.set_text_color(51, 65, 85)
            rem_w = 178 - 5 - (self.get_string_width(clean_text(prefix)) + 1 if prefix else 0)
            self.multi_cell(rem_w, 4.0, clean_text(text))
        else:
            self.ln(4.0)
        self.ln(0.8)

    def callout_box(self, title, text, bg_r=248, bg_g=250, bg_b=252, border_r=225, border_g=29, border_b=72):
        if self.get_y() > 245:
            self.add_page()
        self.ln(1.5)
        x = self.get_x()
        y0 = self.get_y()

        self.set_fill_color(bg_r, bg_g, bg_b)
        self.set_draw_color(border_r, border_g, border_b)

        # Print content indented
        self.set_x(x + 5)
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(border_r, border_g, border_b)
        self.cell(173, 4.5, clean_text(title), new_x="LMARGIN", new_y="NEXT")

        self.set_x(x + 5)
        self.set_font("Helvetica", "", 8.2)
        self.set_text_color(71, 85, 105)
        self.multi_cell(173, 4.0, clean_text(text))
        
        y1 = self.get_y() + 1.5
        box_h = y1 - y0

        # Draw left highlight bar
        self.set_line_width(1.2)
        self.line(x + 1, y0, x + 1, y1)
        self.set_line_width(0.2)
        self.set_y(y1 + 1.5)

    def code_box(self, code_str):
        if self.get_y() > 240:
            self.add_page()
        self.ln(1)
        lines = code_str.strip().split("\n")
        x = self.get_x()
        y0 = self.get_y()

        # Background calculation
        line_height = 3.6
        total_h = len(lines) * line_height + 4
        if y0 + total_h > 275:
            self.add_page()
            y0 = self.get_y()

        self.set_fill_color(241, 245, 249)  # Slate 100
        self.set_draw_color(203, 213, 225)  # Slate 300
        self.rect(x, y0, 178, total_h, style="FD")

        self.set_xy(x + 3, y0 + 2)
        self.set_font("Courier", "", 7.6)
        self.set_text_color(30, 41, 59)
        for line in lines:
            self.cell(172, line_height, clean_text(line), new_x="LMARGIN", new_y="NEXT")
            self.set_x(x + 3)

        self.set_y(y0 + total_h + 2)

    def table_row(self, col_widths, texts, is_header=False):
        if self.get_y() > 265:
            self.add_page()
        if is_header:
            self.set_fill_color(30, 41, 59)
            self.set_text_color(255, 255, 255)
            self.set_font("Helvetica", "B", 7.8)
        else:
            self.set_fill_color(248, 250, 252)
            self.set_text_color(51, 65, 85)
            self.set_font("Helvetica", "", 7.6)

        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.2)
        for w, t in zip(col_widths, texts):
            self.cell(w, 5.2, clean_text(f" {t}"), border=1, fill=True)
        self.ln(5.2)


def build_pdf(output_path="VeriGate_Developer_Documentation.pdf"):
    pdf = VeriGatePDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # ================= COVER BANNER =================
    pdf.set_fill_color(15, 23, 42)  # Navy / Slate 900
    pdf.rect(16, 16, 178, 36, style="F")

    pdf.set_xy(20, 20)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 7.5, clean_text("VERIGATE -- IDENTITY VERIFICATION INTELLIGENCE"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(20)
    pdf.set_font("Helvetica", "B", 9.2)
    pdf.set_text_color(244, 63, 94)  # Rose 500
    pdf.cell(0, 5.0, "Developer-Oriented Identity Verification Prototype Technical Documentation", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(20)
    pdf.set_font("Helvetica", "", 7.8)
    pdf.set_text_color(148, 163, 184)  # Slate 400
    pdf.cell(0, 4.8, "Evidence-First Screening Pipeline | Deterministic Validation | Image Forensics | Multimodal AI Arbitration", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(56)

    # ================= INTRO & PROTOTYPE STATUS =================
    pdf.body_p(
        "VeriGate is a developer-oriented identity verification prototype that combines document processing, "
        "deterministic validation, image forensics, biometric face comparison, and multimodal AI reasoning into "
        "a single screening workflow."
    )

    pdf.callout_box(
        "PROTOTYPE STATUS & BOUNDARIES",
        "VeriGate is a hackathon/MVP system validated primarily with synthetic test fixtures. "
        "It is not a production border-security deployment and does not have access to real government watchlists, "
        "passport PKI/NFC chips, or physical document security inspection hardware."
    )

    # ================= SECTION 1: PROBLEM =================
    pdf.section_title("1", "Problem")
    pdf.body_p(
        "Identity screening can involve passports, national IDs, permits, visas, and other credentials. "
        "Manual inspection can be slow and inconsistent, while isolated OCR or face checks may fail to "
        "expose contradictions across different evidence sources."
    )
    pdf.body_p("VeriGate addresses this with an evidence-first pipeline:")

    pipeline_diagram = (
        "Document + Presented Person\n"
        "            |\n"
        "            v\n"
        "Input Qualification\n"
        "            |\n"
        "            v\n"
        "OCR / Field Extraction\n"
        "            |\n"
        "            v\n"
        "MRZ Validation (when applicable)\n"
        "            |\n"
        "            v\n"
        "Deterministic Document + Date Validation\n"
        "            |\n"
        "            v\n"
        "ELA / Tampering Evidence\n"
        "            |\n"
        "            v\n"
        "Face Verification\n"
        "            |\n"
        "            v\n"
        "Gemma Multimodal Reasoning\n"
        "            |\n"
        "            v\n"
        "Risk Score + Decision + Explanation"
    )
    pdf.code_box(pipeline_diagram)

    # ================= SECTION 2: CORE ARCHITECTURE =================
    pdf.section_title("2", "Core Architecture")
    pdf.body_p("VeriGate uses a 7-stage sequential evidence pipeline.")

    pdf.sub_title("Stage 1 -- Input Qualification")
    pdf.body_p(
        "A multimodal vision model inspects both submitted images before expensive processing begins. "
        "It checks whether the document and presented-person image are suitable for the screening workflow "
        "and can reject irrelevant or unusable inputs early."
    )

    pdf.sub_title("Stage 2 -- OCR and Field Extraction")
    pdf.body_p(
        "The document is processed to extract structured identity information such as name, document number, "
        "nationality, issuing country/authority, date of birth, sex/gender, date of issue (when present), and "
        "date of expiry (when present). The active project uses PaddleOCR/PP-OCR together with OpenCV, Pillow, "
        "and NumPy for image processing."
    )

    pdf.sub_title("Stage 3 -- MRZ Validation")
    pdf.body_p(
        "For documents containing a Machine Readable Zone, VeriGate parses the MRZ and recalculates its check digits. "
        "The stage is conditional: documents without an MRZ skip MRZ-specific checks rather than automatically failing."
    )

    pdf.sub_title("Stage 4 -- Deterministic Document and Temporal Validation")
    pdf.body_p(
        "This stage is rule-based. Python calculates objective evidence including: current date, date-of-birth validity, "
        "calculated age, future DOB detection, issue date, expiry date, expired/not-expired status, days until/since expiry, "
        "issue/expiry relationship, and issue date in the future."
    )
    pdf.callout_box(
        "CENTRAL ARCHITECTURAL RULE",
        "Python calculates deterministic date facts; Gemma interprets them but must not override them.\n"
        "Missing issue or expiry dates are represented as unavailable/null and are not automatically treated as invalid "
        "unless the document type requires the field.",
        border_r=15, border_g=23, border_b=42
    )

    pdf.sub_title("Stage 5 -- Tampering Forensics")
    pdf.body_p(
        "VeriGate performs image-based forensic analysis using Error Level Analysis (ELA). The document is recompressed, "
        "the original and recompressed images are compared, pixel residuals and variance are calculated, and a heatmap "
        "evidence artifact is produced. ELA is treated as supporting forensic evidence, not as a standalone authenticity proof."
    )

    pdf.sub_title("Stage 6 -- Biometric Face Verification")
    pdf.body_p(
        "The document portrait is compared with the presented person's image using DeepFace / Facenet512 facial embeddings "
        "and cosine-distance comparison. The result is returned as match, mismatch, or inconclusive evidence. "
        "If biometric evidence is unavailable or the biometric stage fails, the reasoning layer is instructed not to invent a match."
    )

    pdf.sub_title("Stage 7 -- Gemma AI Arbitration")
    pdf.body_p(
        "Gemma receives the available evidence from the preceding stages, including images, OCR/MRZ results, deterministic "
        "date/age evidence, tampering evidence, and biometric evidence. It produces a structured assessment containing "
        "validity, consistency, biometric status, tampering concern, risk score, risk level, decision, explanation, and risk factors."
    )
    pdf.code_box("Normal decisions are:\nAPPROVE\nREVIEW\nREJECT")

    # ================= SECTION 3: EVIDENCE PHILOSOPHY =================
    pdf.section_title("3", "Evidence Philosophy")
    pdf.callout_box(
        "THE ARCHITECTURAL PRINCIPLE",
        "Specialized systems produce evidence. AI interprets the combined evidence.",
        border_r=15, border_g=23, border_b=42
    )
    pdf.body_p("For example:")
    evidence_flow = (
        "OCR               -> DOB = 1985-03-15\n"
        "Python validation -> Age = 41\n"
        "MRZ               -> checksum = valid\n"
        "Face verification -> distance = 0.217\n"
        "ELA               -> no significant anomaly\n"
        "Gemma             -> cross-evidence interpretation\n"
        "                  -> decision + explanation"
    )
    pdf.code_box(evidence_flow)
    pdf.body_p(
        "This reduces the amount of deterministic work delegated to the language model and makes the system "
        "easier to debug and explain."
    )

    # ================= SECTION 4: AI PROVIDER ARCHITECTURE =================
    pdf.section_title("4", "AI Provider Architecture")
    pdf.body_p("The AI layer is provider-configurable. The normal preference is:")
    provider_flow = (
        "Google AI Studio -- Gemma 4 31B\n"
        "            |\n"
        "            v\n"
        "Ollama Vision fallback\n"
        "            |\n"
        "            v\n"
        "OpenRouter fallback"
    )
    pdf.code_box(provider_flow)
    pdf.body_p(
        "The provider is selected through configuration rather than hardcoded into the rest of the pipeline. "
        "This also makes a future migration to a strong local/on-prem multimodal model possible without rebuilding "
        "the upstream verification stages."
    )

    # ================= SECTION 5: DATABASE AND EVIDENCE MODEL =================
    pdf.section_title("5", "Database and Evidence Model")
    pdf.body_p("A screening run is represented by a central screening session with linked evidence records:")
    db_tree = (
        "screening_session\n"
        "      |\n"
        "      +-- document\n"
        "      +-- OCR result\n"
        "      +-- validation result\n"
        "      |      +-- validation checks\n"
        "      +-- tampering analysis\n"
        "      |      +-- tampering signals\n"
        "      +-- face verification\n"
        "      +-- risk assessment\n"
        "             +-- risk factors"
    )
    pdf.code_box(db_tree)
    pdf.body_p("The database/reference layer can support known-good reference records and future watchlist integrations.")

    pdf.sub_title("Reference / Watchlist Scope")
    pdf.body_p(
        "Real blacklist/watchlist detection requires authoritative external datasets and appropriate production query/access "
        "controls. The hackathon prototype uses synthetic/reference records and does not claim access to real border-security watchlists."
    )
    pdf.body_p(
        "Likewise, detecting repeated identities across a population requires historical biometric/identity data and cross-session "
        "matching infrastructure; that is a future extension rather than a demonstrated production capability."
    )

    # ================= SECTION 6: API FLOW =================
    pdf.section_title("6", "API Flow")
    pdf.body_p("The current frontend screening flow uses the following backend endpoints:")
    api_flow_chart = (
        "POST /api/ocr/extract\n"
        "        |\n"
        "        v\n"
        "Input qualification + OCR/session creation\n"
        "        |\n"
        "        v\n"
        "POST /api/face/verify\n"
        "        |\n"
        "        v\n"
        "Face verification\n"
        "        |\n"
        "        v\n"
        "POST /api/risk/assess/{session_id}\n"
        "        |\n"
        "        v\n"
        "Gemma evidence arbitration\n"
        "        |\n"
        "        v\n"
        "GET /api/screening/{session_id}\n"
        "        |\n"
        "        v\n"
        "Final screening report"
    )
    pdf.code_box(api_flow_chart)
    pdf.body_p("ELA evidence artifacts are served from the backend evidence path.")

    # ================= SECTION 7: FRONTEND ARCHITECTURE =================
    pdf.section_title("7", "Frontend Architecture")
    pdf.body_p(
        "The frontend is a single-page application using HTML5, CSS3, modern JavaScript, GSAP, ScrollTrigger, "
        "and the browser MediaDevices API."
    )
    frontend_tree = (
        "frontend/\n"
        "+-- index.html\n"
        "+-- assets/\n"
        "|   +-- samples/\n"
        "|   +-- videos/\n"
        "+-- css/\n"
        "|   +-- variables.css\n"
        "|   +-- layout.css\n"
        "|   +-- landing.css\n"
        "|   +-- screening.css\n"
        "|   +-- styles.css\n"
        "+-- js/\n"
        "    +-- dev-guard.js\n"
        "    +-- config.js\n"
        "    +-- api.js\n"
        "    +-- animations.js\n"
        "    +-- screening.js\n"
        "    +-- app.js"
    )
    pdf.code_box(frontend_tree)
    pdf.body_p(
        "The landing page, screening workstation, processing state, and results experience are presented as one "
        "continuous product experience."
    )

    # ================= SECTION 8: SCREENING UI =================
    pdf.section_title("8", "Screening UI")
    pdf.body_p("The frontend supports:")
    ui_items = [
        "document upload",
        "presented-person image upload",
        "drag-and-drop input",
        "optional camera capture",
        "synthetic/demo sample cases",
        "processing visualization",
        "final risk report",
        "ELA/original comparison",
        "JSON audit export",
    ]
    for item in ui_items:
        pdf.bullet_point("", item)
    pdf.body_p(
        "The frontend is responsible for presentation and interaction; screening decisions continue to originate "
        "from the backend evidence pipeline."
    )

    # ================= SECTION 9: RESULTS =================
    pdf.section_title("9", "Results")
    pdf.body_p("A completed screening can expose:")
    res_items = [
        "final decision", "risk score", "risk level", "identity fields",
        "calculated age", "document validation state", "MRZ state when applicable",
        "face match state and distance", "tampering/ELA evidence", "temporal validation",
        "risk factors", "AI explanation", "session/audit metadata"
    ]
    for item in res_items:
        pdf.bullet_point("", item)
    pdf.body_p("The aim is to expose the evidence behind the decision rather than only a binary pass/fail result.")

    # ================= SECTION 10: TECHNOLOGY STACK =================
    pdf.section_title("10", "Technology Stack")

    stack_w = [45, 133]
    pdf.table_row(stack_w, ["Layer", "Components & Libraries"], is_header=True)
    pdf.table_row(stack_w, ["Backend", "Python 3.11+, FastAPI, Uvicorn, Pydantic v2, HTTPX"])
    pdf.table_row(stack_w, ["Vision & Forensics", "OpenCV, Pillow, NumPy, Error Level Analysis (ELA)"])
    pdf.table_row(stack_w, ["OCR Engine", "PaddleOCR / PP-OCR"])
    pdf.table_row(stack_w, ["Biometrics", "DeepFace, Facenet512, Cosine distance comparison"])
    pdf.table_row(stack_w, ["Database", "Supabase / PostgreSQL (where configured)"])
    pdf.table_row(stack_w, ["AI Layer", "Google AI Studio -- Gemma 4 31B (gemma-4-31b-it)"])
    pdf.table_row(stack_w, ["AI Fallbacks", "Ollama Vision (qwen2.5-vl), OpenRouter fallback"])
    pdf.table_row(stack_w, ["Frontend", "HTML5, CSS3, JavaScript, GSAP, ScrollTrigger, MediaDevices API"])

    # ================= SECTION 11: INSTALLATION =================
    pdf.section_title("11", "Installation")
    pdf.sub_title("Prerequisites")
    pdf.body_p("Install Python 3.11+, Git, the project dependencies, and at least one configured AI provider.")

    pdf.body_p("Clone the repository:")
    pdf.code_box("git clone https://github.com/mainSiddharthhoon/Veri-Gate.git\ncd Veri-Gate")

    pdf.sub_title("Create and activate a virtual environment:")
    pdf.body_p("Windows PowerShell:")
    pdf.code_box("python -m venv venv\n.\\venv\\Scripts\\Activate.ps1")
    pdf.body_p("Linux / macOS:")
    pdf.code_box("python -m venv venv\nsource venv/bin/activate")

    pdf.body_p("Install Python dependencies:")
    pdf.code_box("pip install -r backend/requirements.txt")
    pdf.body_p("If the active OCR installation requires an external OCR runtime, install the required runtime for the chosen environment.")

    # ================= SECTION 12: ENVIRONMENT CONFIGURATION =================
    pdf.section_title("12", "Environment Configuration")
    pdf.body_p("Create .env in the project root and provide the values appropriate for the selected deployment.")
    env_content = (
        "APP_NAME=VeriGate\n"
        "APP_VERSION=0.1.0\n"
        "DEBUG=false\n"
        "HOST=127.0.0.1\n"
        "PORT=8000\n\n"
        "SUPABASE_URL=your-supabase-url\n"
        "SUPABASE_ANON_KEY=your-supabase-anon-key\n"
        "SUPABASE_SERVICE_ROLE_KEY=your-service-role-key\n\n"
        "GEMINI_API_KEY=your-google-ai-studio-key\n\n"
        "VISION_BASE_URL=http://127.0.0.1:11434\n"
        "VISION_MODEL=qwen2.5-vl-7b-local\n"
        "VISION_API_KEY=\n\n"
        "OPENROUTER_API_KEY=your-openrouter-key\n"
        "OPENROUTER_MODEL=openrouter/free"
    )
    pdf.code_box(env_content)
    pdf.callout_box("SECURITY RULE", "Never commit real API keys or other secrets.")

    # ================= SECTION 13: RUNNING VERIGATE =================
    pdf.section_title("13", "Running VeriGate")
    pdf.body_p("From the project root:")
    pdf.code_box("python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000")
    pdf.body_p("Open the web application at:")
    pdf.code_box("http://127.0.0.1:8000/frontend/")
    pdf.body_p("Useful endpoints:")
    pdf.code_box("http://127.0.0.1:8000/docs\nhttp://127.0.0.1:8000/api/health")

    # ================= SECTION 14: TESTING =================
    pdf.section_title("14", "Testing")
    pdf.body_p("Run the backend test suite with:")
    pdf.code_box("pytest backend/tests -v")
    pdf.body_p("Important test areas include:")
    test_commands = (
        "pytest backend/tests/test_mrz.py -v\n"
        "pytest backend/tests/test_validation.py -v\n"
        "pytest backend/tests/test_field_extraction.py -v\n"
        "pytest backend/tests/test_tampering.py -v\n"
        "pytest backend/tests/test_face.py -v\n"
        "pytest backend/tests/test_risk.py -v"
    )
    pdf.code_box(test_commands)
    pdf.body_p(
        "The project was also validated with controlled synthetic end-to-end cases covering valid identities, "
        "biometric mismatches, invalid inputs, temporal inconsistencies, future DOBs, and multiple-error documents."
    )

    # ================= SECTION 15: SYNTHETIC TESTING DATA =================
    pdf.section_title("15", "Synthetic Testing Data")
    pdf.body_p("The repository uses synthetic fixtures for development and demonstration. Examples include:")
    fixtures_text = (
        "valid/\n"
        "    matching identity cases\n\n"
        "invalid/\n"
        "    invalid input\n"
        "    expired documents\n"
        "    future DOB\n"
        "    temporal contradictions\n"
        "    biometric mismatches\n"
        "    multiple-error documents"
    )
    pdf.code_box(fixtures_text)
    pdf.body_p(
        "Documents branded VERIGATE / SYNTHETIC IDENTITY LAB are authorized synthetic fixtures for this "
        "application's testing workflow."
    )
    pdf.callout_box(
        "PRIVACY & ETHICAL COMPLIANCE",
        "No real government identity documents or real personal identity datasets are intended to be distributed "
        "with the prototype.",
        border_r=15, border_g=23, border_b=42
    )

    # ================= SECTION 16: SECURITY AND PRIVACY CONSIDERATIONS =================
    pdf.section_title("16", "Security and Privacy Considerations")
    pdf.body_p("The prototype is designed so the AI reasoning layer can eventually be moved entirely to private infrastructure.")
    pdf.body_p("A production deployment should additionally implement:")
    sec_items = [
        "authenticated operators", "role-based access control (RBAC)",
        "encrypted transport (TLS 1.3)", "encrypted storage at rest",
        "secrets management", "retention and deletion policies",
        "controlled access to biometric evidence", "dataset governance",
        "production monitoring and audit controls"
    ]
    for item in sec_items:
        pdf.bullet_point("", item)

    # ================= SECTION 17: KNOWN LIMITATIONS =================
    pdf.section_title("17", "Known Limitations")
    pdf.sub_title("Physical security features")
    pdf.body_p("A normal image pipeline cannot reliably inspect tactile engraving, UV-only features, IR-only features, physical holograms, optically variable inks, or other features requiring specialized inspection hardware.")

    pdf.sub_title("NFC / ePassport cryptography")
    pdf.body_p("The prototype does not read or cryptographically verify passport NFC chips, ePassport PKI signatures, or chip-side biometric data.")

    pdf.sub_title("Lighting and occlusion")
    pdf.body_p("Glare, shadows, blur, poor face crops, masks, sunglasses, and other image-quality problems can make biometric or forensic stages inconclusive.")

    pdf.sub_title("Document coverage")
    pdf.body_p("MRZ validation is conditional on an MRZ being present and parsable. Documents without an MRZ use OCR and deterministic validation instead.")

    pdf.sub_title("Dataset-dependent intelligence")
    pdf.body_p("Real blacklist/watchlist detection and cross-session multiple-identity detection require authoritative datasets and additional matching infrastructure.")

    pdf.sub_title("AI latency")
    pdf.body_p("Cloud AI latency depends on network/provider conditions. Local multimodal model latency depends heavily on available CPU, GPU, RAM, and model configuration.")

    pdf.sub_title("Prototype evaluation")
    pdf.body_p("Current demonstrations use controlled synthetic fixtures. These tests should not be presented as production accuracy benchmarks.")

    # ================= SECTION 18: FUTURE EXTENSIONS =================
    pdf.section_title("18", "Future Extensions")
    pdf.body_p("Possible next steps include:")
    future_items = [
        "authoritative watchlist/blacklist integration",
        "cross-session identity correlation",
        "broader document-type support",
        "specialized visa/stamp validation",
        "stronger document-security inspection",
        "NFC/ePassport verification",
        "stronger local/on-prem multimodal reasoning",
        "production authentication and RBAC",
        "labeled-dataset benchmarking",
        "large-scale monitoring and analytics"
    ]
    for item in future_items:
        pdf.bullet_point("", item)

    # ================= SECTION 19: DESIGN RATIONALE =================
    pdf.section_title("19", "Design Rationale")
    pdf.body_p("The system deliberately avoids asking the LLM to perform every verification task.")
    rationale_box = (
        "Deterministic code           -> mathematical/date facts\n"
        "OCR / MRZ engines            -> document evidence\n"
        "Specialized vision/forensics -> biometric and image evidence\n"
        "Gemma                        -> cross-evidence reasoning\n"
        "                             -> risk + decision + explanation"
    )
    pdf.code_box(rationale_box)
    pdf.body_p(
        "This separation makes the pipeline easier to reason about, test, debug, and upgrade. "
        "A future local/on-prem multimodal model can replace the current AI provider while preserving "
        "the upstream verification architecture."
    )

    # ================= SECTION 20: CURRENT PROTOTYPE SCOPE =================
    pdf.section_title("20", "Current Prototype Scope")

    pdf.sub_title("Implemented")
    implemented_items = [
        "multimodal input qualification",
        "OCR and structured field extraction",
        "conditional MRZ validation",
        "deterministic document validation",
        "deterministic date/age validation",
        "ELA-based tampering evidence",
        "biometric face verification",
        "multimodal AI evidence arbitration",
        "risk scoring",
        "approve/review/reject decisions",
        "explainable screening report",
        "camera capture",
        "ELA/original comparison",
        "JSON audit export",
        "modular single-page frontend",
        "synthetic end-to-end testing fixtures"
    ]
    for item in implemented_items:
        pdf.bullet_point("", item)

    pdf.ln(1.5)
    pdf.sub_title("Not claimed by this prototype")
    not_claimed = [
        "real government watchlist access",
        "production border deployment",
        "NFC/ePassport chip verification",
        "physical security-feature inspection",
        "universal document recognition",
        "guaranteed production accuracy",
        "guaranteed fixed latency",
        "regulatory certification"
    ]
    for item in not_claimed:
        pdf.bullet_point("", item)

    # ================= SECTION 21: SUMMARY =================
    pdf.section_title("21", "Summary")
    pdf.body_p("VeriGate is an evidence-first identity screening system:")
    summary_flow = (
        "Input\n"
        "  -> Qualification\n"
        "  -> OCR\n"
        "  -> MRZ (when applicable)\n"
        "  -> Deterministic Validation\n"
        "  -> ELA Forensics\n"
        "  -> Face Verification\n"
        "  -> Gemma Reasoning\n"
        "  -> Risk + Decision + Explanation"
    )
    pdf.code_box(summary_flow)
    pdf.body_p(
        "The architecture is modular so individual verification components and the AI reasoning provider "
        "can be improved or replaced without rebuilding the entire application."
    )

    # ================= SECTION 22: LICENSE =================
    pdf.section_title("22", "License")
    pdf.body_p("See the repository LICENSE file for the applicable license terms.")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 5, "END OF DEVELOPER DOCUMENTATION -- VERIGATE PROTOTYPE", align="C")

    # Output file
    pdf.output(output_path)
    print(f"Developer Documentation PDF successfully generated at: {output_path} ({pdf.page_no()} pages)")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "VeriGate_Developer_Documentation.pdf"
    build_pdf(out)
