# VeriGate — Identity Verification Intelligence

> **Multimodal Identity Verification Engine** combining document field extraction, deterministic validation rules, error-level tampering forensics, and biometric facial comparison — reconciled by Gemma AI into an explainable risk assessment.

---

## 1. What VeriGate Is

**VeriGate** is an open-source, multi-stage identity verification and fraud detection system designed to close the gaps between isolated verification checks. Traditional identity verification tools evaluate OCR, check digits, image compression, and facial comparison in silos, often producing opaque pass/fail scores that obscure critical inconsistencies or generate unexplainable rejections.

VeriGate implements a **7-stage sequential evidence analysis chain**. Each stage extracts and verifies objective signals—from optical typography and ICAO MRZ check digits to pixel-level error differences and 512-dimensional facial embeddings. These forensic findings are then synthesized by **Gemma AI**, which acts as an evidence arbiter to generate an explainable verdict, itemized risk factors, and an auditable risk score.

---

## 2. Actual Architecture & Pipeline

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           INTAKE CONSOLE                               │
  │      Identity Document Image         Presented Person (Upload / Camera)│
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ STAGE 1: PRE-FLIGHT INPUT QUALIFICATION                                │
  │ • Gemma Vision inspects document visibility & framing                  │
  │ • Validates frontal portrait presence & suitability (fails early)      │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ STAGE 2: OPTICAL OCR & FIELD EXTRACTION                                │
  │ • OCR text extraction (pytesseract) & physical glyph segmentation      │
  │ • Structured field normalization: Name, Doc Number, DOB, Expiry        │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ STAGE 3: MRZ CHECK DIGIT VERIFICATION (Conditional)                   │
  │ • Parses Machine Readable Zone when present (ICAO 9303 TD3 format)     │
  │ • Recalculates 7-3-1 weighted Modulo-10 checksums & composite parity   │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ STAGE 4: DETERMINISTIC DOCUMENT VALIDATION                             │
  │ • Calendar arithmetic: DOB in the past, calculated applicant age       │
  │ • Issue date predates expiry; credential active/expired evaluation     │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ STAGE 5: TAMPERING FORENSICS (Error Level Analysis)                    │
  │ • Re-compresses document at fixed JPEG quality (90)                    │
  │ • Computes pixel error difference residuals & face region variance     │
  │ • Generates visual ELA heatmap evidence artifact                       │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ STAGE 6: BIOMETRIC FACE CORRESPONDENCE                                 │
  │ • Extracts 512-dimensional biometric embeddings (Facenet512)           │
  │ • Computes Cosine distance against acceptance threshold (0.40)         │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ STAGE 7: GEMMA AI ARBITRATION & EXPLAINABLE REPORT                     │
  │ • Reconciles objective findings, forensic metrics & visual cues        │
  │ • Synthesizes overall risk score (0–100) & decision (APPROVE/REVIEW/   │
  │   REJECT) with itemized risk factors & explainable narrative           │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                     DYNAMIC RESULTS WORKSTATION                        │
  │ • Real-time animated telemetry report with ELA / Original toggle       │
  │ • One-click JSON audit report export for compliance records            │
  └────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

### Backend
- **Runtime**: Python 3.11+
- **API Framework**: FastAPI & Uvicorn (ASGI)
- **Data Validation & Settings**: Pydantic v2 & Pydantic Settings
- **OCR Engine**: Tesseract OCR (`pytesseract`)
- **Computer Vision & Image Processing**: OpenCV (`cv2`), Pillow (`PIL`), NumPy
- **Biometric Verification**: DeepFace (`Facenet512` model, cosine distance metric)
- **Database & Storage**: Supabase (PostgreSQL client) with graceful local/offline fallback
- **HTTP Client**: HTTPX (async & sync connection pools with timeout handling)

### AI Providers & Vision Models
- **Primary AI Arbiter**: Google Gemma (`gemma-4-31b-it` via Google AI Studio REST API) / Gemini 3.6 Flash via Google GenAI SDK
- **Local Fallback**: Ollama Vision API (`qwen2.5-vl-7b-local` or local multimodal models)
- **Cloud Fallback**: OpenRouter API (`openrouter/free` multimodal endpoint)

### Frontend
- **Architecture**: Single-page application, pure vanilla HTML5, CSS3, ES2022 JavaScript
- **Animations**: GSAP (GreenSock Animation Platform) + ScrollTrigger
- **Camera Capture**: HTML5 `MediaDevices.getUserMedia` API with Canvas frame serialization
- **Asset Serving**: Served directly by the FastAPI backend under `/frontend`

---

## 4. Setup Instructions

### Prerequisites
1. **Python 3.11+** installed and available in your PATH.
2. **Tesseract OCR** installed:
   - **Windows**: Install via [UB-Mannheim Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki) and add to PATH or set `TESSDATA_PREFIX`.
   - **Linux**: `sudo apt-get install tesseract-ocr`
   - **macOS**: `brew install tesseract`

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/mainSiddharthhoon/Veri-Gate.git
cd Veri-Gate

# Create virtual environment
python -m venv backend/venv

# Activate virtual environment
# Windows (PowerShell):
backend\venv\Scripts\Activate.ps1
# Windows (cmd):
backend\venv\Scripts\activate.bat
# Linux / macOS:
source backend/venv/bin/activate
```

### Step 2: Install Python Dependencies
```bash
pip install -r backend/requirements.txt
```

---

## 5. Environment Variables

Create a `.env` file in the project root directory (or copy from `.env.example` if present):

```env
# ---------------------------------------------------------------------------
# VeriGate Environment Configuration
# ---------------------------------------------------------------------------

# Application
APP_NAME=VeriGate
APP_VERSION=0.1.0
DEBUG=false
HOST=127.0.0.1
PORT=8000

# Supabase (Database & Storage)
# Required by schema; if unreachable, services operate in local/memory fallback
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# AI Reasoning — Google AI Studio / Gemini
# Used for Gemma 4 31B IT input qualification and multimodal arbitration
GEMINI_API_KEY=your-google-ai-studio-api-key

# AI Reasoning — Local Vision Fallback (Optional)
VISION_BASE_URL=http://127.0.0.1:11434
VISION_MODEL=qwen2.5-vl-7b-local
VISION_API_KEY=
VISION_TIMEOUT_SECONDS=20.0

# AI Reasoning — OpenRouter Fallback (Optional)
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=openrouter/free
```

---

## 6. How to Run Backend and Frontend

### Starting the Server
Start the Uvicorn ASGI server pointing to the `backend` application directory:

```bash
# From the repository root with virtual environment activated:
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

### Accessing the Web Application
Once the server starts:
- **Web Frontend**: Open your browser at [http://127.0.0.1:8000/frontend/](http://127.0.0.1:8000/frontend/)
- **API Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **API Health Check**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- **Evidence Images**: Static ELA evidence heatmaps are served at `/evidence/`

---

## 7. How Gemma Is Used

VeriGate uses **Gemma** (`gemma-4-31b-it`) across two strategic operational phases:

### Phase 1: Pre-Flight Input Qualification (`qualify_inputs`)
Before executing computationally intensive OCR, MRZ, or DeepFace pipelines, Gemma inspects both uploaded image buffers:
1. **Document Visibility**: Confirms whether Image 1 appears to be a legitimate identity document (passport, national ID, driver's license), checking that text regions and geometry are visible and readable.
2. **Portrait Visibility**: Verifies that Image 2 contains a usable, clear frontal face suitable for biometric feature extraction.
3. **Fail-Early Gating**: Rejects completely blurred, cropped, or irrelevant submissions (e.g. photos of objects, blank backgrounds) early, conserving downstream computing resources.

### Phase 2: Multimodal Evidence Arbitration (`assess_evidence`)
Rather than relying on isolated thresholds, Gemma acts as an **intelligent evidence arbiter**:
- Receives the visual document image, live presented person photo, generated ELA heatmap, extracted OCR fields, MRZ verification status, deterministic validation results, tampering scores, and DeepFace biometric distance.
- Cross-correlates potential contradictions (e.g. valid MRZ checksums but anomalous high-frequency ELA variance around the expiration date, or matching names but mismatched facial biometrics).
- Outputs a **structured Pydantic assessment (`AiAssessment`)** with an explainable verdict, itemized risk factors, and overall risk rating.

### Provider Fallback Order
1. **Primary**: Google AI Studio native REST API (`gemma-4-31b-it`) enforcing strict JSON schema.
2. **Secondary**: Local Ollama Vision API (`VISION_BASE_URL` with models such as `qwen2.5-vl-7b-local`).
3. **Tertiary**: OpenRouter API (`openrouter/free`).
4. **Fatal Error Handling**: Client format errors (HTTP 400) or authentication errors fail immediately without cascading, preventing disguised misconfigurations.

---

## 8. Detailed Verification Pipeline Stages

### Stage 1: Input Qualification
- **Service**: `app.services.ai_reasoning.qualify_inputs`
- Evaluates document and presented selfie image suitability with fail-early gating.

### Stage 2: OCR & Field Extraction
- **Service**: `app.services.ocr_pipeline` & `app.services.field_extraction`
- Preprocesses document images using adaptive thresholding, grayscale conversion, and noise filtering.
- Extracts printed characters with Tesseract OCR.
- Uses typographic heuristic segmenters to parse surname, given names, document number, nationality, date of birth, and date of expiry into a structured identity dictionary.

### Stage 3: MRZ Check Digit Validation
- **Service**: `app.services.mrz`
- Evaluates documents featuring an ICAO 9303 TD3 Machine Readable Zone (2 lines × 44 characters).
- Computes check digits using the standard **7-3-1 weighting algorithm** (Modulo 10) on:
  - Document number + check digit
  - Date of birth (YYMMDD) + check digit
  - Expiry date (YYMMDD) + check digit
  - Personal number + check digit
  - Composite checksum covering all subfields
- Flags discrepancies between OCR visual text and MRZ encoded text.
- *Note: Non-MRZ documents (such as national cards without MRZ) skip this check without failing.*

### Stage 4: Deterministic Document Validation
- **Service**: `app.services.validation`
- Pure, rule-based mathematical and calendar logic with zero hallucination risk:
  - **Date of Birth Past Check**: Ensures birth date is strictly in the past.
  - **Subject Age Calculation**: Accurately computes calendar age in years.
  - **Expiry Status Check**: Confirms expiration date is in the future relative to the current verification date and calculates days remaining.
  - **Issuance Relationship**: Confirms document issue date predates expiration date.
  - **Format Conformance**: Validates document numbering patterns against standard issuing jurisdiction formats.

### Stage 5: Tampering Forensics (Error Level Analysis)
- **Service**: `app.services.tampering_core` & `app.services.tampering_pipeline`
- Re-compresses the document image at a fixed JPEG compression quality (90).
- Computes the absolute difference matrix between the original and recompressed image, scaled by 15×.
- Calculates global variance and localized face-region variance ratios to detect image splicing, cloned fonts, or digital pasting.
- Generates a visual ELA heatmap artifact saved to `/evidence/` for side-by-side inspector review.

### Stage 6: Biometric Facial Comparison
- **Service**: `app.services.face_core.verify_faces`
- Locates document portrait and presented live person using OpenCV / DeepFace detector backends.
- Extracts 512-dimensional facial feature vectors using the **Facenet512** biometric model.
- Evaluates identity correspondence using **Cosine Distance**:
  - Distance < 0.40: High-confidence facial match.
  - Distance ≥ 0.40: Biometric mismatch or inconclusive.

### Stage 7: Risk Scoring & Evidence Arbitration
- **Service**: `app.services.risk_scoring` & `app.services.ai_reasoning`
- Computes a weighted baseline risk score from deterministic validation rules, tampering signals, and biometric distance.
- Gemma synthesizes all inputs to provide the final `APPROVE`, `REVIEW`, or `REJECT` decision accompanied by plain-language justification and itemized risk factors.

---

## 9. Testing Instructions

VeriGate includes comprehensive test suites covering unit logic, parsers, algorithms, and API endpoints.

### Running Tests with Pytest
```bash
# Run the entire test suite:
pytest backend/tests -v

# Run specific unit test suites:
pytest backend/tests/test_mrz.py -v           # MRZ parsing & Mod-10 check digits
pytest backend/tests/test_validation.py -v    # Deterministic date & field rules
pytest backend/tests/test_field_extraction.py -v # Typography & field regexes
pytest backend/tests/test_tampering.py -v     # ELA compression & variance logic
pytest backend/tests/test_face.py -v          # Face verification & distance
pytest backend/tests/test_risk.py -v          # Risk scoring models
```

### Synthetic Test Fixtures Note
> [!NOTE]
> **Synthetic Fixtures Used for Testing**:
> In accordance with strict data privacy and security standards, all test documents located in `backend/tests/test_data/` (including `synthetic_passport.jpg` and `synthetic_passport_tampered.jpg`) and frontend demo samples (`frontend/assets/samples/`) are **100% synthetic, programmatically generated test documents**.
> 
> No real personally identifiable information (PII) or authentic government-issued identity documents are included in this repository.

---

## 10. Known Limitations

While VeriGate provides deep, explainable multimodal verification, the following technical limitations apply:

1. **Physical Security Features**: Standard 2D camera images cannot inspect tactile engraving, ultraviolet (UV) fluorescent ink, optically variable ink (OVI), infrared (IR) luminescence, or physical holograms.
2. **NFC Chip Verification**: VeriGate operates on optical images and does not read or cryptographically verify embedded ICAO 9303 ePassport RFID/NFC chips or PKI digital signatures.
3. **Lighting & Occlusion Dependencies**: Extreme glare, shadows, physical camera blur, or heavy facial occlusions (e.g. face masks, dark sunglasses) may cause biometric comparisons or ELA scans to yield inconclusive results.
4. **Document Type Coverage**: MRZ check-digit verification applies specifically to documents equipped with an ICAO 9303 MRZ (such as passports and TD1/TD2/TD3 travel cards); national ID cards lacking an MRZ rely on optical OCR and deterministic validation rules instead.
5. **AI Network Latency**: When utilizing cloud LLM providers for arbitration (Google AI Studio / OpenRouter), total screening latency depends on outbound network response times.

---

## 11. License

Dual-licensed under the **Apache License 2.0** and the **MIT License**. See `LICENSE` for details.
