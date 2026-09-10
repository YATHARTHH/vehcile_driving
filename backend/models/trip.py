from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    trip_date = Column(String(50), index=True)
    distance_km = Column(Float, default=0.0)
    avg_speed_kmph = Column(Float, default=0.0)
    max_speed = Column(Float, default=0.0)
    max_rpm = Column(Integer, default=0)
    fuel_consumed = Column(Float, default=0.0)
    brake_events = Column(Integer, default=0)
    steering_angle = Column(Float, default=0.0)
    angular_velocity = Column(Float, default=0.0)
    gps_path = Column(Text, nullable=True)
    acceleration = Column(Float, default=0.0)
    gear_position = Column(Integer, default=1)
    tire_pressure = Column(Float, default=32.0)
    engine_load = Column(Float, default=0.0)
    throttle_position = Column(Float, default=0.0)
    brake_pressure = Column(Float, default=0.0)
    trip_duration = Column(Float, default=0.0)
    start_location = Column(String(100), nullable=True)
    end_location = Column(String(100), nullable=True)

    # Relationships
    user = relationship("User", back_populates="trips")
    alerts = relationship("Alert", back_populates="trip", cascade="all, delete-orphan")
