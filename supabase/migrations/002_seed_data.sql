-- ============================================================================
-- VeriGate — Seed Data (Synthetic Demo Records)
-- ============================================================================
-- Populates the database with realistic demo data for testing and demos.
--
-- Contents:
--   - 5 reference documents (3 valid, 1 stolen, 1 on watchlist)
--   - 1 completed screening session with full analysis pipeline results
--   - 1 pending screening session (no results yet)
--
-- All data is fictional. Document numbers, names, and dates are fabricated.
-- DO NOT apply this migration until reviewed and approved.
-- ============================================================================


-- ============================================================================
-- Reference Documents (standalone lookup data)
-- ============================================================================

INSERT INTO reference_documents (id, document_type, document_number, issuing_country, holder_surname, holder_given_names, date_of_birth, date_of_expiry, status, source) VALUES
    -- Valid passports
    ('a0000001-0000-4000-8000-000000000001', 'passport', 'AB1234567', 'GBR', 'SMITH', 'JAMES EDWARD', '1985-03-15', '2029-07-20', 'valid', 'demo_seed'),
    ('a0000001-0000-4000-8000-000000000002', 'passport', 'CD9876543', 'DEU', 'MUELLER', 'ANNA MARIA', '1990-11-02', '2028-04-10', 'valid', 'demo_seed'),
    ('a0000001-0000-4000-8000-000000000003', 'passport', 'EF5551234', 'FRA', 'DUBOIS', 'PIERRE JEAN', '1978-06-25', '2027-12-01', 'valid', 'demo_seed'),
    -- Stolen passport
    ('a0000001-0000-4000-8000-000000000004', 'passport', 'GH1112233', 'ITA', 'ROSSI', 'MARCO', '1982-01-10', '2030-09-15', 'stolen', 'demo_seed'),
    -- Watchlist entry
    ('a0000001-0000-4000-8000-000000000005', 'passport', 'IJ4445566', 'ESP', 'GARCIA', 'CARLOS LUIS', '1975-08-30', '2028-03-22', 'watchlist', 'demo_seed');


-- ============================================================================
-- Screening Session 1: Completed, low-risk (clean passport)
-- ============================================================================

INSERT INTO screening_sessions (id, status, document_type, operator_id, document_image_path, person_image_path, created_at, updated_at, completed_at) VALUES
    ('b0000001-0000-4000-8000-000000000001', 'completed', 'passport', 'demo_operator',
     'uploads/b0000001-0000-4000-8000-000000000001/document_original.jpg',
     'uploads/b0000001-0000-4000-8000-000000000001/person_original.jpg',
     '2026-08-28T10:00:00Z', '2026-08-28T10:00:12Z', '2026-08-28T10:00:12Z');

-- Extracted document fields
INSERT INTO documents (id, session_id, document_type, document_number, issuing_country, nationality, surname, given_names, date_of_birth, sex, date_of_issue, date_of_expiry, mrz_line_1, mrz_line_2, mrz_parsed, document_photo_path) VALUES
    ('c0000001-0000-4000-8000-000000000001',
     'b0000001-0000-4000-8000-000000000001',
     'passport', 'AB1234567', 'GBR', 'GBR',
     'SMITH', 'JAMES EDWARD',
     '1985-03-15', 'M',
     '2019-07-20', '2029-07-20',
     'P<GBRSMITH<<JAMES<EDWARD<<<<<<<<<<<<<<<<<<<<<',
     'AB12345674GBR8503151M2907201<<<<<<<<<<<<<<04',
     '{"document_type": "P", "country_code": "GBR", "surname": "SMITH", "given_names": "JAMES EDWARD", "document_number": "AB1234567", "nationality": "GBR", "date_of_birth": "850315", "sex": "M", "date_of_expiry": "290720", "check_digits_valid": true}',
     'processed/b0000001-0000-4000-8000-000000000001/document_face_crop.jpg');

-- OCR result
INSERT INTO ocr_results (id, session_id, engine, raw_text, confidence_score, processing_time_ms, preprocessed_image_path) VALUES
    ('d0000001-0000-4000-8000-000000000001',
     'b0000001-0000-4000-8000-000000000001',
     'paddleocr',
     'BRITISH PASSPORT\nUNITED KINGDOM OF GREAT BRITAIN\nAND NORTHERN IRELAND\n\nSurname / Nom\nSMITH\n\nGiven names / Prénoms\nJAMES EDWARD\n\nNationality / Nationalité\nBRITISH CITIZEN\n\nDate of birth / Date de naissance\n15 MAR / MARS 85\n\nSex/Sexe\nM\n\nPlace of birth / Lieu de naissance\nLONDON\n\nDate of issue / Date de délivrance\n20 JUL / JUIL 19\n\nDate of expiry / Date d''expiration\n20 JUL / JUIL 29\n\nPassport No. / No de passeport\nAB1234567\n\nP<GBRSMITH<<JAMES<EDWARD<<<<<<<<<<<<<<<<<<<<<\nAB12345674GBR8503151M2907201<<<<<<<<<<<<<<04',
     0.94,
     1250,
     'processed/b0000001-0000-4000-8000-000000000001/document_preprocessed.jpg');

-- Validation result (all checks passed)
INSERT INTO validation_results (id, session_id, is_valid, checks_passed, checks_failed, checks_warned) VALUES
    ('e0000001-0000-4000-8000-000000000001',
     'b0000001-0000-4000-8000-000000000001',
     true, 5, 0, 0);

INSERT INTO validation_checks (id, validation_result_id, check_name, check_category, status, expected_value, actual_value, message) VALUES
    (gen_random_uuid(), 'e0000001-0000-4000-8000-000000000001', 'mrz_checksum',       'mrz',   'passed', NULL,         NULL,         'MRZ check digits are valid.'),
    (gen_random_uuid(), 'e0000001-0000-4000-8000-000000000001', 'mrz_fields_match',   'mrz',   'passed', NULL,         NULL,         'MRZ fields match VIZ (visual inspection zone) fields.'),
    (gen_random_uuid(), 'e0000001-0000-4000-8000-000000000001', 'expiry_date_valid',  'dates', 'passed', 'not expired', 'not expired', 'Document has not expired.'),
    (gen_random_uuid(), 'e0000001-0000-4000-8000-000000000001', 'issuing_country_valid', 'fields', 'passed', 'GBR',     'GBR',        'Issuing country code is valid ISO 3166-1 alpha-3.'),
    (gen_random_uuid(), 'e0000001-0000-4000-8000-000000000001', 'database_check',     'database', 'passed', 'valid',   'valid',       'Document found in reference database with status: valid.');

-- Tampering analysis (clean)
INSERT INTO tampering_analyses (id, session_id, tamper_score, is_suspicious, analysis_metadata, processing_time_ms) VALUES
    ('f0000001-0000-4000-8000-000000000001',
     'b0000001-0000-4000-8000-000000000001',
     0.08, false,
     '{"engines": ["ela", "noise", "edge"], "opencv_version": "4.9.0"}',
     3200);

INSERT INTO tampering_signals (id, tampering_analysis_id, signal_type, signal_name, score, is_suspicious, message, evidence_image_path) VALUES
    (gen_random_uuid(), 'f0000001-0000-4000-8000-000000000001', 'metadata',      'exif_consistency',    0.05, false, 'EXIF metadata appears consistent.', NULL),
    (gen_random_uuid(), 'f0000001-0000-4000-8000-000000000001', 'photo_region',  'ela_analysis',        0.10, false, 'Error Level Analysis shows uniform compression.', 'evidence/b0000001-0000-4000-8000-000000000001/ela_heatmap.jpg'),
    (gen_random_uuid(), 'f0000001-0000-4000-8000-000000000001', 'noise_analysis', 'noise_consistency',  0.08, false, 'Noise patterns are consistent across the document.', NULL),
    (gen_random_uuid(), 'f0000001-0000-4000-8000-000000000001', 'edge_analysis',  'edge_discontinuity', 0.06, false, 'No edge discontinuities detected near photo region.', NULL);

-- Face verification (match)
INSERT INTO face_verifications (id, session_id, model_name, distance, distance_metric, threshold, is_match, document_face_path, person_face_path, processing_time_ms) VALUES
    ('70000001-0000-4000-8000-000000000001',
     'b0000001-0000-4000-8000-000000000001',
     'Facenet512', 0.32, 'cosine', 0.40, true,
     'processed/b0000001-0000-4000-8000-000000000001/document_face_crop.jpg',
     'processed/b0000001-0000-4000-8000-000000000001/person_face_crop.jpg',
     1800);

-- Risk assessment (low risk — approve)
INSERT INTO risk_assessments (id, session_id, risk_score, risk_level, decision, summary, scoring_config) VALUES
    ('80000001-0000-4000-8000-000000000001',
     'b0000001-0000-4000-8000-000000000001',
     12.0, 'low', 'approve',
     'Document is valid. All checks passed. Face matches. No tampering detected.',
     '{"weights": {"validation": 0.25, "tampering": 0.30, "face_verification": 0.30, "database_check": 0.15}, "thresholds": {"low": 25, "medium": 50, "high": 75}}');

INSERT INTO risk_factors (id, risk_assessment_id, factor_source, factor_name, weight, score_contribution, severity, message) VALUES
    (gen_random_uuid(), '80000001-0000-4000-8000-000000000001', 'validation',        'all_checks_passed',  0.25, 0.0,  'info', 'All validation checks passed.'),
    (gen_random_uuid(), '80000001-0000-4000-8000-000000000001', 'tampering',         'no_tampering',       0.30, 2.4,  'info', 'Tamper score 0.08 — within normal range.'),
    (gen_random_uuid(), '80000001-0000-4000-8000-000000000001', 'face_verification', 'face_match',         0.30, 0.0,  'info', 'Face verification passed (distance 0.32 < threshold 0.40).'),
    (gen_random_uuid(), '80000001-0000-4000-8000-000000000001', 'database_check',    'reference_valid',    0.15, 0.0,  'info', 'Document found in reference database with valid status.');


-- ============================================================================
-- Screening Session 2: Pending (demonstrates an in-progress state)
-- ============================================================================

INSERT INTO screening_sessions (id, status, document_type, operator_id, document_image_path, person_image_path, created_at, updated_at) VALUES
    ('b0000001-0000-4000-8000-000000000002', 'pending', 'passport', 'demo_operator',
     'uploads/b0000001-0000-4000-8000-000000000002/document_original.png',
     'uploads/b0000001-0000-4000-8000-000000000002/person_original.jpg',
     '2026-08-28T11:30:00Z', '2026-08-28T11:30:00Z');


-- ============================================================================
-- Audit log entries for the completed session
-- ============================================================================

INSERT INTO audit_log (session_id, event_type, event_data, created_at) VALUES
    ('b0000001-0000-4000-8000-000000000001', 'session_created',        '{"document_type": "passport"}',                  '2026-08-28T10:00:00Z'),
    ('b0000001-0000-4000-8000-000000000001', 'ocr_completed',          '{"engine": "paddleocr", "confidence": 0.94}',    '2026-08-28T10:00:03Z'),
    ('b0000001-0000-4000-8000-000000000001', 'validation_completed',   '{"is_valid": true, "passed": 5, "failed": 0}',  '2026-08-28T10:00:05Z'),
    ('b0000001-0000-4000-8000-000000000001', 'tampering_completed',    '{"tamper_score": 0.08, "suspicious": false}',    '2026-08-28T10:00:08Z'),
    ('b0000001-0000-4000-8000-000000000001', 'face_verified',          '{"is_match": true, "distance": 0.32}',          '2026-08-28T10:00:10Z'),
    ('b0000001-0000-4000-8000-000000000001', 'risk_assessed',          '{"risk_score": 12.0, "decision": "approve"}',    '2026-08-28T10:00:11Z'),
    ('b0000001-0000-4000-8000-000000000001', 'session_completed',      '{"total_time_ms": 12000}',                       '2026-08-28T10:00:12Z'),
    ('b0000001-0000-4000-8000-000000000002', 'session_created',        '{"document_type": "passport"}',                  '2026-08-28T11:30:00Z');
