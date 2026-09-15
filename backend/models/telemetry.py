from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    PrimaryKeyConstraint,
    String,
    func,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class TelemetryEventLedger(Base):
    """
    Dedicated Relational Idempotency Ledger table.
    Enforces strict global uniqueness on (tenant_id, vehicle_id, event_id) across all time
    within the 90-day operational replay horizon, decoupled from TimescaleDB hypertable chunking.
    After the 90-day ledger retention window expires, a previously seen event ID may be accepted as a new event.
    """
    __tablename__ = "telemetry_event_ledger"

    tenant_id = Column(String(50), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    vehicle_id = Column(String(50), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    event_id = Column(String(100), nullable=False, primary_key=True)
    payload_hash = Column(String(64), nullable=False)
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    first_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "vehicle_id", "event_id", name="pk_telemetry_event_ledger"),
    )


class TelemetryEvent(Base):
    """
    Authoritative time-series telemetry event hypertable.
    Configured as a TimescaleDB hypertable in PostgreSQL environments.
    Enforces chunk partition locality via composite PK (tenant_id, vehicle_id, event_id, event_timestamp).
    """
    __tablename__ = "telemetry_events"

    tenant_id = Column(String(50), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    vehicle_id = Column(String(50), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    event_id = Column(String(100), nullable=False, primary_key=True)
    event_timestamp = Column(DateTime(timezone=True), nullable=False, primary_key=True)

    payload_hash = Column(String(64), nullable=False)
    ingestion_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    # Pre-ingestion Data Quality & Lineage Metadata (Immutable once inserted)
    data_quality_status = Column(String(20), default="VALID", nullable=False)
    invalid_reasons = Column(JSON, nullable=True)
    is_late = Column(Boolean, default=False, nullable=False)
    is_duplicate = Column(Boolean, default=False, nullable=False)
    is_imputed = Column(Boolean, default=False, nullable=False)
    schema_version = Column(String(20), default="v1.0.0", nullable=False)

    # Validated Canonical Telemetry readings
    telemetry_data = Column(JSON, nullable=False)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="telemetry_events")

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "vehicle_id", "event_id", "event_timestamp", name="pk_telemetry_events"),
        Index("ix_telemetry_lookup", "tenant_id", "vehicle_id", "event_timestamp"),
        Index("ix_telemetry_event_id", "event_id"),
    )
