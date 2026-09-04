/**
 * ============================================================================
 * VeriGate — Configuration & Shared Constants
 * ============================================================================
 */

const API_BASE = window.VERIGATE_API_BASE || (
  window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? (window.location.port === '8000' ? '' : `${window.location.protocol}//${window.location.hostname}:8000`)
    : window.location.origin
);

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

/* Global session state */
const session = { doc: null, face: null, sessionId: null, report: null };
