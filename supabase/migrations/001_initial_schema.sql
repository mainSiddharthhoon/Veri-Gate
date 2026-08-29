-- ============================================================================
-- VeriGate — Initial Schema Migration
-- ============================================================================
-- Creates the complete database schema for the VeriGate screening system.
--
-- Tables:
--   1.  screening_sessions    — Central screening entity
--   2.  documents              — Extracted document fields (1:1 per session)
--   3.  ocr_results            — Raw OCR output (1:1 per session)
--   4.  validation_results     — Validation summary (1:1 per session)
--   5.  validation_checks      — Individual validation checks (N per result)
--   6.  tampering_analyses     — Tampering summary (1:1 per session)
--   7.  tampering_signals      — Individual tampering signals (N per analysis)
--   8.  face_verifications     — Face comparison result (1:1 per session)
--   9.  risk_assessments       — Final risk score (1:1 per session)
--   10. risk_factors           — Individual risk factors (N per assessment)
--   11. reference_documents    — Reference/known-good records (standalone)
--   12. audit_log              — Immutable event log
--
-- DO NOT apply this migration until reviewed and approved.
-- ============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ============================================================================
-- 1. screening_sessions
-- ============================================================================
-- The central entity. One row = one complete screening run.
-- All analysis tables link back here via session_id.
-- ============================================================================

CREATE TABLE screening_sessions (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    status           TEXT        NOT NULL DEFAULT 'pending'
                                 CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    document_type    TEXT        NOT NULL DEFAULT 'passport'
                                 CHECK (document_type IN ('passport', 'visa', 'national_id', 'driving_license', 'permit')),
    operator_id      TEXT,                              -- Plain text for MVP (no auth)
    operator_notes   TEXT,
    document_image_path TEXT     NOT NULL,               -- Supabase Storage path to original document
    person_image_path   TEXT     NOT NULL,               -- Supabase Storage path to live/selfie photo
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at     TIMESTAMPTZ                         -- When the screening finished
);

COMMENT ON TABLE screening_sessions IS 'Central screening entity. One row per screening run.';
COMMENT ON COLUMN screening_sessions.document_image_path IS 'Supabase Storage path to the original uploaded document image.';
COMMENT ON COLUMN screening_sessions.person_image_path IS 'Supabase Storage path to the uploaded live/selfie photo.';


-- ============================================================================
-- 2. documents
-- ============================================================================
-- Structured data extracted from the screened document.
-- Core passport fields are explicit columns for queryability.
-- additional_fields JSONB handles document-type-specific extras.
-- ============================================================================

CREATE TABLE documents (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id       UUID        NOT NULL UNIQUE
                                 REFERENCES screening_sessions(id) ON DELETE CASCADE,
    document_type    TEXT        NOT NULL
                                 CHECK (document_type IN ('passport', 'visa', 'national_id', 'driving_license', 'permit')),
    document_number  TEXT,
    issuing_country  TEXT,                               -- ISO 3166-1 alpha-3
    nationality      TEXT,                               -- ISO 3166-1 alpha-3
    surname          TEXT,
    given_names      TEXT,
    date_of_birth    DATE,
    sex              TEXT        CHECK (sex IN ('M', 'F', 'X')),
    date_of_issue    DATE,
    date_of_expiry   DATE,
    mrz_line_1       TEXT,                               -- Raw MRZ line 1
    mrz_line_2       TEXT,                               -- Raw MRZ line 2
    mrz_parsed       JSONB,                              -- Full parsed MRZ structure
    additional_fields JSONB,                             -- Document-type-specific extras
    document_photo_path TEXT,                            -- Storage path to face extracted from document
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE documents IS 'Extracted document fields. One row per screening session.';
COMMENT ON COLUMN documents.mrz_line_1 IS 'Raw MRZ line 1 as read from the document.';
COMMENT ON COLUMN documents.mrz_parsed IS 'Parsed MRZ fields as structured JSON.';
COMMENT ON COLUMN documents.additional_fields IS 'Catch-all JSONB for document-type-specific fields (visa category, permit type, etc.).';


-- ============================================================================
-- 3. ocr_results
-- ============================================================================
-- Raw OCR output preserved as evidence. One row per session.
-- ============================================================================

CREATE TABLE ocr_results (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id              UUID        NOT NULL UNIQUE
                                        REFERENCES screening_sessions(id) ON DELETE CASCADE,
    engine                  TEXT        NOT NULL DEFAULT 'paddleocr',
    raw_text                TEXT,                        -- Full raw OCR text
    raw_blocks              JSONB,                       -- Structured output: bounding boxes, confidence per block
    confidence_score        REAL        CHECK (confidence_score >= 0 AND confidence_score <= 1),
    processing_time_ms      INTEGER,
    preprocessed_image_path TEXT,                        -- Storage path to image fed to OCR
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE ocr_results IS 'Raw OCR output preserved as evidence. One row per session.';


-- ============================================================================
-- 4. validation_results
-- ============================================================================
-- Summary of document field validation. One row per session.
-- Individual checks are in validation_checks.
-- ============================================================================

CREATE TABLE validation_results (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id       UUID        NOT NULL UNIQUE
                                 REFERENCES screening_sessions(id) ON DELETE CASCADE,
    is_valid         BOOLEAN     NOT NULL DEFAULT false,
    checks_passed    INTEGER     NOT NULL DEFAULT 0,
    checks_failed    INTEGER     NOT NULL DEFAULT 0,
    checks_warned    INTEGER     NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE validation_results IS 'Validation summary. One row per session.';


-- ============================================================================
-- 5. validation_checks
-- ============================================================================
-- Individual validation checks (e.g., "MRZ checksum valid", "document not expired").
-- Many checks per validation_result.
-- ============================================================================

CREATE TABLE validation_checks (
    id                    UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    validation_result_id  UUID    NOT NULL
                                  REFERENCES validation_results(id) ON DELETE CASCADE,
    check_name            TEXT    NOT NULL,               -- e.g., 'mrz_checksum', 'expiry_date_valid'
    check_category        TEXT    NOT NULL                -- e.g., 'mrz', 'dates', 'fields', 'database', 'format'
                                  CHECK (check_category IN ('mrz', 'dates', 'fields', 'database', 'format')),
    status                TEXT    NOT NULL
                                  CHECK (status IN ('passed', 'failed', 'warning', 'skipped')),
    expected_value        TEXT,
    actual_value          TEXT,
    message               TEXT,                           -- Human-readable explanation
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE validation_checks IS 'Individual validation checks. Many per validation_result.';


-- ============================================================================
-- 6. tampering_analyses
-- ============================================================================
-- Summary of document tampering analysis. One row per session.
-- Individual signals are in tampering_signals.
-- ============================================================================

CREATE TABLE tampering_analyses (
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id         UUID        NOT NULL UNIQUE
                                   REFERENCES screening_sessions(id) ON DELETE CASCADE,
    tamper_score       REAL        NOT NULL DEFAULT 0.0
                                   CHECK (tamper_score >= 0 AND tamper_score <= 1),
    is_suspicious      BOOLEAN     NOT NULL DEFAULT false,
    analysis_metadata  JSONB,                             -- Engine versions, parameters used
    processing_time_ms INTEGER,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE tampering_analyses IS 'Tampering analysis summary. One row per session.';


-- ============================================================================
-- 7. tampering_signals
-- ============================================================================
-- Individual tampering evidence signals.
-- Many signals per tampering_analysis.
-- ============================================================================

CREATE TABLE tampering_signals (
    id                     UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    tampering_analysis_id  UUID    NOT NULL
                                   REFERENCES tampering_analyses(id) ON DELETE CASCADE,
    signal_type            TEXT    NOT NULL
                                   CHECK (signal_type IN (
                                       'metadata', 'photo_region', 'text_manipulation',
                                       'copy_move', 'noise_analysis', 'edge_analysis'
                                   )),
    signal_name            TEXT    NOT NULL,               -- e.g., 'ela_anomaly', 'photo_splice_detected'
    score                  REAL    NOT NULL
                                   CHECK (score >= 0 AND score <= 1),
    is_suspicious          BOOLEAN NOT NULL DEFAULT false,
    details                JSONB,                          -- Signal-specific structured output
    evidence_image_path    TEXT,                           -- Storage path to evidence visualization
    message                TEXT,                           -- Human-readable description
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE tampering_signals IS 'Individual tampering evidence signals. Many per analysis.';


-- ============================================================================
-- 8. face_verifications
-- ============================================================================
-- Face comparison result between the document photo and the live photo.
-- One row per session.
--
-- distance/threshold/is_match come directly from DeepFace.
-- No derived "confidence" — the application layer can compute that if needed.
-- ============================================================================

CREATE TABLE face_verifications (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID        NOT NULL UNIQUE
                                    REFERENCES screening_sessions(id) ON DELETE CASCADE,
    model_name          TEXT        NOT NULL DEFAULT 'Facenet512',
    distance            REAL,                              -- Raw distance from DeepFace
    distance_metric     TEXT,                              -- 'cosine', 'euclidean', 'euclidean_l2'
    threshold           REAL,                              -- Model-specific threshold used
    is_match            BOOLEAN     NOT NULL DEFAULT false,
    document_face_path  TEXT,                              -- Storage path to extracted document face
    person_face_path    TEXT,                              -- Storage path to detected live face
    processing_time_ms  INTEGER,
    error_message       TEXT,                              -- If face detection/comparison failed
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE face_verifications IS 'Face comparison result. One row per session.';
COMMENT ON COLUMN face_verifications.distance IS 'Raw distance/dissimilarity from DeepFace. Lower = more similar.';
COMMENT ON COLUMN face_verifications.threshold IS 'Model-specific threshold. is_match = (distance < threshold).';


-- ============================================================================
-- 9. risk_assessments
-- ============================================================================
-- Final fused risk result. One row per session.
-- Individual contributing factors are in risk_factors.
-- ============================================================================

CREATE TABLE risk_assessments (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id       UUID        NOT NULL UNIQUE
                                 REFERENCES screening_sessions(id) ON DELETE CASCADE,
    risk_score       REAL        NOT NULL
                                 CHECK (risk_score >= 0 AND risk_score <= 100),
    risk_level       TEXT        NOT NULL
                                 CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    decision         TEXT        NOT NULL
                                 CHECK (decision IN ('approve', 'review', 'reject')),
    summary          TEXT,                                -- Human-readable summary
    scoring_config   JSONB,                               -- Snapshot of weights/thresholds used
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE risk_assessments IS 'Final fused risk result. One row per session.';
COMMENT ON COLUMN risk_assessments.scoring_config IS 'Snapshot of the scoring weights/thresholds used, for reproducibility.';


-- ============================================================================
-- 10. risk_factors
-- ============================================================================
-- Individual factors contributing to the risk score.
-- Many factors per risk_assessment.
-- ============================================================================

CREATE TABLE risk_factors (
    id                  UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_assessment_id  UUID    NOT NULL
                                REFERENCES risk_assessments(id) ON DELETE CASCADE,
    factor_source       TEXT    NOT NULL
                                CHECK (factor_source IN ('validation', 'tampering', 'face_verification', 'database_check')),
    factor_name         TEXT    NOT NULL,                   -- e.g., 'document_expired', 'face_mismatch'
    weight              REAL    NOT NULL,                   -- Weight used in this scoring run
    score_contribution  REAL    NOT NULL,                   -- Contribution to total score
    severity            TEXT    NOT NULL
                                CHECK (severity IN ('info', 'low', 'medium', 'high', 'critical')),
    message             TEXT,                               -- Human-readable reason
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE risk_factors IS 'Individual factors contributing to the risk score.';


-- ============================================================================
-- 11. reference_documents
-- ============================================================================
-- Standalone reference/known-good records for database validation.
-- Used during screening to cross-check extracted document data.
-- NOT linked to screening_sessions via FK — this is reference data.
-- ============================================================================

CREATE TABLE reference_documents (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    document_type     TEXT        NOT NULL
                                  CHECK (document_type IN ('passport', 'visa', 'national_id', 'driving_license', 'permit')),
    document_number   TEXT        NOT NULL,
    issuing_country   TEXT,                                -- ISO 3166-1 alpha-3
    holder_surname    TEXT,
    holder_given_names TEXT,
    date_of_birth     DATE,
    date_of_expiry    DATE,
    status            TEXT        NOT NULL DEFAULT 'valid'
                                  CHECK (status IN ('valid', 'expired', 'revoked', 'stolen', 'lost', 'watchlist')),
    metadata          JSONB,                               -- Additional reference data
    source            TEXT,                                -- Where this record came from
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- One canonical record per document
    CONSTRAINT uq_reference_document UNIQUE (document_type, document_number, issuing_country)
);

COMMENT ON TABLE reference_documents IS 'Reference/known-good document records for database validation. Standalone — not FK-linked to sessions.';


-- ============================================================================
-- 12. audit_log
-- ============================================================================
-- Immutable log of screening events for traceability.
-- ============================================================================

CREATE TABLE audit_log (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID        REFERENCES screening_sessions(id) ON DELETE SET NULL,
    event_type  TEXT        NOT NULL,                       -- e.g., 'session_created', 'ocr_completed', 'error'
    event_data  JSONB,                                     -- Event-specific payload
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE audit_log IS 'Immutable event log for screening traceability.';


-- ============================================================================
-- INDEXES
-- ============================================================================

-- screening_sessions
CREATE INDEX idx_sessions_status     ON screening_sessions (status);
CREATE INDEX idx_sessions_created_at ON screening_sessions (created_at DESC);

-- documents
CREATE INDEX idx_documents_document_number ON documents (document_number);
CREATE INDEX idx_documents_nationality     ON documents (nationality);

-- validation_checks
CREATE INDEX idx_val_checks_status ON validation_checks (status);

-- tampering_signals
CREATE INDEX idx_tamp_signals_suspicious ON tampering_signals (is_suspicious);

-- reference_documents
CREATE INDEX idx_ref_docs_lookup ON reference_documents (document_type, document_number, issuing_country);
CREATE INDEX idx_ref_docs_status ON reference_documents (status);

-- audit_log
CREATE INDEX idx_audit_session    ON audit_log (session_id);
CREATE INDEX idx_audit_created_at ON audit_log (created_at DESC);


-- ============================================================================
-- TRIGGER: auto-update updated_at on screening_sessions
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sessions_updated_at
    BEFORE UPDATE ON screening_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_ref_docs_updated_at
    BEFORE UPDATE ON reference_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================
-- RLS is enabled on all tables as a safety baseline.
--
-- IMPORTANT — MVP TEMPORARY POLICIES:
-- The policies below use USING (true) / WITH CHECK (true), which means they
-- allow ALL operations for ANY role. These are NOT real security controls.
-- They exist only so that RLS is structurally enabled and the backend
-- (which uses the Supabase service_role key, bypassing RLS entirely) can
-- operate without friction during early development.
--
-- TODO: Before any production or public-facing deployment, replace these
-- permissive policies with proper role-based or authenticated policies
-- (e.g., restricting access to authenticated users, specific roles, or
-- row-level ownership checks via Supabase Auth).
-- ============================================================================

ALTER TABLE screening_sessions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents           ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_results         ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_results  ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_checks   ENABLE ROW LEVEL SECURITY;
ALTER TABLE tampering_analyses  ENABLE ROW LEVEL SECURITY;
ALTER TABLE tampering_signals   ENABLE ROW LEVEL SECURITY;
ALTER TABLE face_verifications  ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_assessments    ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_factors        ENABLE ROW LEVEL SECURITY;
ALTER TABLE reference_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log           ENABLE ROW LEVEL SECURITY;

-- MVP temporary policies — allow all operations (not real security controls).
-- Replace with authenticated policies before production use. See TODO above.
CREATE POLICY "MVP allow all" ON screening_sessions  FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "MVP allow all" ON documents           FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "MVP allow all" ON ocr_results         FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "MVP allow all" ON validation_results  FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "MVP allow all" ON validation_checks   FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "MVP allow all" ON tampering_analyses  FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "MVP allow all" ON tampering_signals   FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "MVP allow all" ON face_verifications  FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "MVP allow all" ON risk_assessments    FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "MVP allow all" ON risk_factors        FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "MVP allow all" ON reference_documents FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "MVP allow all" ON audit_log           FOR ALL USING (true) WITH CHECK (true);
