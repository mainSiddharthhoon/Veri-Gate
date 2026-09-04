/**
 * ============================================================================
 * VeriGate — Configuration & Shared Constants
 * ============================================================================
 */

const API_BASE = window.VERIGATE_API_BASE || (
  window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : window.location.origin
);

/* Pipeline stages for landing page showcase */
const STAGES = [
  { num: '01', tag: 'INPUT', title: 'Input Qualification', body: 'Gemma checks that the document and presented-person image meet clarity, framing, and resolution standards before processing begins.' },
  { num: '02', tag: 'OCR', title: 'OCR & Field Extraction', body: 'Extracts printed and embedded identity fields — name, dates, document number — establishing the structured baseline for validation.' },
  { num: '03', tag: 'MRZ', title: 'MRZ Validation', body: 'When the document format contains an MRZ, recalculates check digits and verifies parity against optical visual fields.' },
  { num: '04', tag: 'RULES', title: 'Deterministic Validation', body: 'Applies deterministic rules: verifies DOB in the past, calculates applicant age, confirms issue predates expiry, and checks validity status.' },
  { num: '05', tag: 'FORENSICS', title: 'Tampering Forensics', body: 'Error-level analysis (ELA) inspects compression discrepancies across image regions to highlight localized edits or substitutions.' },
  { num: '06', tag: 'FACE', title: 'Face Verification', body: 'Compares the document portrait with the presented person’s image using a dedicated biometric facial embedding model.' },
  { num: '07', tag: 'AI', title: 'Gemma AI Reasoning', body: 'Combines objective validation checks, forensic signals, and visual inspection into an evidence-based risk assessment, decision, and explanation.' },
];

/* Real-time screening pipeline stages */
const PIPELINE_STAGES = [
  { label: 'Input Qualification', sub: 'Checking document and portrait suitability with Gemma' },
  { label: 'OCR & Field Extraction', sub: 'Reading printed and embedded identity fields' },
  { label: 'MRZ Validation', sub: 'Validating check digits when document has an MRZ' },
  { label: 'Deterministic Validation', sub: 'Evaluating DOB, calculated age, and expiry rules' },
  { label: 'Tampering Forensics', sub: 'Error-level analysis for localized compression traces' },
  { label: 'Face Verification', sub: 'Comparing document portrait with presented person' },
  { label: 'Gemma AI Reasoning', sub: 'Evidence reconciliation, risk scoring, and decision' },
];

/* Default upload panel markup */
const DEFAULT_PANEL_CONTENT = {
  doc: `
    <div class="scan-line"></div>
    <div class="panel-icon">
      <svg class="icon" style="width:22px;height:22px;" viewBox="0 0 24 24" fill="none" stroke="var(--crimson-glow)" stroke-width="1.5">
        <rect x="2" y="4" width="20" height="16" rx="2"/>
        <circle cx="8" cy="10" r="1.5"/>
        <path d="M2 16l4-4 4 4 6-6 4 4"/>
      </svg>
    </div>
    <div class="panel-title">Identity Document</div>
    <div class="panel-hint">Passport, national ID card, or driver's licence — front side</div>
    <div class="panel-browse mono">
      <svg class="icon" style="width:12px;height:12px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 16V8m0 0-3 3m3-3 3 3M4 20h16"/>
      </svg>
      DROP FILE OR BROWSE
    </div>
  `,
  face: `
    <div class="scan-line"></div>
    <div class="panel-icon">
      <svg class="icon" style="width:22px;height:22px;" viewBox="0 0 24 24" fill="none" stroke="var(--crimson-glow)" stroke-width="1.5">
        <circle cx="12" cy="9" r="3"/>
        <path d="M6 20c0-3 3-5 6-5s6 2 6 5"/>
        <rect x="2" y="2" width="20" height="20" rx="4"/>
      </svg>
    </div>
    <div class="panel-title">Presented Person</div>
    <div class="panel-hint">A clear, front-facing photo or selfie of the person being verified</div>
    <div class="panel-browse mono">
      <svg class="icon" style="width:12px;height:12px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 16V8m0 0-3 3m3-3 3 3M4 20h16"/>
      </svg>
      DROP FILE OR BROWSE
    </div>
  `,
};

/* Global session state */
const session = { doc: null, face: null, sessionId: null, report: null };
