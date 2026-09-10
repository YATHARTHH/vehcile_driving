import re
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from backend.database import get_db
from backend.models.user import User
from backend.models.trip import Trip
from backend.schemas.user import UserCreate, UserResponse, TokenResponse
from backend.utils.auth import hash_password, verify_password, create_access_token, get_current_user
from utils.data_generator import generate_random_trip_data

router = APIRouter(prefix="/auth", tags=["Authentication"])

class ForgotPasswordRequest(BaseModel):
    username: str
    vehicle_number: str
    new_password: str

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    username = payload.username.strip()
    vehicle_number = payload.vehicle_number.strip().upper()
    password = payload.password.strip()

    # Vehicle format validation
    vehicle_pattern = r'^[A-Z]{2}\d{2}[A-Z]{2}\d{4}$'
    if not re.match(vehicle_pattern, vehicle_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vehicle number format. Use standard format like MP09AB1234"
        )

    # Check for existing username or vehicle
    existing_user_query = await db.execute(
        select(User).where((User.username == username) | (User.vehicle_number == vehicle_number))
    )
    existing_user = existing_user_query.scalars().first()
    if existing_user:
        if existing_user.username == username:
            raise HTTPException(status_code=400, detail="Username already registered.")
        else:
            raise HTTPException(status_code=400, detail="Vehicle number already registered.")

    hashed_pw = hash_password(password)
    new_user = User(
        username=username,
        password=hashed_pw,
        vehicle_number=vehicle_number,
        email=payload.email
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Auto-generate 5 initial telemetry trips for the new user
    for _ in range(5):
        t_data = generate_random_trip_data()
        trip_entry = Trip(
            user_id=new_user.id,
            trip_date=t_data['trip_date'],
            distance_km=t_data['distance'],
            avg_speed_kmph=t_data['avg_speed'],
            max_speed=t_data['max_speed'],
            max_rpm=t_data['max_rpm'],
            fuel_consumed=t_data['fuel_consumed'],
            brake_events=t_data['brake_events'],
            steering_angle=t_data['steering_angle'],
            angular_velocity=t_data['angular_velocity'],
            acceleration=t_data['acceleration'],
            gear_position=t_data['gear_position'],
            tire_pressure=t_data['tire_pressure'],
            engine_load=t_data['engine_load'],
            throttle_position=t_data['throttle_position'],
            brake_pressure=t_data['brake_pressure'],
            trip_duration=t_data['trip_duration'],
            start_location=t_data['start_location'],
            end_location=t_data['end_location'],
            gps_path=t_data['gps_path']
        )
        db.add(trip_entry)
    await db.commit()

    # Generate Token
    access_token = create_access_token(data={"sub": new_user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": new_user
    }

@router.post("/login", response_model=TokenResponse)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    username = payload.username.strip()
    vehicle_number = payload.vehicle_number.strip().upper()
    new_password = payload.new_password.strip()

    if not (username and vehicle_number and new_password):
        raise HTTPException(status_code=400, detail="All fields are required.")

    result = await db.execute(
        select(User).where(User.username == username, User.vehicle_number == vehicle_number)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Username and vehicle registration number do not match.")

    user.password = hash_password(new_password)
    await db.commit()
    return {"success": True, "message": "Password reset successfully. Please log in with your new password."}

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user
