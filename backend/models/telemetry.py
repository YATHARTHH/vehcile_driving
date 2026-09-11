from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class TelemetryEvent(Base):
    """
    Authoritative time-series telemetry event table.
    Configured as a TimescaleDB hypertable in PostgreSQL environments.
    Enforces tenant-scoped unique idempotency and payload hash conflict detection.
    """
    __tablename__ = "telemetry_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(50), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_id = Column(String(50), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(String(100), nullable=False, index=True)
    payload_hash = Column(String(64), nullable=False)  # SHA-256 for conflict detection

    event_timestamp = Column(DateTime, nullable=False, index=True)
    ingestion_timestamp = Column(DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False)

    # Data Quality & Lineage Metadata (4-State model flags)
    data_quality_status = Column(String(20), default="VALID", nullable=False)  # VALID, DEGRADED, QUARANTINED
    invalid_reasons = Column(JSON, nullable=True)  # List of violated rules, e.g. ["RPM_OUT_OF_BOUNDS"]
    is_late = Column(Boolean, default=False, nullable=False)
    is_duplicate = Column(Boolean, default=False, nullable=False)
    is_imputed = Column(Boolean, default=False, nullable=False)
    schema_version = Column(String(20), default="v1.0.0", nullable=False)

    # Validated Canonical Telemetry readings
    telemetry_data = Column(JSON, nullable=False)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="telemetry_events")

    # Authoritative Idempotency & Range Query Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "vehicle_id", "event_id", name="uq_tenant_vehicle_event"),
        Index("ix_tenant_vehicle_timestamp", "tenant_id", "vehicle_id", "event_timestamp"),
    )
