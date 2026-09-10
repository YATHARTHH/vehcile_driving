from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from backend.database import get_db
from backend.models.user import User
from backend.models.trip import Trip
from backend.utils.auth import get_current_user
from chatbot.chatbot_logic import VehicleChatbot

router = APIRouter(prefix="/chatbot", tags=["AI Chatbot Assistant"])
chatbot_engine = VehicleChatbot()

class ChatMessageQuery(BaseModel):
    message: str
    conversation_id: Optional[str] = None

@router.post("/query")
async def chatbot_query(
    payload: ChatMessageQuery, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    msg = payload.message.strip()
    if not msg:
        return {"response": "Please enter a message.", "suggestions": []}

    # Fetch recent trip telemetry context for user
    result = await db.execute(
        select(Trip).where(Trip.user_id == current_user.id).order_by(Trip.trip_date.desc()).limit(10)
    )
    recent_trips = result.scalars().all()
    trips_dict = [{column.name: getattr(t, column.name) for column in t.__table__.columns} for t in recent_trips]

    user_data = {
        'recent_trips': trips_dict,
        'vehicle_number': current_user.vehicle_number,
        'user_id': current_user.id
    }

    bot_response = chatbot_engine.get_response(msg, user_data)
    
    # Contextual suggestions
    suggestions = ["Analyze my driving patterns", "How can I improve fuel efficiency?", "Show me maintenance tips"]
    if "fuel" in msg.lower():
        suggestions = ["What's my current fuel efficiency?", "How can I reduce fuel costs?", "Show me eco-driving tips"]
    elif "maintenance" in msg.lower():
        suggestions = ["When is my next service due?", "Check vehicle health status", "Show maintenance schedule"]

    return {
        "response": bot_response,
        "suggestions": suggestions[:3],
        "conversation_id": payload.conversation_id
    }

@router.get("/suggestions")
async def get_initial_suggestions(
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Trip).where(Trip.user_id == current_user.id)
    )
    trips = result.scalars().all()

    if len(trips) > 0:
        suggestions = [
            "Analyze my recent trips",
            "How can I improve my fuel efficiency?",
            "What's my driving score?",
            "Show me cost savings tips",
            "Give me maintenance advice"
        ]
    else:
        suggestions = [
            "What can you help me with?",
            "Give me driving tips",
            "How do I save fuel?",
            "Tell me about safety features",
            "Show maintenance schedule"
        ]
    return {"suggestions": suggestions}

@router.websocket("/ws")
async def websocket_chatbot(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            response = chatbot_engine.get_response(data)
            await websocket.send_json({"response": response})
    except WebSocketDisconnect:
        pass
