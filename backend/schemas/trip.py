
from pydantic import BaseModel


class TripBase(BaseModel):
    trip_date: str | None = None
    distance_km: float = 0.0
    avg_speed_kmph: float = 0.0
    max_speed: float = 0.0
    max_rpm: int = 0
    fuel_consumed: float = 0.0
    brake_events: int = 0
    steering_angle: float = 0.0
    angular_velocity: float = 0.0
    gps_path: str | None = None
    acceleration: float = 0.0
    gear_position: int = 1
    tire_pressure: float = 32.0
    engine_load: float = 0.0
    throttle_position: float = 0.0
    brake_pressure: float = 0.0
    trip_duration: float = 0.0
    start_location: str | None = None
    end_location: str | None = None

class TripCreate(TripBase):
    pass

class TripResponse(TripBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class TripDetailResponse(BaseModel):
    trip: TripResponse
    logic_score: float
    logic_behavior: str
    ml_behavior: str
    ml_confidence: float
    ml_model_used: str
    health_recommendation: str
    maintenance_alerts: list[dict]
