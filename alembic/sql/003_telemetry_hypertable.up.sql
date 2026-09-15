-- Migration: 003_telemetry_hypertable.up.sql
-- Description: Enables TimescaleDB extension and converts telemetry_events into a hypertable

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

SELECT create_hypertable(
    'telemetry_events',
    'event_timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);
