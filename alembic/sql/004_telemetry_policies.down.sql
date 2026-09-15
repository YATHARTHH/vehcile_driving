-- Migration: 004_telemetry_policies.down.sql
-- Description: Reverses retention and compression policies

SELECT remove_retention_policy('telemetry_events', if_exists => TRUE);
SELECT remove_compression_policy('telemetry_events', if_exists => TRUE);
ALTER TABLE telemetry_events SET (timescaledb.compress = false);
