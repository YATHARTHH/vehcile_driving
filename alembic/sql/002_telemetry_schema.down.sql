-- Migration: 002_telemetry_schema.down.sql
-- Description: Reversible downgrade dropping telemetry_events and telemetry_event_ledger

DROP TABLE IF EXISTS telemetry_events CASCADE;
DROP TABLE IF EXISTS telemetry_event_ledger CASCADE;
