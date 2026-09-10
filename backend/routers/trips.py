import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from backend.database import get_db
from backend.models.user import User
from backend.models.trip import Trip
from backend.models.alert import Alert
from backend.schemas.trip import TripResponse, TripDetailResponse
from backend.utils.auth import get_current_user

from ml_model.driving_logic import calculate_driving_score
from ml_model.maintenance_logic import build_alerts, get_health_recommendation

# ML Loader
try:
    from ml_model.model_utils import load_artifacts, predict_behavior
    ml_model_obj, scaler_obj, le_obj, model_info_obj = load_artifacts()
    ML_MODEL_LOADED = True
except Exception as e:
    logging.warning(f"ML Pipeline connection warning: {e}")
    ML_MODEL_LOADED = False
    ml_model_obj = scaler_obj = le_obj = model_info_obj = None

router = APIRouter(prefix="/trips", tags=["Trips Telemetry"])

@router.get("", response_model=List[TripResponse])
async def get_user_trips(
    limit: int = 15, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Trip)
        .where(Trip.user_id == current_user.id)
        .order_by(Trip.trip_date.desc())
        .limit(limit)
    )
    trips = result.scalars().all()
    return trips

@router.get("/{trip_id}", response_model=TripDetailResponse)
async def get_trip_detail(
    trip_id: int, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    # IDOR Security Protection: Query filtered explicitly by user_id
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.user_id == current_user.id)
    )
    trip = result.scalars().first()

    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Trip record not found or access denied."
        )

    # Convert ORM to dict for logic modules
    trip_dict = {
        "id": trip.id,
        "avg_speed_kmph": trip.avg_speed_kmph or 0.0,
        "max_speed": trip.max_speed or 0.0,
        "max_rpm": trip.max_rpm or 0,
        "fuel_consumed": trip.fuel_consumed or 0.0,
        "brake_events": trip.brake_events or 0,
        "steering_angle": trip.steering_angle or 0.0,
        "angular_velocity": trip.angular_velocity or 0.0,
        "acceleration": trip.acceleration or 0.0,
        "gear_position": trip.gear_position or 1,
        "tire_pressure": trip.tire_pressure or 32.0,
        "engine_load": trip.engine_load or 0.0,
        "throttle_position": trip.throttle_position or 0.0,
        "brake_pressure": trip.brake_pressure or 0.0,
        "trip_duration": trip.trip_duration or 0.0,
        "distance_km": trip.distance_km or 0.0
    }

    # Heuristic score calculation
    logic_behavior, logic_score = calculate_driving_score(
        trip_dict["avg_speed_kmph"], trip_dict["max_rpm"], trip_dict["brake_events"], trip_dict["steering_angle"],
        trip_dict["angular_velocity"], trip_dict["acceleration"], trip_dict["gear_position"], trip_dict["tire_pressure"],
        trip_dict["engine_load"], trip_dict["throttle_position"], trip_dict["brake_pressure"], trip_dict["trip_duration"]
    )

    # ML behavior prediction
    ml_behavior, ml_confidence, ml_model_used = "Unknown", 0.0, "None"
    if ML_MODEL_LOADED:
        try:
            ml_res = predict_behavior(trip_dict, ml_model_obj, scaler_obj, le_obj, model_info_obj)
            ml_behavior = ml_res.get("behavior_class", "Unknown")
            ml_confidence = ml_res.get("confidence", 0.0)
            ml_model_used = ml_res.get("model_used", "Unknown")
        except Exception as ex:
            logging.error(f"ML prediction error: {ex}")

    # Maintenance alerts
    alerts_list, health_rec = build_alerts(trip_dict)
    
    # Save alerts to DB asynchronously if any
    for alert_item in alerts_list:
        alert_entry = Alert(
            user_id=current_user.id,
            trip_id=trip.id,
            alert_type=alert_item["alert_type"],
            severity=alert_item["severity"],
            title=alert_item["title"],
            message=alert_item["description"],
            icon=alert_item["icon"]
        )
        db.add(alert_entry)
    if alerts_list:
        await db.commit()

    if ml_behavior != "Unknown":
        ml_health = get_health_recommendation(ml_behavior)
        combined_rec = f"{health_rec}\n\n{ml_health}" if ml_health else health_rec
    else:
        combined_rec = health_rec

    return {
        "trip": trip,
        "logic_score": logic_score,
        "logic_behavior": logic_behavior,
        "ml_behavior": ml_behavior,
        "ml_confidence": ml_confidence,
        "ml_model_used": ml_model_used,
        "health_recommendation": combined_rec,
        "maintenance_alerts": alerts_list
    }
