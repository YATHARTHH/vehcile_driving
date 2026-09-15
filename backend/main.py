import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import Base, engine
from backend.routers import auth, chatbot, insights, route, telemetry, trips
from backend.streaming.broker import get_broker


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

    yield

    # Shutdown
    await broker.disconnect()
    await engine.dispose()
    print("[Lifecycle] Broker and Database connections cleanly disposed.")


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
