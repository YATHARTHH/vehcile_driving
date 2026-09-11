import uuid
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class DLQFailureCategory(str, Enum):
    TRANSIENT_FAILURE = "TRANSIENT_FAILURE"          # Database timeout, Redis down -> Auto retry
    PERMANENT_FAILURE = "PERMANENT_FAILURE"          # Corrupt JSON, impossible RPM -> No auto retry
    CONFLICTING_EVENT = "CONFLICTING_EVENT"          # Reused event_id with different hash -> Audit/quarantine
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED" # Borderline validation -> Admin review


class RawIngressPayload(BaseModel):
    """
    Edge device packet submitted to POST /api/v1/telemetry/ingest.
    Note: tenant_id and fleet_id are NOT accepted here to prevent tenant spoofing.
    They are derived server-side from device credentials.
    """
    event_id: str = Field(..., min_length=1, max_length=100, description="Unique client event UUID")
    event_timestamp: datetime = Field(..., description="Edge sensor UTC timestamp")
    schema_version: str = Field(default="v1.0.0", description="Schema semantic version")
    telemetry: dict[str, Any] = Field(..., description="Raw sensor dictionary")

    model_config = ConfigDict(extra="ignore")


class ValidatedTelemetryEvent(BaseModel):
    """
    Canonical validated event stamped with server-derived identity and data quality metadata.
    """
    event_id: str
    tenant_id: str
    fleet_id: str | None = None
    vehicle_id: str
    event_timestamp: datetime
    ingestion_timestamp: datetime
    payload_hash: str
    schema_version: str = "v1.0.0"

    # Data Quality & Lineage Flags
    data_quality_status: str = "VALID"  # VALID, DEGRADED, QUARANTINED
    invalid_reasons: list[str] = Field(default_factory=list)
    is_late: bool = False
    is_duplicate: bool = False
    is_imputed: bool = False

    # Sensor readings (unmutated by validator)
    telemetry: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class DLQQuarantineEvent(BaseModel):
    """
    Quarantined record envelope routed to telemetry.dlq with comprehensive retry and audit metadata.
    """
    dlq_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_event_id: str
    tenant_id: str
    vehicle_id: str
    failed_at: datetime = Field(default_factory=datetime.utcnow)
    failure_stage: str  # DESERIALIZATION, DYNAMIC_PHYSICAL_VALIDATION, IDEMPOTENCY_CONFLICT, etc.
    failure_category: DLQFailureCategory
    error_code: str
    error_message: str
    retry_count: int = 0
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_retry_at: datetime | None = None
    schema_version: str = "v1.0.0"
    raw_payload: str

    model_config = ConfigDict(from_attributes=True)


class IngestionResponse(BaseModel):
    """
    Standard asynchronous ingestion acknowledgement.
    """
    event_id: str
    status: str = "accepted"
    processing: str = "asynchronous"
    received_at: datetime = Field(default_factory=datetime.utcnow)
