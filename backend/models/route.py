from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from backend.database import Base


class SavedRoute(Base):
    __tablename__ = "saved_routes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    route_name = Column(String(100), nullable=False)
    start_location = Column(String(100), nullable=False)
    end_location = Column(String(100), nullable=False)
    route_type = Column(String(50), default="direct")
    distance_km = Column(Float, default=0.0)
    travel_time_minutes = Column(Integer, default=0)
    fuel_consumption = Column(Float, default=0.0)
    fuel_cost = Column(Float, default=0.0)
    efficiency_score = Column(Integer, default=0)
    saved_date = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="saved_routes")
