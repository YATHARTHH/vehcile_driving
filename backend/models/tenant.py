from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import relationship

from backend.database import Base


class Tenant(Base):
    """
    Multi-tenant organization root (e.g., FedEx India, DHL Logistics).
    Enforces tenant boundaries and Row-Level Security.
    """
    __tablename__ = "tenants"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    tier = Column(String(20), default="standard")  # enterprise, standard, trial
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    # Relationships
    fleets = relationship("Fleet", back_populates="tenant", cascade="all, delete-orphan")
    vehicles = relationship("Vehicle", back_populates="tenant", cascade="all, delete-orphan")


class Fleet(Base):
    """
    Logical grouping of vehicles within a tenant (e.g. North Zone Depot, Airport Hub).
    """
    __tablename__ = "fleets"

    id = Column(String(50), primary_key=True, index=True)
    tenant_id = Column(String(50), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    region = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="fleets")
    vehicles = relationship("Vehicle", back_populates="fleet")


class Vehicle(Base):
    """
    Physical vehicle asset linked to a tenant and fleet.
    Stores vehicle class, powertrain, and profile config.
    """
    __tablename__ = "vehicles"

    id = Column(String(50), primary_key=True, index=True)  # Plate / Asset ID (e.g. MH12AB1234)
    tenant_id = Column(String(50), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    fleet_id = Column(String(50), ForeignKey("fleets.id", ondelete="SET NULL"), nullable=True, index=True)
    vin = Column(String(17), unique=True, index=True, nullable=True)
    vehicle_class = Column(String(50), default="passenger_car")  # passenger_car, light_commercial, heavy_truck, passenger_ev
    powertrain = Column(String(50), default="ice_petrol")  # ice_petrol, ice_diesel, bev, hybrid

    # Dynamic Profile Config (supported sensors, sensor ranges, max values)
    profile_config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="vehicles")
    fleet = relationship("Fleet", back_populates="vehicles")
    telemetry_events = relationship("TelemetryEvent", back_populates="vehicle")
