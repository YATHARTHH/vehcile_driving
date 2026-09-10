from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=True, index=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), default="info")
    title = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    icon = Column(String(50), default="fa-car")
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    resolved = Column(Boolean, default=False, index=True)

    # Relationships
    user = relationship("User", back_populates="alerts")
    trip = relationship("Trip", back_populates="alerts")
