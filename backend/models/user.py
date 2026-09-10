from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    vehicle_number = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    trips = relationship("Trip", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    saved_routes = relationship("SavedRoute", back_populates="user", cascade="all, delete-orphan")
