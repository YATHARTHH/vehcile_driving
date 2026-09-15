-- Migration: 004_telemetry_policies.up.sql
-- Description: Applies chunk compression policy and 90-day hot operational retention policy

-- 1. 7-Day Chunk Compression Policy
ALTER TABLE telemetry_events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'tenant_id, vehicle_id',
    timescaledb.compress_orderby = 'event_timestamp DESC'
);

SELECT add_compression_policy('telemetry_events', INTERVAL '7 days', if_not_exists => TRUE);

-- 2. Operational Hot Data Retention Policy (drop chunks older than 90 days)
SELECT add_retention_policy('telemetry_events', INTERVAL '90 days', if_not_exists => TRUE);
