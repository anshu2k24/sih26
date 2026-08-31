-- ============================================================
-- eRTMAC-NWIS Cloud Migration — Phase 1: Schema Extensions
-- Run in Supabase SQL Editor AFTER the base schema.sql
-- ============================================================

-- ============================================================
-- 1. NEW TABLE: telemetry_readings
-- Stores USROP sensor data (previously in usrop_clean.parquet)
-- ~199K rows, 15 numeric columns
-- ============================================================
CREATE TABLE IF NOT EXISTS telemetry_readings (
    id              BIGSERIAL PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) DEFAULT '00000000-0000-0000-0000-000000000001',
    well_id         TEXT NOT NULL,
    md              DOUBLE PRECISION NOT NULL,
    tvd             DOUBLE PRECISION,
    rop             DOUBLE PRECISION,
    wob             DOUBLE PRECISION,
    rpm             DOUBLE PRECISION,
    torque          DOUBLE PRECISION,
    hookload        DOUBLE PRECISION,
    spp             DOUBLE PRECISION,
    flow_in         DOUBLE PRECISION,
    mud_density     DOUBLE PRECISION,
    gamma           DOUBLE PRECISION,
    diameter_mm     DOUBLE PRECISION,
    timestamp       TIMESTAMPTZ,
    source          TEXT DEFAULT 'VOLVE_USROP',
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Performance indexes for common access patterns
CREATE INDEX IF NOT EXISTS idx_telemetry_well_md ON telemetry_readings(well_id, md);
CREATE INDEX IF NOT EXISTS idx_telemetry_well_ts ON telemetry_readings(well_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_telemetry_org     ON telemetry_readings(organization_id);

-- ============================================================
-- 2. ALTER wellbores: Add geospatial/operational columns
-- (populated from well_coordinates.json)
-- ============================================================
ALTER TABLE wellbores ADD COLUMN IF NOT EXISTS field TEXT DEFAULT 'Volve';
ALTER TABLE wellbores ADD COLUMN IF NOT EXISTS operator TEXT DEFAULT 'Equinor';
ALTER TABLE wellbores ADD COLUMN IF NOT EXISTS water_depth_m DOUBLE PRECISION DEFAULT 84.0;

-- ============================================================
-- 3. RLS for telemetry_readings
-- ============================================================
ALTER TABLE telemetry_readings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "telemetry_org_read" ON telemetry_readings
    FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM profiles WHERE id = auth.uid()
        )
    );

-- Service role bypasses RLS for backend insert/bulk operations.

-- ============================================================
-- 4. Storage Buckets
-- Create via Supabase Dashboard > Storage > New Bucket:
--   1. Name: "documents", Public: OFF
--   2. Name: "reports", Public: OFF
-- ============================================================

-- ============================================================
-- DONE: Phase 1 Schema Extensions Applied
-- ============================================================
