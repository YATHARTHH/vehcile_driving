-- Migration: 002_telemetry_schema.up.sql
-- Description: Creates decoupled idempotency ledger and telemetry base table

-- 1. Dedicated Idempotency Ledger (Relational Domain)
CREATE TABLE telemetry_event_ledger (
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    vehicle_id VARCHAR(50) NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    event_id VARCHAR(100) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL,
    first_seen_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (tenant_id, vehicle_id, event_id)
);

CREATE INDEX ix_ledger_event_timestamp ON telemetry_event_ledger (event_timestamp);

-- 2. Telemetry Time-Series Base Table
CREATE TABLE telemetry_events (
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    vehicle_id VARCHAR(50) NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    event_id VARCHAR(100) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL,
    ingestion_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    data_quality_status VARCHAR(20) DEFAULT 'VALID' NOT NULL,
    invalid_reasons JSONB,
    is_late BOOLEAN DEFAULT FALSE NOT NULL,
    is_duplicate BOOLEAN DEFAULT FALSE NOT NULL,
    is_imputed BOOLEAN DEFAULT FALSE NOT NULL,
    schema_version VARCHAR(20) DEFAULT 'v1.0.0' NOT NULL,
    telemetry_data JSONB NOT NULL,
    PRIMARY KEY (tenant_id, vehicle_id, event_id, event_timestamp)
);

CREATE INDEX ix_telemetry_lookup ON telemetry_events (tenant_id, vehicle_id, event_timestamp DESC);
CREATE INDEX ix_telemetry_event_id ON telemetry_events (event_id);
