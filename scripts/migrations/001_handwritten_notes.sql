-- ============================================================
-- PS121 HANDWRITTEN NOTES OCR SYSTEM — MIGRATION 001
-- Adds: handwritten_notes, ocr_runs, ocr_audit_logs, FTS index, and RLS policies
-- Compatible with: Supabase PostgreSQL
-- ============================================================

-- 1. HANDWRITTEN NOTES TABLE
CREATE TABLE IF NOT EXISTS handwritten_notes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID REFERENCES organizations(id),
    title               TEXT NOT NULL,
    raw_ocr_text        TEXT NOT NULL DEFAULT '',
    verified_text       TEXT NOT NULL DEFAULT '',
    source              TEXT DEFAULT 'handwritten',
    source_file_id      TEXT,
    storage_path        TEXT,
    public_url          TEXT,
    ocr_status          TEXT DEFAULT 'UPLOADED'
                        CHECK (ocr_status IN ('UPLOADED', 'PROCESSING', 'COMPLETED', 'FAILED')),
    verification_status TEXT DEFAULT 'NEEDS_REVIEW'
                        CHECK (verification_status IN ('NEEDS_REVIEW', 'VERIFIED', 'REJECTED')),
    confidence          DOUBLE PRECISION,
    confidence_level    TEXT DEFAULT 'UNKNOWN'
                        CHECK (confidence_level IN ('HIGH', 'MEDIUM', 'LOW', 'UNKNOWN')),
    latest_ocr_run_id   UUID,
    structured_data     JSONB DEFAULT '{}',
    metadata            JSONB DEFAULT '{}',
    is_deleted          BOOLEAN DEFAULT false,
    created_by          UUID REFERENCES profiles(id),
    verified_by         UUID REFERENCES profiles(id),
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),
    verified_at         TIMESTAMPTZ
);

-- Full-text search index
CREATE INDEX IF NOT EXISTS handwritten_notes_org_idx ON handwritten_notes(organization_id);
CREATE INDEX IF NOT EXISTS handwritten_notes_status_idx ON handwritten_notes(verification_status);
CREATE INDEX IF NOT EXISTS handwritten_notes_ocr_idx ON handwritten_notes(ocr_status);
CREATE INDEX IF NOT EXISTS handwritten_notes_created_idx ON handwritten_notes(created_at DESC);

-- 2. OCR RUN HISTORY TABLE (Immutable)
CREATE TABLE IF NOT EXISTS ocr_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id             UUID REFERENCES handwritten_notes(id) ON DELETE CASCADE,
    organization_id     UUID REFERENCES organizations(id),
    provider            TEXT NOT NULL,
    model               TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'COMPLETED'
                        CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED')),
    confidence          DOUBLE PRECISION,
    raw_result          JSONB DEFAULT '{}',
    normalized_text     TEXT,
    processing_time_ms  INTEGER DEFAULT 0,
    error               TEXT,
    attempt             INTEGER DEFAULT 1,
    created_at          TIMESTAMPTZ DEFAULT now(),
    completed_at        TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ocr_runs_note_idx ON ocr_runs(note_id);
CREATE INDEX IF NOT EXISTS ocr_runs_org_idx ON ocr_runs(organization_id);

-- 3. OCR AUDIT LOGS TABLE
CREATE TABLE IF NOT EXISTS ocr_audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    note_id         UUID REFERENCES handwritten_notes(id) ON DELETE SET NULL,
    actor_user_id   UUID REFERENCES profiles(id),
    action          TEXT NOT NULL,
    details         JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ocr_audit_note_idx ON ocr_audit_logs(note_id);
CREATE INDEX IF NOT EXISTS ocr_audit_time_idx ON ocr_audit_logs(created_at DESC);

-- 4. ROW-LEVEL SECURITY (RLS)
ALTER TABLE handwritten_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_runs          ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_audit_logs    ENABLE ROW LEVEL SECURITY;

CREATE POLICY "handwritten_notes_org_read"
    ON handwritten_notes FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "handwritten_notes_org_insert"
    ON handwritten_notes FOR INSERT
    WITH CHECK (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "handwritten_notes_org_update"
    ON handwritten_notes FOR UPDATE
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "ocr_runs_org_read"
    ON ocr_runs FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "ocr_runs_org_insert"
    ON ocr_runs FOR INSERT
    WITH CHECK (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "ocr_audit_org_read"
    ON ocr_audit_logs FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "ocr_audit_org_insert"
    ON ocr_audit_logs FOR INSERT
    WITH CHECK (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );
