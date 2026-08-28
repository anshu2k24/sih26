-- ============================================================
-- PS26121 eRTMAC-NWIS — PRODUCTION DATABASE SCHEMA v2
-- Compatible with: Supabase PostgreSQL
-- Deploy: Paste into Supabase SQL Editor and run
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- 1. ORGANIZATIONS (Tenant root — foundation for Phase 12)
-- ============================================================
CREATE TABLE IF NOT EXISTS organizations (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT NOT NULL,
    slug         TEXT UNIQUE NOT NULL,  -- e.g. 'equinor-volve'
    license_code TEXT UNIQUE NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 2. USER PROFILES (extends Supabase auth.users)
-- ============================================================
-- Canonical role set (matches rbac.py):
--   ADMIN, DRILLING_ENGINEER, OPERATIONS_ENGINEER, ANALYST, VIEWER
CREATE TABLE IF NOT EXISTS profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id),
    email           TEXT NOT NULL UNIQUE,
    full_name       TEXT,
    role            TEXT NOT NULL DEFAULT 'VIEWER'
                    CHECK (role IN ('ADMIN', 'DRILLING_ENGINEER', 'OPERATIONS_ENGINEER', 'ANALYST', 'VIEWER')),
    is_active       BOOLEAN DEFAULT true,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 3. WELLBORES METADATA
-- ============================================================
CREATE TABLE IF NOT EXISTS wellbores (
    id              TEXT PRIMARY KEY,  -- e.g. '15/9-F-14'
    organization_id UUID REFERENCES organizations(id),
    name            TEXT NOT NULL,
    slot_name       TEXT,
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    spud_date       TIMESTAMPTZ,
    status          TEXT DEFAULT 'ACTIVE',
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 4. VERIFIED HISTORICAL DDR EVENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS historical_ddr_events (
    id                    TEXT PRIMARY KEY,  -- e.g. 'EP_V2_605'
    wellbore_id           TEXT REFERENCES wellbores(id),
    organization_id       UUID REFERENCES organizations(id),
    event_type            TEXT NOT NULL,
    event_domain          TEXT NOT NULL,
    onset_md              DOUBLE PRECISION NOT NULL,
    onset_tvd             DOUBLE PRECISION,
    onset_timestamp       TIMESTAMPTZ,
    primary_evidence      TEXT NOT NULL,
    mitigation_text       TEXT,
    resolution_text       TEXT,
    primary_source_record TEXT NOT NULL,
    is_verified           BOOLEAN DEFAULT true,
    created_at            TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 5. OPERATIONAL ALERTS (Full lifecycle — replaces proximity_alerts)
-- ============================================================
CREATE TABLE IF NOT EXISTS alerts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID REFERENCES organizations(id),
    well_id             TEXT,
    source              TEXT NOT NULL
                        CHECK (source IN ('HISTORICAL_PROXIMITY', 'ML_PREDICTION', 'TELEMETRY_RULE', 'DATA_QUALITY', 'SYSTEM')),
    severity            TEXT NOT NULL
                        CHECK (severity IN ('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status              TEXT NOT NULL DEFAULT 'ACTIVE'
                        CHECK (status IN ('ACTIVE', 'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED', 'DISMISSED')),
    title               TEXT NOT NULL,
    description         TEXT,
    current_md          DOUBLE PRECISION,
    tvd                 DOUBLE PRECISION,
    evidence            TEXT,
    recommended_action  TEXT,
    disclaimer          TEXT DEFAULT 'HISTORICAL OFFSET EVENT — NOT A PREDICTION',
    source_record       TEXT,
    deduplication_key   TEXT,
    -- Lifecycle timestamps and actors
    acknowledged_at     TIMESTAMPTZ,
    acknowledged_by     UUID REFERENCES profiles(id),
    investigating_at    TIMESTAMPTZ,
    investigating_by    UUID REFERENCES profiles(id),
    assigned_to         UUID REFERENCES profiles(id),
    resolved_at         TIMESTAMPTZ,
    resolved_by         UUID REFERENCES profiles(id),
    resolution_summary  TEXT,
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS alerts_org_idx     ON alerts(organization_id);
CREATE INDEX IF NOT EXISTS alerts_well_idx    ON alerts(well_id);
CREATE INDEX IF NOT EXISTS alerts_status_idx  ON alerts(status);
CREATE INDEX IF NOT EXISTS alerts_dedup_idx   ON alerts(deduplication_key);

-- ============================================================
-- 6. ALERT NOTES
-- ============================================================
CREATE TABLE IF NOT EXISTS alert_notes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id        UUID REFERENCES alerts(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id),
    author_id       UUID REFERENCES profiles(id),
    note_text       TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 7. ALERT ESCALATION RULES
-- ============================================================
CREATE TABLE IF NOT EXISTS alert_escalation_rules (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID REFERENCES organizations(id),
    rule_name               TEXT NOT NULL,
    trigger_severity        TEXT CHECK (trigger_severity IN ('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    acknowledge_timeout_min INTEGER DEFAULT 30,
    escalation_role         TEXT CHECK (escalation_role IN ('ADMIN', 'DRILLING_ENGINEER', 'OPERATIONS_ENGINEER', 'ANALYST', 'VIEWER')),
    is_enabled              BOOLEAN DEFAULT true,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 8. NOTIFICATION PREFERENCES (per user)
-- ============================================================
CREATE TABLE IF NOT EXISTS notification_preferences (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID UNIQUE REFERENCES profiles(id) ON DELETE CASCADE,
    email_enabled           BOOLEAN DEFAULT true,
    critical_alerts         BOOLEAN DEFAULT true,
    high_alerts             BOOLEAN DEFAULT true,
    medium_alerts           BOOLEAN DEFAULT false,
    historical_alerts       BOOLEAN DEFAULT false,
    system_notifications    BOOLEAN DEFAULT true,
    report_notifications    BOOLEAN DEFAULT false,
    created_at              TIMESTAMPTZ DEFAULT now(),
    updated_at              TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 9. NOTIFICATION DELIVERIES (email audit trail)
-- ============================================================
CREATE TABLE IF NOT EXISTS notification_deliveries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    alert_id        UUID REFERENCES alerts(id),
    recipient_id    UUID REFERENCES profiles(id),
    recipient_email TEXT NOT NULL,
    subject         TEXT,
    status          TEXT NOT NULL DEFAULT 'QUEUED'
                    CHECK (status IN ('QUEUED', 'SENT', 'FAILED', 'RETRYING')),
    attempt_count   INTEGER DEFAULT 0,
    last_attempted  TIMESTAMPTZ,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 10. IN-APP NOTIFICATION EVENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS notification_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    user_id         UUID REFERENCES profiles(id),
    alert_id        UUID REFERENCES alerts(id),
    title           TEXT NOT NULL,
    body            TEXT,
    is_read         BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 11. UPLOADED DOCUMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID REFERENCES organizations(id),
    filename            TEXT NOT NULL,
    storage_path        TEXT,
    document_type       TEXT,  -- 'PDF', 'TXT', 'CSV', 'DOCX'
    uploaded_by         UUID REFERENCES profiles(id),
    checksum            TEXT,  -- SHA-256 for deduplication
    processing_status   TEXT DEFAULT 'PENDING'
                        CHECK (processing_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    extraction_status   TEXT DEFAULT 'PENDING'
                        CHECK (extraction_status IN ('PENDING', 'EXTRACTED', 'OCR_REQUIRED', 'OCR_UNAVAILABLE', 'FAILED')),
    verification_status TEXT DEFAULT 'PENDING'
                        CHECK (verification_status IN ('PENDING', 'REVIEW_REQUIRED', 'VERIFIED', 'REJECTED')),
    source_metadata     JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 12. EXTRACTED EVENTS FROM DOCUMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS extracted_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID REFERENCES documents(id) ON DELETE CASCADE,
    organization_id     UUID REFERENCES organizations(id),
    well_id             TEXT,
    event_type          TEXT,
    event_domain        TEXT,
    onset_md            DOUBLE PRECISION,
    onset_tvd           DOUBLE PRECISION,
    event_timestamp     TIMESTAMPTZ,
    evidence_text       TEXT,
    mitigation_text     TEXT,
    resolution_text     TEXT,
    confidence          DOUBLE PRECISION,  -- 0.0–1.0, NOT used as truth
    verification_status TEXT NOT NULL DEFAULT 'EXTRACTED'
                        CHECK (verification_status IN ('EXTRACTED', 'REVIEW_REQUIRED', 'VERIFIED', 'REJECTED')),
    verified_by         UUID REFERENCES profiles(id),
    verified_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 13. OPERATIONAL TIMELINE EVENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS timeline_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    well_id         TEXT,
    event_timestamp TIMESTAMPTZ NOT NULL,
    event_type      TEXT NOT NULL,  -- 'TELEMETRY_MILESTONE', 'DDR_EVENT', 'PROXIMITY_ALERT', 'ALERT_ACTION', 'REPORT', 'DOCUMENT_VERIFIED'
    source          TEXT NOT NULL,  -- 'HISTORICAL', 'OPERATIONAL', 'ML', 'ENGINEER'
    md              DOUBLE PRECISION,
    title           TEXT NOT NULL,
    summary         TEXT,
    resource_id     TEXT,
    severity        TEXT,
    actor_id        UUID REFERENCES profiles(id),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS timeline_org_idx    ON timeline_events(organization_id);
CREATE INDEX IF NOT EXISTS timeline_well_idx   ON timeline_events(well_id);
CREATE INDEX IF NOT EXISTS timeline_time_idx   ON timeline_events(event_timestamp DESC);

-- ============================================================
-- 14. REPORTS
-- ============================================================
CREATE TABLE IF NOT EXISTS reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    report_type     TEXT NOT NULL,  -- 'DDR', 'INCIDENT', 'SHIFT_HANDOVER', 'WELL_INTELLIGENCE', 'ALERT_SUMMARY'
    well_id         TEXT,
    title           TEXT NOT NULL,
    generated_by    UUID REFERENCES profiles(id),
    period_start    TIMESTAMPTZ,
    period_end      TIMESTAMPTZ,
    status          TEXT DEFAULT 'GENERATED',
    payload         JSONB,  -- Full report data
    storage_path    TEXT,   -- Optional: if exported to file
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 15. IMMUTABLE AUDIT LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    actor_user_id   UUID REFERENCES profiles(id),
    actor_role      TEXT,
    action          TEXT NOT NULL,
    resource_type   TEXT NOT NULL,
    resource_id     TEXT NOT NULL,
    well_id         TEXT,
    request_id      TEXT,
    ip_address      INET,
    before_state    JSONB,
    after_state     JSONB,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now()
    -- NO updated_at — immutable record
);

CREATE INDEX IF NOT EXISTS audit_org_idx    ON audit_logs(organization_id);
CREATE INDEX IF NOT EXISTS audit_actor_idx  ON audit_logs(actor_user_id);
CREATE INDEX IF NOT EXISTS audit_action_idx ON audit_logs(action);
CREATE INDEX IF NOT EXISTS audit_time_idx   ON audit_logs(created_at DESC);

-- ============================================================
-- ROW-LEVEL SECURITY (RLS)
-- Enable RLS on ALL tenant-scoped tables
-- ============================================================
ALTER TABLE organizations          ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles               ENABLE ROW LEVEL SECURITY;
ALTER TABLE wellbores              ENABLE ROW LEVEL SECURITY;
ALTER TABLE historical_ddr_events  ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_notes            ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_escalation_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_deliveries  ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_events    ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents              ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracted_events       ENABLE ROW LEVEL SECURITY;
ALTER TABLE timeline_events        ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports                ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs             ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- RLS POLICIES
-- ============================================================

-- profiles: Users can read/update ONLY their own profile
CREATE POLICY "profiles_own_read"
    ON profiles FOR SELECT
    USING (id = auth.uid());

CREATE POLICY "profiles_own_update"
    ON profiles FOR UPDATE
    USING (id = auth.uid());

-- ADMIN can read all profiles in their org
CREATE POLICY "profiles_admin_read"
    ON profiles FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles p
            WHERE p.id = auth.uid()
              AND p.role = 'ADMIN'
              AND p.organization_id = profiles.organization_id
        )
    );

-- alerts: Members can read alerts within their org only
CREATE POLICY "alerts_org_read"
    ON alerts FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "alerts_org_insert"
    ON alerts FOR INSERT
    WITH CHECK (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

-- Only DRILLING_ENGINEER, OPERATIONS_ENGINEER, ADMIN can update alerts
CREATE POLICY "alerts_engineer_update"
    ON alerts FOR UPDATE
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles
            WHERE id = auth.uid()
              AND role IN ('ADMIN', 'DRILLING_ENGINEER', 'OPERATIONS_ENGINEER')
        )
    );

-- alert_notes: Read within org, insert within org
CREATE POLICY "alert_notes_org_read"
    ON alert_notes FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "alert_notes_org_insert"
    ON alert_notes FOR INSERT
    WITH CHECK (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

-- notification_preferences: Users own their preferences
CREATE POLICY "notif_prefs_own"
    ON notification_preferences FOR ALL
    USING (user_id = auth.uid());

-- notification_events: Users read their own notifications
CREATE POLICY "notif_events_own_read"
    ON notification_events FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "notif_events_mark_read"
    ON notification_events FOR UPDATE
    USING (user_id = auth.uid());

-- documents: Read/insert within org
CREATE POLICY "documents_org_read"
    ON documents FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "documents_org_insert"
    ON documents FOR INSERT
    WITH CHECK (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

-- Only ADMIN or DRILLING_ENGINEER can verify/reject extracted events
CREATE POLICY "extracted_events_org_read"
    ON extracted_events FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "extracted_events_verify"
    ON extracted_events FOR UPDATE
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles
            WHERE id = auth.uid()
              AND role IN ('ADMIN', 'DRILLING_ENGINEER')
        )
    );

-- timeline_events: Read within org
CREATE POLICY "timeline_org_read"
    ON timeline_events FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

-- reports: Read within org; generate requires GENERATE_REPORTS roles
CREATE POLICY "reports_org_read"
    ON reports FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "reports_org_insert"
    ON reports FOR INSERT
    WITH CHECK (
        organization_id IN (
            SELECT organization_id FROM profiles
            WHERE id = auth.uid()
              AND role IN ('ADMIN', 'DRILLING_ENGINEER', 'OPERATIONS_ENGINEER', 'ANALYST')
        )
    );

-- audit_logs: APPEND-ONLY
-- No UPDATE, no DELETE policies defined → blocked by default
CREATE POLICY "audit_org_read"
    ON audit_logs FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles
            WHERE id = auth.uid()
              AND role IN ('ADMIN', 'DRILLING_ENGINEER', 'OPERATIONS_ENGINEER')
        )
    );

CREATE POLICY "audit_org_insert"
    ON audit_logs FOR INSERT
    WITH CHECK (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );
-- NOTE: No UPDATE policy = UPDATE blocked. No DELETE policy = DELETE blocked.
-- audit_logs is append-only by RLS design.

-- wellbores: Read within org
CREATE POLICY "wellbores_org_read"
    ON wellbores FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

-- historical_ddr_events: Read within org
CREATE POLICY "ddr_events_org_read"
    ON historical_ddr_events FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

-- ============================================================
-- HELPER FUNCTION: Automatically create profile on signup
-- ============================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name, role)
    VALUES (
        new.id,
        new.email,
        COALESCE(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
        COALESCE(new.raw_user_meta_data->>'role', 'VIEWER')
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN new;
END;
$$;

-- Trigger fires after Supabase Auth creates a user
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- SEED: Default organization & dev profile for Volve demo
-- Run this after schema is applied
-- ============================================================
INSERT INTO organizations (id, name, slug, license_code)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Equinor Volve Operations',
    'equinor-volve',
    'VOLVE-DEMO-2026'
)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO profiles (id, organization_id, email, full_name, role)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',
    'dev.engineer@localhost',
    'Dev Engineer (Local)',
    'DRILLING_ENGINEER'
)
ON CONFLICT (id) DO NOTHING;
