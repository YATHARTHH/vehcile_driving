import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import Base, engine
from backend.routers import auth, chatbot, insights, route, telemetry, trips, ws_telemetry
from backend.streaming.broker import get_broker
from backend.streaming.hot_state import get_hot_state_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure instance directory exists
    os.makedirs("instance", exist_ok=True)

    # Startup Database Policy:
    # In production and PostgreSQL environments, schema migrations are strictly managed
    # by Alembic (e.g. via 'python scripts/migrate.py upgrade').
    # create_all is permitted ONLY for local SQLite development/testing fallback when explicitly enabled.
    is_sqlite = "sqlite" in settings.DATABASE_URL
    is_dev_test = settings.ENVIRONMENT in ("development", "test")
    if is_sqlite and (is_dev_test or settings.AUTO_CREATE_DEV_TABLES):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("[Database] WARNING: Running Base.metadata.create_all() for local SQLite development only. In production, use 'python scripts/migrate.py upgrade'.")
    else:
        print("[Database] Schema managed by Alembic migrations. Skipping automatic create_all().")

    # Startup event broker
    broker = get_broker()
    await broker.connect()
    print("[Broker] Event broker connected successfully.")

    # Startup Hot State Manager (Phase 8 Real-Time Projection)
    hot_state = await get_hot_state_manager()
    print(f"[HotState] Hot state manager ({settings.HOT_STATE_BACKEND}) initialized.")

    # Startup Streaming Pipeline Workers (Bronze Lake, Validation, and Real-Time Projection)
    worker_tasks = []
    if settings.ENABLE_STREAMING_WORKERS and settings.ENVIRONMENT != "test":
        from backend.streaming.bronze_sink import BronzeSinkWorker
        from backend.streaming.projection_worker import RealtimeProjectionWorker
        from backend.streaming.sessionizer import get_sessionizer
        from backend.streaming.validation_worker import ValidationWorker

        bronze_worker = BronzeSinkWorker(broker)
        validation_worker = ValidationWorker(broker)
        projection_worker = RealtimeProjectionWorker(
            broker=broker,
            hot_state=hot_state,
            ui_interval_seconds=settings.UI_STREAM_INTERVAL_SECONDS,
        )
        sessionizer_worker = get_sessionizer(broker)

        worker_tasks = [
            asyncio.create_task(bronze_worker.run()),
            asyncio.create_task(validation_worker.run()),
            asyncio.create_task(projection_worker.run()),
            asyncio.create_task(sessionizer_worker.run()),
        ]
        print("[Pipeline] Streaming pipeline workers (Bronze, Validation, Realtime Projection, Trip Sessionizer) active.")

    yield

    # Shutdown
    for task in worker_tasks:
        task.cancel()
    if settings.ENABLE_STREAMING_WORKERS and settings.ENVIRONMENT != "test":
        try:
            await sessionizer_worker.stop()
        except Exception:
            pass
    await hot_state.disconnect()
    await broker.disconnect()
    await engine.dispose()
    print("[Lifecycle] HotState, Broker, and Database connections cleanly disposed.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="High-performance async FastAPI backend for FleetTrack Telematics & Analytics Platform",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(trips.router, prefix=settings.API_V1_STR)
app.include_router(insights.router, prefix=settings.API_V1_STR)
app.include_router(route.router, prefix=settings.API_V1_STR)
app.include_router(chatbot.router, prefix=settings.API_V1_STR)
app.include_router(telemetry.router)  # Already includes prefix in router definition
app.include_router(ws_telemetry.router)  # Already includes prefix in router definition


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
