"""
VeriGate Developer Documentation PDF Generator
Uses fpdf2 to generate a publication-grade, professional technical PDF manual.
Latin-1 compatible for standard Helvetica/Arial fonts.
"""

import sys
from pathlib import Path
from fpdf import FPDF

class VeriGatePDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 18, 18)

    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(100, 116, 139) # Slate 500
            self.cell(100, 7, "VERIGATE -- TECHNICAL ARCHITECTURE & DEVELOPER MANUAL", align="L")
            self.cell(74, 7, "INTERNAL & JURY BRIEFING", align="R", new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(226, 232, 240) # Slate 200
            self.set_line_width(0.3)
            self.line(18, 17, 192, 17)
            self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184) # Slate 400
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.line(18, 283, 192, 283)
        self.cell(120, 6, "CONFIDENTIAL & OPEN-SOURCE (APACHE 2.0 / MIT) | VERIGATE CORE TEAM", align="L")
        page_str = f"Page {self.page_no()} of {{nb}}"
        self.cell(54, 6, page_str, align="R")

    def section_title(self, num, title):
        self.ln(4)
        self.set_fill_color(15, 23, 42) # Dark Slate / Navy (#0f172a)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 10.5)
        # Colored accent block
        self.cell(0, 7.5, f"  {num}. {title.upper()}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2.5)

    def sub_title(self, title):
        self.set_font("Helvetica", "B", 9.5)
        self.set_text_color(225, 29, 72) # Crimson Rose (#e11d48)
        self.cell(0, 5.5, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_p(self, text):
        self.set_font("Helvetica", "", 8.8)
        self.set_text_color(51, 65, 85) # Slate 700
        self.multi_cell(0, 4.3, text)
        self.ln(2)

    def bullet_point(self, bold_prefix, text):
        self.set_font("Helvetica", "B", 8.6)
        self.set_text_color(15, 23, 42)
        self.cell(6, 4.3, " - ")
        self.cell(self.get_string_width(bold_prefix) + 1, 4.3, bold_prefix)
        self.set_font("Helvetica", "", 8.6)
        self.set_text_color(51, 65, 85)
        remaining_w = 174 - 6 - (self.get_string_width(bold_prefix) + 1)
        self.multi_cell(remaining_w, 4.3, text)
        self.ln(1)

    def callout_box(self, title, text, bg_r=248, bg_g=250, bg_b=252, border_r=203, border_g=213, border_b=225):
        self.set_fill_color(bg_r, bg_g, bg_b)
        self.set_draw_color(border_r, border_g, border_b)
        self.set_line_width(0.4)
        
        self.set_font("Helvetica", "B", 8.5)
        title_lines = 1
        self.set_font("Helvetica", "", 8.2)
        text_lines = len(text) // 95 + text.count('\n') + 1
        box_h = (title_lines + text_lines) * 4.3 + 6

        x = self.get_x()
        y = self.get_y()
        self.rect(x, y, 174, box_h, style="FD")
        self.set_xy(x + 3, y + 2.5)
        self.set_font("Helvetica", "B", 8.8)
        self.set_text_color(225, 29, 72)
        self.cell(168, 4.5, title, new_x="LMARGIN", new_y="NEXT")
        self.set_x(x + 3)
        self.set_font("Helvetica", "", 8.2)
        self.set_text_color(71, 85, 105)
        self.multi_cell(168, 4.0, text)
        self.set_xy(x, y + box_h + 2)

    def table_row(self, col_widths, texts, is_header=False):
        if is_header:
            self.set_fill_color(30, 41, 59)
            self.set_text_color(255, 255, 255)
            self.set_font("Helvetica", "B", 8)
        else:
            self.set_fill_color(248, 250, 252)
            self.set_text_color(51, 65, 85)
            self.set_font("Helvetica", "", 7.6)

        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.2)
        for w, t in zip(col_widths, texts):
            self.cell(w, 5.5, f" {t}", border=1, fill=True)
        self.ln(5.5)

def build_pdf(output_path="VeriGate_Developer_Documentation.pdf"):
    pdf = VeriGatePDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # --- TITLE / COVER BLOCK ---
    pdf.set_fill_color(15, 23, 42) # Slate 900
    pdf.rect(18, 18, 174, 38, style="F")

    pdf.set_xy(22, 22)
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, "VERIGATE: DEVELOPER TECHNICAL MANUAL", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(22)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(244, 63, 94) # Rose 500
    pdf.cell(0, 5.5, "Multimodal Verification Pipeline, Synthetic Data Strategy & Enterprise Architecture", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(22)
    pdf.set_font("Helvetica", "", 7.8)
    pdf.set_text_color(148, 163, 184) # Slate 400
    pdf.cell(0, 5, "Version 2.0.0 | Release: September 2026 | Target Audience: Core Engineering, DevOps, & Jury", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(60)

    # --- SECTION 1: EXECUTIVE ARCHITECTURE & MISSION ---
    pdf.section_title("1", "Executive Summary & System Mission")
    pdf.body_p(
        "Border checkpoints, immigration corridors, and digital banking platforms process millions of identity "
        "documents daily. Existing automated screeners suffer from a critical flaw: they operate in isolated silos. "
        "OCR, checksums, and face matchers run independently and produce opaque pass/fail scores that obscure "
        "evidence or trigger unexplainable rejections."
    )
    pdf.body_p(
        "VeriGate solves this by introducing an explainable, 7-stage sequential multimodal pipeline. "
        "Objective signals (optical glyphs, ICAO Modulo 7-3-1 check digits, pixel error level residuals, and "
        "512-dimensional facial embeddings) are synthesized by Gemma AI, acting as an evidence arbiter to output "
        "an auditable 0-100 risk score, categorical decision (APPROVE / REVIEW / REJECT), and natural-language rationale."
    )

    pdf.callout_box(
        "CORE VALUE PROPOSITION",
        "Deterministic Rules ensure zero AI hallucination on mathematical standards (ICAO 9303, calendar dates).\n"
        "Generative Vision-Language Arbitration (Gemma) prevents false rejections caused by real-world camera noise "
        "and detects sophisticated digital photo splicing that human eyes miss."
    )

    # --- SECTION 2: 7-STAGE PIPELINE ---
    pdf.section_title("2", "The 7-Stage Verification Pipeline")
    
    stages = [
        ("Stage 1: Pre-Flight Input Qualification", "Gemma Vision validates document framing and human portrait suitability before committing heavy CPU/GPU cycles. Fails early on blurry, truncated, or non-document submissions."),
        ("Stage 2: OCR & Field Extraction", "Preprocesses images with adaptive thresholding. Tesseract extracts glyphs; heuristic typography segmenters parse Surname, Given Names, Document Number, Nationality, DOB, and Expiry."),
        ("Stage 3: ICAO 9303 MRZ Verification", "Parses TD1/TD2/TD3 Machine Readable Zones. Computes Modulo-10 checksums using cyclic weights [7, 3, 1] on Doc Number, DOB, Expiry, and composite checksum. Non-MRZ IDs skip cleanly."),
        ("Stage 4: Deterministic Rule Engine", "Strict calendar logic: DOB strictly in past, age computed in years, expiration strictly in future, issue date predates expiry. Zero hallucination risk."),
        ("Stage 5: Tampering Forensics (ELA)", "Recompresses document at JPEG Q=90. Computes absolute difference matrix scaled 15x. Spliced portraits and pasted text light up as high-frequency noise anomalies. Outputs ELA Heatmap."),
        ("Stage 6: Biometric Facial Match", "Locates and crops document face and live selfie. Facenet512 extracts 512-D deep feature embeddings. Evaluates identity correspondence via Cosine Distance (match if distance < 0.40)."),
        ("Stage 7: Gemma AI Arbitration", "Synthesizes multi-source evidence dossier. Differentiates harmless scan glare from genuine forgery. Computes final 0-100 score, decision, and itemized weighted risk factors.")
    ]

    for title, desc in stages:
        pdf.sub_title(title)
        pdf.body_p(desc)

    # --- SECTION 3: THE WHY SYNTHETIC DATA MANDATE ---
    pdf.section_title("3", "The 'Why Synthetic Data?' Strategy & Justification")
    pdf.body_p(
        "A critical question frequently asked by technical evaluators is: Why did VeriGate utilize synthetic identity "
        "documents for development and testing instead of real scraped passports? This was a deliberate, "
        "ethical, and scientifically rigorous architectural choice driven by three pillars:"
    )

    pdf.bullet_point("1. Regulatory Compliance (GDPR, CCPA, BIPA): ", 
                     "Real identity documents contain Tier-1 sensitive Personally Identifiable Information (PII) and biometric "
                     "identifiers. Storing or transmitting authentic government IDs in developmental test suites, Git repositories, "
                     "or shared cloud environments violates GDPR Articles 9/83 and BIPA, carrying severe criminal penalties.")

    pdf.bullet_point("2. Mathematically Controlled Ground-Truth: ", 
                     "In real-world fraudulent passports seized at checkpoints, the exact tampering delta is rarely known. "
                     "Synthetic document generation allows Counterfactual Pair Testing: creating an identical pristine document "
                     "and a surgically altered clone (e.g. changing 1985 to 1995, or altering one check digit). This lets us measure "
                     "the exact sensitivity, recall, and false-positive rates of our ELA and MRZ engines.")

    pdf.bullet_point("3. Adversarial Edge-Case Simulation: ", 
                     "Authentic public datasets do not provide rare adversarial attacks needed to stress-test border systems. "
                     "With synthetic engines, we programmatically simulate leap-day edge cases (Feb 29 on non-leap years), "
                     "single-pixel font cloning, and spliced facial borders across diverse demographic profiles without bias.")

    pdf.callout_box(
        "LEGAL & BENCHMARKING TAKEAWAY",
        "Synthetic test fixtures (e.g., synthetic_passport.jpg and synthetic_passport_tampered.jpg) ensure VeriGate is "
        "100% legally compliant, ethically auditable, and reproducibly benchmarked with zero real-world citizen data leaks."
    )

    # --- SECTION 4: HOW AI IMPROVES SCREENING ---
    pdf.section_title("4", "How AI Improves & Transforms Document Screening")
    pdf.body_p(
        "Traditional identity screening software relies on hardcoded threshold logic (e.g., 'if confidence < 75% then reject'). "
        "In production, this leads to disastrous failure modes: document laminate reflection, minor OCR typos, or camera "
        "distortions trigger false rejections of legitimate travelers, while stealthy synthetic forgeries pass unnoticed."
    )

    pdf.sub_title("The Explainable AI (XAI) Arbiter Difference:")
    pdf.bullet_point("Differentiating Noise from Fraud: ", 
                     "If OCR reads 'SM1TH' instead of 'SMITH' due to plastic sheen, but the MRZ check digit passes and face similarity "
                     "is 95%, Gemma reconciles this as an optical glare artifact and approves the passenger, preventing airport queues.")
    pdf.bullet_point("Isolating Stealth Forgeries: ", 
                     "If a forged passport exhibits visually perfect typography and clean dates, but Error Level Analysis flags "
                     "anomalous compression noise across the birth year bounding box, Gemma isolates the fraud and triggers an itemized REJECT.")
    pdf.bullet_point("Auditable Legal Trail: ", 
                     "Instead of returning an unexplainable number, VeriGate delivers a plain-language executive rationale suitable "
                     "for court submission, supervisory review, and traveler notification.")

    # --- SECTION 5: DEPLOYMENT PARADIGMS ---
    pdf.section_title("5", "Deployment Engineering: Cloud API vs. Air-Gapped Enterprise")
    pdf.body_p(
        "VeriGate is engineered with a modular Provider Abstraction Layer, allowing identical application code to run "
        "seamlessly in cloud-assisted rapid prototyping and sovereign, air-gapped enterprise environments."
    )

    col_w = [45, 64, 65]
    pdf.table_row(col_w, ["Dimension", "Hackathon / Dev Cloud Setup", "Enterprise / Border Agency Production"], is_header=True)
    pdf.table_row(col_w, ["Target Use Case", "Rapid iteration, team testing, hackathons", "Border checkpoints, defense, Tier-1 banks"])
    pdf.table_row(col_w, ["AI Reasoning Engine", "Google AI Studio REST (Gemma-4-31B-IT)", "Local GPU Cluster (vLLM / TensorRT-LLM)"])
    pdf.table_row(col_w, ["Model Deployment", "Cloud API endpoint (OpenRouter fallback)", "Self-hosted quantized Gemma-27B/9B / Qwen-VL"])
    pdf.table_row(col_w, ["Data Sovereignty", "Encrypted HTTPS transport to public cloud", "100% Air-gapped on-premises; 0 outbound traffic"])
    pdf.table_row(col_w, ["Database / Storage", "Supabase Cloud PostgreSQL + S3 bucket", "Self-hosted PostgreSQL with Row-Level Security"])
    pdf.table_row(col_w, ["Inference Latency", "~2.0 - 3.2 seconds (WAN network roundtrip)", "< 450 - 750 milliseconds (Local PCIe/LAN)"])
    pdf.table_row(col_w, ["Hardware Cost", "Zero GPU server cost (Pay-per-token / Free tier)", "Local dual-GPU workstation (NVIDIA RTX/A100)"])

    pdf.ln(2)
    pdf.body_p(
        "Key Architectural Insight: The application logic (FastAPI, screening pipeline, ELA, MRZ, DeepFace) remains "
        "100% identical between both deployments. Switching from cloud development to sovereign enterprise simply requires "
        "updating the environment variables (VISION_BASE_URL and SUPABASE_URL) to local intranet hostnames."
    )

    # --- SECTION 6: DATA CONTRACTS & DATABASE SCHEMA ---
    pdf.section_title("6", "API Specifications & Supabase Relational Schema")
    pdf.body_p(
        "VeriGate's data architecture is backed by 10 relational tables in PostgreSQL (Supabase) with foreign-key cascade "
        "protection and JSONB document structures:"
    )

    t_cols = [42, 38, 94]
    pdf.table_row(t_cols, ["Table Name", "Key Columns", "Operational Role & Data Payload"], is_header=True)
    pdf.table_row(t_cols, ["screening_sessions", "id, status, doc_type", "Root session entity (pending -> processing -> completed)"])
    pdf.table_row(t_cols, ["documents", "session_id, surname, mrz", "Extracted identity fields, parsed MRZ, JSONB extras"])
    pdf.table_row(t_cols, ["ocr_results", "session_id, raw_text, conf", "Raw Tesseract OCR glyphs, bounding boxes, confidence"])
    pdf.table_row(t_cols, ["validation_results", "session_id, is_valid", "Summary of deterministic validation rules pass/fail"])
    pdf.table_row(t_cols, ["validation_checks", "result_id, check_name", "Granular check rows (mrz_checksum, expiry_date_valid)"])
    pdf.table_row(t_cols, ["tampering_analyses", "session_id, tamper_score", "Overall Error Level Analysis score, suspicious flag"])
    pdf.table_row(t_cols, ["tampering_signals", "analysis_id, signal_type", "Granular tamper signals linked to ELA heatmap evidence"])
    pdf.table_row(t_cols, ["face_verifications", "session_id, distance, match", "Facenet512 biometric distance, threshold, match flag"])
    pdf.table_row(t_cols, ["risk_assessments", "session_id, score, decision", "Gemma AI risk score (0-100), decision, plain-language text"])
    pdf.table_row(t_cols, ["risk_factors", "assessment_id, severity", "Itemized risk contributions (factor_source, weight, severity)"])

    # --- SECTION 7: QUALITY ASSURANCE & HARDENING ---
    pdf.section_title("7", "Verification, Hardening & Accessibility Standards")
    pdf.bullet_point("Automated Test Suite: ", "78 targeted unit tests covering MRZ math, date arithmetic, and field extraction (test_mrz.py, test_validation.py, test_field_extraction.py).")
    pdf.bullet_point("Database E2E Script: ", "scripts/test_db_full.py verifies end-to-end Supabase CRUD, schema constraints, and foreign key cascading.")
    pdf.bullet_point("Lighthouse Accessibility: ", "100% compliant with WCAG accessibility guidelines, featuring semantic landmarks (<header>, <main id='main-content'>, <footer>) and strict sequential heading hierarchy (h1 -> h2 -> h3).")
    pdf.bullet_point("Mobile Touch Hardening: ", "Responsive CSS Grid architecture with 50/50 balanced action buttons and live HTTPS camera support.")

    # --- SECTION 8: ROADMAP ---
    pdf.section_title("8", "Physical Limitations & Enterprise Roadmap")
    pdf.bullet_point("Physical Holograms & UV: ", "Standard optical cameras cannot inspect physical intaglio print, UV ink, or tactile features. Future versions interface with dedicated multi-spectral 3M/Desko hardware.")
    pdf.bullet_point("ICAO 9303 NFC Chip Reading: ", "Phase 3 roadmap adds contact/contactless smartcard chip reader support to verify cryptographically signed biometrics directly from the ePassport RFID chip.")
    pdf.bullet_point("3D Passive Liveness: ", "Integration of temporal depth-mapping to defeat advanced silicon mask and deepfake replay attacks.")

    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 5, "END OF TECHNICAL MANUAL | VERIGATE IDENTITY INTELLIGENCE", align="C")

    # Output file
    pdf.output(output_path)
    print(f"Developer Documentation PDF successfully generated at: {output_path} ({pdf.page_no()} pages)")

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "VeriGate_Developer_Documentation.pdf"
    build_pdf(out)
