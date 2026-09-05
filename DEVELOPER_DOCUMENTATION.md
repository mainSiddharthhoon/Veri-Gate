# VeriGate: Technical Architecture & Developer Documentation
**Internal Engineering & Jury Technical Reference**  
*Document Version:* 2.0.0 | *Last Updated:* September 2026 | *Classification:* Engineering Technical Manual  

---

## Table of Contents
1. [Executive Summary & System Mission](#1-executive-summary--system-mission)
2. [End-to-End Multimodal System Architecture](#2-end-to-end-multimodal-system-architecture)
3. [The 7-Stage Verification Pipeline: Engineering Deep-Dive](#3-the-7-stage-verification-pipeline-engineering-deep-dive)
4. [The "Why Synthetic Data?" Rationale & Data Strategy](#4-the-why-synthetic-data-rationale--data-strategy)
5. [How AI Improves & Transforms Document Screening](#5-how-ai-improves--transforms-document-screening)
6. [Deployment Engineering: Cloud API Prototyping vs. Air-Gapped Enterprise Infrastructure](#6-deployment-engineering-cloud-api-prototyping-vs-air-gapped-enterprise-infrastructure)
7. [API Specifications, Data Contracts & Supabase Schema](#7-api-specifications-data-contracts--supabase-schema)
8. [Testing, Security Hardening & Accessibility Standards](#8-testing-security-hardening--accessibility-standards)
9. [Known Physical Limitations & Future Roadmap](#9-known-physical-limitations--future-roadmap)

---

## 1. Executive Summary & System Mission

### 1.1 The Problem
Border checkpoints, immigration counters, and financial KYC operations process tens of thousands of identity documents daily (passports, national IDs, visas, permits). Existing automated inspection tools suffer from three fundamental deficiencies:
1. **Siloed Brittle Engines**: Optical Character Recognition (OCR), check-digit validation, and face comparison run as isolated components. A single minor optical glitch causes catastrophic false rejections, while sophisticated composite forgeries slip through.
2. **Opaque Black-Box Rejections**: Most commercial screening tools output an unexplainable scalar score (e.g., `Risk: 74%`). Security officers and border agents are unable to determine *why* a traveler was flagged, leading to lengthy secondary inspections, racial/demographic bias, and regulatory non-compliance.
3. **Sophisticated Digital Forgery**: High-fidelity generative image editing and digital splicing easily bypass basic visual inspections by human agents fatigued by high passenger volume.

### 1.2 The VeriGate Solution
VeriGate is an **open-source, explainable multimodal identity verification engine**. It synthesizes:
- **Optical Typography & OCR** (Tesseract & heuristic segmentation)
- **Mathematical Check-Digit Validation** (ICAO 9303 Modulo 7-3-1 algorithms)
- **Forensic Compression Analysis** (Error Level Analysis - ELA & localized noise variance)
- **512-Dimensional Deep Biometrics** (Facenet512 & Cosine feature distance)
- **Explainable Multimodal AI Arbitration** (Google Gemma 4 31B IT / Vision Models)

Instead of relying on rigid thresholds, VeriGate reconciles all extracted evidence into an auditable **0–100 risk score**, a clear decision (**`APPROVE` / `REVIEW` / `REJECT`**), itemized weighted risk factors, and a natural-language forensic explanation.

---

## 2. End-to-End Multimodal System Architecture

```
                                  [ INTAKE WORKSTATION ]
                  ┌─────────────────────────────────────────────────────┐
                  │ • Identity Document (Passport / National ID / Visa) │
                  │ • Presented Individual Photo (File Upload / Camera) │
                  └──────────────────────────┬──────────────────────────┘
                                             │ HTTP POST /api/screen
                                             ▼
                                     [ FASTAPI BACKEND ]
                                             │
      ┌──────────────────────────────────────┼──────────────────────────────────────┐
      │                                      │                                      │
      ▼                                      ▼                                      ▼
[ STAGE 1: QUALIFY ]               [ STAGE 2: OCR & MRZ ]                 [ STAGE 5: ELA ]
Gemma Vision Input Gate            Tesseract Text Extraction              JPEG Resave (Q=90)
• Document Framing                 • Surname / Given Names                • Pixel Delta Matrix
• Portrait Presence                • Document ID / Nationality            • Splicing Heatmap
• Fail-Early Check                 • ICAO 7-3-1 Check Digits              • Face Region Variance
      │                                      │                                      │
      └──────────────────────────────────────┼──────────────────────────────────────┘
                                             │
                                             ▼
                               [ STAGE 6: BIOMETRICS ]
                               Facenet512 Face Verification
                               • Face Crop & Alignment
                               • 512-D Embedding Extraction
                               • Cosine Distance Metric
                                             │
                                             ▼
                        [ STAGE 7: GEMMA AI ARBITRATION ]
                        Multimodal Evidence Reconciliation
                        • Correlates Visual + Math + Forensic Signals
                        • Discards False Positives (Glare, Minor Scans)
                        • Synthesizes Risk Score (0-100) & Decision
                                             │
                                             ▼
                              [ PERSISTENCE & AUDIT LOG ]
                        Supabase PostgreSQL (10 Relational Tables)
                        • Audit Trail & Immutable Decision Records
                        • Exportable JSON & Executive PDF Reports
```

---

## 3. The 7-Stage Verification Pipeline: Engineering Deep-Dive

### Stage 1: Pre-Flight Input Qualification (`qualify_inputs`)
* **File:** `backend/app/services/ai_reasoning.py`
* **Objective:** Fail early on degraded, unreadable, or fraudulent non-document submissions before committing expensive CPU/GPU cycles to OCR or facial inference.
* **Mechanism:**
  - Evaluates document image geometry, lighting, readability, and boundary visibility.
  - Verifies presence of a valid, human frontal face in the presented selfie.
  - Returns `inputs_qualified: bool`. If invalid, immediately rejects with descriptive feedback (e.g., `"Document image is severely blurred and cut off at top border"`).

### Stage 2: Optical OCR & Structured Field Extraction (`ocr_pipeline`)
* **Files:** `backend/app/services/ocr_pipeline.py`, `backend/app/services/field_extraction.py`
* **Objective:** Extract raw glyphs and normalize them into structured identity fields.
* **Mechanism:**
  - Image preprocessing: Grayscale conversion, adaptive Otsu thresholding, noise reduction via morphological filtering.
  - Tesseract OCR extraction with physical glyph coordinate tracking.
  - Typographic heuristic regex segmentation parses Surname, Given Names, Document Number, Nationality, Date of Birth, and Expiration Date into a strongly-typed `DocumentFields` model.

### Stage 3: ICAO 9303 MRZ Check Digit Verification (`mrz.py`)
* **File:** `backend/app/services/mrz.py`
* **Objective:** Enforce international civil aviation standards on Machine Readable Travel Documents (MRTDs).
* **Mechanism:**
  - Parses ICAO 9303 TD3 (Passports: 2 lines × 44 chars) and TD1/TD2 (ID cards: 3 lines × 30 chars or 2 lines × 36 chars).
  - Computes Modulo 10 checksums using fixed cyclic weights `[7, 3, 1]`:
    $$\text{Checksum} = \left( \sum_{i=1}^{n} c_i \cdot w_{(i-1) \pmod 3} \right) \pmod{10}$$
  - Verifies check digits for:
    1. Document Number
    2. Date of Birth (`YYMMDD`)
    3. Expiration Date (`YYMMDD`)
    4. Optional Personal Number
    5. Composite Master Check Digit covering all fields.
  - Documents lacking an MRZ (e.g., standard national ID cards) gracefully bypass this stage without failing.

### Stage 4: Deterministic Document Validation (`validation.py`)
* **File:** `backend/app/services/validation.py`
* **Objective:** Pure mathematical and temporal logic with **zero hallucination risk**.
* **Rules Evaluated:**
  - **Temporal Integrity**: Date of birth must strictly precede current date.
  - **Subject Age**: Accurately computes chronological age in years.
  - **Expiry Status**: Expiration date must strictly succeed the screening timestamp.
  - **Issuance Plausibility**: Document issue date must strictly precede expiration date.
  - **Format Conformance**: Validates numbering syntax against country-specific rules.

### Stage 5: Tampering Forensics & Error Level Analysis (`tampering_core.py`)
* **File:** `backend/app/services/tampering_core.py`
* **Objective:** Detect digital photo replacement, text modification, and clone-stamp manipulations.
* **Mechanism:**
  - Re-compresses the document image at a known, fixed JPEG quality level ($Q = 90$).
  - Calculates the absolute difference between original and recompressed image matrices:
    $$\Delta(x, y) = 15 \times |I_{\text{orig}}(x, y) - I_{\text{recomp}}(x, y)|$$
  - Digital pastes, modified fonts, and replaced portrait boxes exhibit starkly divergent error levels compared to the original background.
  - Generates a visual forensic ELA Heatmap artifact saved to `/evidence/` for human inspector review.

### Stage 6: Biometric Facial Correspondence (`face_core.py`)
* **File:** `backend/app/services/face_core.py`
* **Objective:** Biometrically verify that the document holder matches the live presented individual.
* **Mechanism:**
  - OpenCV/Haar/RetinaFace pipeline crops the face from the identity document and the live presented photo.
  - Computes 512-dimensional facial embedding vectors using the **Facenet512** deep neural network.
  - Evaluates similarity via **Cosine Distance**:
    $$\text{Distance} = 1 - \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2}$$
    - Distance $< 0.40 \implies$ High-confidence biometric match.
    - Distance $\ge 0.40 \implies$ Biometric identity mismatch.

### Stage 7: Gemma AI Multimodal Arbitration (`ai_reasoning.py`)
* **File:** `backend/app/services/ai_reasoning.py`
* **Objective:** Evidence synthesis, contradiction resolution, and natural-language risk reporting.
* **Mechanism:**
  - Evaluates the holistic forensic dossier: visual document photo, live selfie, ELA heatmap, extracted fields, MRZ verification status, deterministic validation results, tampering scores, and biometric distance.
  - Resolves false alarms (e.g., OCR misreading `"O"` as `"0"`, but MRZ check digit and facial biometrics pass 100%).
  - Produces structured JSON output (`AiAssessment`) with:
    - Overall Risk Score ($0 - 100$)
    - Categorical Decision: `APPROVE`, `REVIEW`, or `REJECT`
    - Itemized, weighted Risk Factors
    - Plain-language forensic reasoning narrative for security personnel.

---

## 4. The "Why Synthetic Data?" Rationale & Data Strategy

During development, testing, and automated unit testing, VeriGate exclusively utilizes **programmatically generated synthetic identity documents** (e.g., `synthetic_passport.jpg`, `synthetic_passport_tampered.jpg`). This deliberate engineering choice addresses three critical challenges:

### 4.1 Strict Privacy Laws & Regulatory Compliance (GDPR, CCPA, BIPA)
- Real identity documents contain highly sensitive Personally Identifiable Information (PII), including full names, birth dates, national registry IDs, and biometric face portraits.
- Committing authentic government credentials to source code repositories, training corpora, or cloud testing environments violates **GDPR (Articles 9 & 83)**, the **Biometric Information Privacy Act (BIPA)**, and international privacy standards.
- Violations carry severe criminal and financial penalties (up to €20M or 4% of global annual turnover).

### 4.2 Controlled Ground-Truth & Counterfactual Benchmarking
- In real-world counterfeit documents seized at borders, the **exact ground-truth tampering delta** is often uncertain: exactly which pixels were modified, what font was cloned, or what compression artifacts were introduced by the counterfeiter.
- Synthetic generation provides **mathematically known ground-truth**:
  - We create an unaltered baseline document (`synthetic_passport.jpg`).
  - We create an exact counterfactual copy (`synthetic_passport_tampered.jpg`) with surgically controlled modifications: changing a birth year from `1985` to `1995`, modifying an expiry check digit, or replacing the face box.
  - This allows us to quantify the **exact sensitivity, precision, and recall** of our ELA algorithm and MRZ validator.

### 4.3 Adversarial Edge-Case Simulation
- Authentic identity datasets rarely contain the exotic, adversarial edge cases necessary to test screening robustness:
  - Leap-day birthdays (`Feb 29`) on non-leap years.
  - Expired visas pasted inside valid passport booklets.
  - Single-character check-digit transpositions.
  - Spliced facial portraits with subtle boundary blur.
- Synthetic generation allows our engineering team to simulate thousands of diverse adversarial permutations on demand without ethical or legal compromises.

---

## 5. How AI Improves & Transforms Document Screening

### 5.1 Moving Beyond Brittle Rules and Unexplainable Black Boxes
Traditional verification architectures fall into two extremes:
1. **Rigid Rule Engines**: Brittle and unforgiving. A slight glare over a barcode, an unparsed middle name, or a camera reflection causes automatic rejection of legitimate travelers, creating massive airport bottlenecks.
2. **Opaque Deep Learning Black Boxes**: Outputs a non-interpretable probability (e.g., `Fraud: 0.82`). Border security officers cannot legally detain a traveler based on an unexplainable number without actionable evidence.

### 5.2 The Explainable AI (XAI) Arbiter Pattern
VeriGate implements a **two-tier hybrid architecture**:
1. **Tier 1 (Deterministic & Forensic Feature Extraction)**: Math, algorithms, and deep metrics compute objective signals (MRZ checksum validity, ELA variance ratios, Facenet cosine distance).
2. **Tier 2 (Gemma AI Multimodal Arbitration)**: A multimodal vision-language model acts as the "court magistrate". It correlates the objective findings with visual context:
   - *Example 1 (Innocent Glare)*: OCR read `"SM1TH"` instead of `"SMITH"`, but MRZ Modulo-10 checksum is valid and Facenet distance is $0.14$. Gemma rules: **`APPROVE`** — optical character error attributed to document laminate glare, identity confirmed.
   - *Example 2 (Stealth Forgery)*: All OCR fields and typography look plausible, but ELA heatmap exhibits high-frequency localized noise variance over the expiration year. Gemma rules: **`REJECT`** — localized digital splicing detected over expiration date.

### 5.3 Continuous Learning & Active Feedback
In future iterations, human border officer overrides (approving or confirming fraud on flagged cases) feed into an active learning feedback loop, fine-tuning local detection heads without storing raw biometric images.

---

## 6. Deployment Engineering: Cloud API Prototyping vs. Air-Gapped Enterprise Infrastructure

A major design strength of VeriGate is its **infrastructure-agnostic provider abstraction layer**.

```
                  ┌───────────────────────────────────────────────────┐
                  │          VeriGate Provider Abstraction            │
                  └─────────┬───────────────────────────────┬─────────┘
                            │                               │
             ┌──────────────┴──────────────┐ ┌──────────────┴──────────────┐
             │    Development / Hackathon  │ │    Enterprise / Sovereign   │
             │       Cloud Architecture    │ │    Air-Gapped Infrastructure│
             ├─────────────────────────────┤ ├─────────────────────────────┤
             │ • Google AI Studio REST     │ │ • Local GPU Rig (vLLM)      │
             │ • OpenRouter Fallback       │ │ • Quantized Gemma-27B/9B    │
             │ • Supabase Cloud DB         │ │ • Local PostgreSQL + RLS    │
             │ • Cloudflare Dev Tunnels    │ │ • Isolated Air-Gapped LAN   │
             │ • Zero GPU Cloud Overhead   │ │ • Zero Outbound Telemetry   │
             └─────────────────────────────┘ └─────────────────────────────┘
```

### 6.1 Our Development Setup (Cloud API Providers)
For development, fast prototyping, and hackathon demonstration, VeriGate utilized:
- **Google AI Studio REST API** (`gemma-4-31b-it` / Gemini): Rapid testing, state-of-the-art vision capabilities, zero local GPU requirements.
- **OpenRouter Multimodal Fallback**: Redundant cloud backup if primary rate limits are reached.
- **Cloudflare Quick Tunnels**: Zero-config HTTPS tunneling for real-time mobile phone camera testing (`https://...trycloudflare.com`).
- **Supabase Cloud (PostgreSQL)**: Instant cloud database with RESTful JSON querying and live dashboard.

### 6.2 Enterprise & Border Checkpoint Deployment (Air-Gapped On-Premises)
In production deployment at national borders, customs, or defense facilities, regulations forbid streaming passenger documents across public cloud networks. VeriGate is architected for **turnkey on-premises execution**:
- **Air-Gapped Inference Server**: Local high-density GPU server (e.g., dual NVIDIA RTX 4090s or single A100/H100) running **vLLM** or **Ollama** with quantized `gemma-2-27b-it` or `qwen2.5-vl-7b-instruct`.
- **Local Biometrics & OCR**: Tesseract and DeepFace execute locally with sub-second CPU/CUDA inference.
- **Self-Hosted PostgreSQL**: On-premises PostgreSQL database with Row-Level Security (RLS) and encrypted audit tables.
- **Data Sovereignty Guarantee**: 100% of document buffers, ELA heatmaps, and facial feature vectors remain strictly within the physical checkpoint perimeter. Latency drops from ~2.5s (cloud roundtrip) to **< 600ms total pipeline execution**.

---

## 7. API Specifications, Data Contracts & Supabase Schema

### 7.1 Core API Endpoints
* **`POST /api/screen`**: Primary screening intake endpoint.
  - *Request*: `multipart/form-data` with `document` (image file) and `presented_person` (image file).
  - *Response*: Structured JSON containing session ID, extracted fields, validation results, tampering scores, face match metrics, and Gemma AI reasoning verdict.
* **`GET /api/health`**: Real-time service health check. Verifies API availability and database connectivity.
* **`GET /evidence/{filename}`**: Serves generated ELA forensic heatmap images.
* **`POST /api/sessions`**: Creates and tracks long-term screening sessions.

### 7.2 Database Schema (Supabase PostgreSQL)
VeriGate defines **10 relational tables** in `supabase/migrations/001_initial_schema.sql`:
1. `screening_sessions`: Primary screening entity; tracks session lifecycle (`pending`, `processing`, `completed`, `failed`).
2. `documents`: Structured extracted identity data (names, doc number, nationality, DOB, expiry, raw & parsed MRZ lines).
3. `ocr_results`: Raw OCR glyph output, bounding boxes, and engine confidence scores.
4. `validation_results`: Overall validation pass/fail summary and check counts.
5. `validation_checks`: Granular individual checks (`expiry_date_valid`, `mrz_checksum`, `age_consistency`).
6. `tampering_analyses`: Overall ELA score, suspicious flag, and metadata.
7. `tampering_signals`: Individual tamper signals (`photo_region`, `noise_analysis`) linked to heatmap artifacts.
8. `face_verifications`: Facial comparison metrics (model, distance, threshold, match flag).
9. `risk_assessments`: Final AI Arbiter score ($0 - 100$), decision (`APPROVE`/`REVIEW`/`REJECT`), and reasoning summary.
10. `risk_factors`: Individual weighted risk contributions.

---

## 8. Testing, Security Hardening & Accessibility Standards

### 8.1 Automated Test Suites
- **Pytest**: 78 unit and integration tests executing in $< 0.5$ seconds (`test_mrz.py`, `test_validation.py`, `test_field_extraction.py`).
- **Database E2E Verification**: `scripts/test_db_full.py` tests end-to-end Supabase CRUD, schema validation, foreign key cascading, and cleanup.

### 8.2 Frontend Security & Dev Guard
- **`dev-guard.js`**: Intercepts VS Code Live Server WebSocket reload signals during document processing to prevent mid-screening UI reloads.
- **Debounced Execution**: `isScreeningInFlight` and `isLoadingSample` guards prevent double-click API floods.

### 8.3 Accessibility (Lighthouse Audit Compliance)
- **Landmark Architecture**: Standard semantic `<header>`, `<main id="main-content">`, and `<footer>` landmarks.
- **Strict Heading Hierarchy**: Verified sequential descending order ($h1 \to h2 \to h3$) with **0 skipped levels**.

---

## 9. Known Physical Limitations & Future Roadmap

1. **Physical Material Security**: Standard 2D camera images cannot inspect ultraviolet (UV) fluorescent ink, optically variable ink (OVI), infrared (IR) luminescence, or tactile intaglio print.
2. **NFC / ePassport PKI**: Does not currently interface with physical RFID/NFC passport chips; future enterprise modules will incorporate ICAO 9303 PKI chip readers.
3. **3D Liveness Detection**: Currently compares 2D biometric embeddings; integration with passive 3D depth-map liveness is scheduled for Phase 3.

---
*© 2026 VeriGate Core Engineering Team. Dual-licensed under Apache 2.0 and MIT.*
