from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.database import get_db
from backend.models.route import SavedRoute
from backend.models.user import User
from backend.schemas.route import (
    RouteOptimizeRequest,
    SavedRouteCreate,
    SavedRouteResponse,
)
from backend.utils.auth import get_current_user
from route_optimization.route_engine import RouteOptimizer

router = APIRouter(prefix="/route", tags=["Route Optimization"])
optimizer = RouteOptimizer()


@router.post("/optimize")
async def optimize_route(
    payload: RouteOptimizeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if len(payload.start_coords) != 2 or len(payload.end_coords) != 2:
        raise HTTPException(status_code=400, detail="Start and End coordinates must contain [latitude, longitude]")

    user_preferences = {
        'priority': payload.priority,
        'fuel_efficiency': 15.0
    }
    user_vehicle_data = {'avg_engine_load': 50}
    user_history = {'avg_fuel_efficiency': 15.0, 'preferred_route_type': payload.priority}

    routes = optimizer.optimize_routes(
        tuple(payload.start_coords),
        tuple(payload.end_coords),
        user_preferences,
        user_vehicle_data
    )
    recommendations = optimizer.get_personalized_recommendations(routes, user_history)

    return {
        "success": True,
        "routes": routes,
        "recommendations": recommendations
    }


@router.post("/save", response_model=SavedRouteResponse, status_code=status.HTTP_201_CREATED)
async def save_route(
    payload: SavedRouteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    saved_route = SavedRoute(
        user_id=current_user.id,
        route_name=payload.route_name,
        start_location=payload.start_location,
        end_location=payload.end_location,
        route_type=payload.route_type,
        distance_km=payload.distance_km,
        travel_time_minutes=payload.travel_time_minutes,
        fuel_consumption=payload.fuel_consumption,
        fuel_cost=payload.fuel_cost,
        efficiency_score=payload.efficiency_score
    )
    db.add(saved_route)
    await db.commit()
    await db.refresh(saved_route)
    return saved_route


@router.get("/saved", response_model=list[SavedRouteResponse])
async def get_saved_routes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SavedRoute).where(SavedRoute.user_id == current_user.id).order_by(SavedRoute.saved_date.desc())
    )
    return result.scalars().all()
