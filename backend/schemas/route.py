from datetime import datetime

from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: int
    user_id: int
    trip_id: int | None = None
    alert_type: str
    severity: str
    title: str
    message: str
    icon: str
    timestamp: datetime | None = None
    resolved: bool = False

    class Config:
        from_attributes = True

class RouteOptimizeRequest(BaseModel):
    start_coords: list[float]
    end_coords: list[float]
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
    saved_date: datetime | None = None

    class Config:
        from_attributes = True
