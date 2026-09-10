from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class AlertResponse(BaseModel):
    id: int
    user_id: int
    trip_id: Optional[int] = None
    alert_type: str
    severity: str
    title: str
    message: str
    icon: str
    timestamp: Optional[datetime] = None
    resolved: bool = False

    class Config:
        from_attributes = True

class RouteOptimizeRequest(BaseModel):
    start_coords: List[float]
    end_coords: List[float]
    priority: str = "balanced"

class SavedRouteCreate(BaseModel):
    route_name: str
    start_location: str
    end_location: str
    route_type: str
    distance_km: float
    travel_time_minutes: int
    fuel_consumption: float
    fuel_cost: float
    efficiency_score: int

class SavedRouteResponse(SavedRouteCreate):
    id: int
    user_id: int
    saved_date: Optional[datetime] = None

    class Config:
        from_attributes = True
