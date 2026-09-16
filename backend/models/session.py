from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, Index, Integer, JSON, String, Text, text

from backend.database import Base


class TripSessionCheckpoint(Base):
    __tablename__ = "trip_session_checkpoints"

    session_id = Column(String(64), primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    vehicle_id = Column(String(64), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)

    status = Column(String(32), nullable=False, default="ACTIVE", index=True)
    start_event_time = Column(DateTime(timezone=True), nullable=False)
    last_event_time = Column(DateTime(timezone=True), nullable=False)
    last_event_received_at = Column(DateTime(timezone=True), nullable=False)
    last_checkpoint_time = Column(DateTime(timezone=True), nullable=False)

    point_count = Column(Integer, default=0, nullable=False)
    moving_point_count = Column(Integer, default=0, nullable=False)
    distance_km = Column(Float, default=0.0, nullable=False)
    fuel_consumed_l = Column(Float, default=0.0, nullable=False)

    last_speed = Column(Float, default=0.0, nullable=False)
    last_latitude = Column(Float, nullable=True)
    last_longitude = Column(Float, nullable=True)
    start_latitude = Column(Float, nullable=True)
    start_longitude = Column(Float, nullable=True)

    running_aggregates = Column(JSON, nullable=False, default=dict)
    gps_breadcrumbs = Column(JSON, nullable=False, default=list)

    source_partition = Column(Integer, default=0, nullable=False)
    source_offset = Column(Integer, default=-1, nullable=False)
    checkpoint_version = Column(Integer, default=1, nullable=False)

    finalization_attempts = Column(Integer, default=0, nullable=False)
    finalization_started_at = Column(DateTime(timezone=True), nullable=True)
    last_finalization_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "uq_active_session_tenant_vehicle",
            "tenant_id",
            "vehicle_id",
            unique=True,
            sqlite_where=text("status IN ('ACTIVE', 'FINISH_REQUESTED', 'FINALIZING')"),
            postgresql_where=text("status IN ('ACTIVE', 'FINISH_REQUESTED', 'FINALIZING')"),
        ),
    )


class TripOutboxEvent(Base):
    __tablename__ = "trip_outbox_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64), unique=True, index=True, nullable=False)
    event_type = Column(String(64), index=True, nullable=False)
    topic = Column(String(128), index=True, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(32), default="PENDING", index=True, nullable=False)  # PENDING, PUBLISHED, FAILED
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
