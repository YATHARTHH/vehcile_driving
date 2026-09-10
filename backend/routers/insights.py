from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import Dict, Any, Optional

from backend.database import get_db
from backend.models.user import User
from backend.models.trip import Trip
from backend.utils.auth import get_current_user

from ai_insights import (
    analyze_trip_sentiment, detect_anomalies, predict_maintenance,
    generate_recommendations, predict_fuel_consumption
)

router = APIRouter(prefix="/insights", tags=["AI Insights & Analytics"])

class TripIdRequest(BaseModel):
    trip_id: int

class FuelPredictionRequest(BaseModel):
    route_data: Dict[str, Any]

@router.post("/sentiment")
async def get_trip_sentiment(
    payload: TripIdRequest, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Trip).where(Trip.id == payload.trip_id, Trip.user_id == current_user.id)
    )
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip record not found")
    
    trip_dict = {column.name: getattr(trip, column.name) for column in trip.__table__.columns}
    sentiment = analyze_trip_sentiment(trip_dict)
    return {"success": True, "sentiment": sentiment}

@router.post("/anomaly-detection")
async def get_anomaly_detection(
    payload: TripIdRequest, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    # Fetch Target Trip
    result = await db.execute(
        select(Trip).where(Trip.id == payload.trip_id, Trip.user_id == current_user.id)
    )
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip record not found")

    # Fetch User History
    history_res = await db.execute(
        select(Trip).where(Trip.user_id == current_user.id).order_by(Trip.trip_date.desc()).limit(20)
    )
    history = history_res.scalars().all()

    trip_dict = {column.name: getattr(trip, column.name) for column in trip.__table__.columns}
    history_list = [{column.name: getattr(h, column.name) for column in h.__table__.columns} for h in history]

    anomaly_result = detect_anomalies(trip_dict, history_list)
    return {"success": True, "anomalies": anomaly_result}

@router.get("/predictive-maintenance")
async def get_predictive_maintenance(
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    recent_res = await db.execute(
        select(Trip).where(Trip.user_id == current_user.id).order_by(Trip.trip_date.desc()).limit(1)
    )
    recent_trip = recent_res.scalars().first()

    if not recent_trip:
        raise HTTPException(status_code=400, detail="No telemetry trip data available")

    history_res = await db.execute(
        select(Trip).where(Trip.user_id == current_user.id).order_by(Trip.trip_date.desc()).limit(30)
    )
    history = history_res.scalars().all()

    trip_dict = {column.name: getattr(recent_trip, column.name) for column in recent_trip.__table__.columns}
    history_list = [{column.name: getattr(h, column.name) for column in h.__table__.columns} for h in history]

    maint_result = predict_maintenance(trip_dict, history_list)
    return {"success": True, "maintenance": maint_result}

@router.get("/model-info")
async def get_model_info():
    try:
        from ml_model.model_utils import get_model_summary
        info = get_model_summary()
        if not info:
            return {"success": False, "model_loaded": False, "message": "ML model info not found"}
        return {"success": True, "model_loaded": True, "model_info": info}
    except Exception as e:
        return {"success": False, "model_loaded": False, "error": str(e)}

@router.post("/fuel-prediction")
async def get_fuel_prediction(
    payload: FuelPredictionRequest, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    history_res = await db.execute(
        select(Trip).where(Trip.user_id == current_user.id).order_by(Trip.trip_date.desc()).limit(10)
    )
    history = history_res.scalars().all()

    avg_efficiency = 12.0
    if history:
        effs = [h.distance_km / h.fuel_consumed for h in history if h.fuel_consumed and h.fuel_consumed > 0]
        if effs:
            avg_efficiency = sum(effs) / len(effs)

    user_profile = {'avg_efficiency': avg_efficiency, 'driving_style': 'normal'}
    vehicle_data = {'engine_size': 1.6, 'vehicle_type': 'sedan', 'age_years': 3}

    pred_res = predict_fuel_consumption(payload.route_data, user_profile, vehicle_data)
    return {"success": True, "prediction": pred_res}
