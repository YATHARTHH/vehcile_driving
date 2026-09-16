import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "FleetTrack EcoDriving Analytics Platform"
    VERSION: str = "2.1.0"
    API_V1_STR: str = "/api/v1"

    # Security Secrets & Identity
    SECRET_KEY: str = os.getenv("SECRET_KEY", "ecodriving_super_secret_jwt_key_2026_change_in_prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Environment & Deployment Mode
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # "development", "test", "production"
    AUTO_CREATE_DEV_TABLES: bool = os.getenv("AUTO_CREATE_DEV_TABLES", "false").lower() in ("true", "1")

    # Database Configuration (Dual-Mode: TimescaleDB / PostgreSQL with SQLite test fallback)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./instance/trips.db"
    )
    POSTGRES_DATABASE_URL: str = os.getenv(
        "POSTGRES_DATABASE_URL",
        "postgresql+asyncpg://fleettrack_user:fleettrack_secure_dev_password_2026@localhost:5432/fleettrack_telematics"
    )

    # Event Broker Configuration (Redpanda / Kafka vs AsyncQueue)
    BROKER_MODE: str = os.getenv("BROKER_MODE", "auto")  # "redpanda", "async_queue", or "auto"
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    SCHEMA_REGISTRY_URL: str = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")

    # Hot State & Real-Time Projection Policies (Phase 8)
    HOT_STATE_BACKEND: str = os.getenv("HOT_STATE_BACKEND", "auto")  # "auto", "redis", or "memory"
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    UI_STREAM_INTERVAL_SECONDS: float = float(os.getenv("UI_STREAM_INTERVAL_SECONDS", "1.0"))
    WS_AUTH_TIMEOUT_SECONDS: float = float(os.getenv("WS_AUTH_TIMEOUT_SECONDS", "5.0"))
    ENABLE_STREAMING_WORKERS: bool = os.getenv("ENABLE_STREAMING_WORKERS", "true").lower() in ("true", "1")

    # Object Storage & Medallion Data Lake
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadminpassword2026")
    MINIO_BUCKET_NAME: str = os.getenv("MINIO_BUCKET_NAME", "fleettrack-lake")
    LOCAL_LAKE_PATH: str = os.getenv("LOCAL_LAKE_PATH", "./data/lake")

    # Telemetry Streaming & Watermarking Policies
    TELEMETRY_ALLOWED_LATENESS_SECONDS: float = float(os.getenv("TELEMETRY_ALLOWED_LATENESS_SECONDS", "30.0"))
    WATERMARK_STATE_TTL_HOURS: float = float(os.getenv("WATERMARK_STATE_TTL_HOURS", "24.0"))
    MAX_REPLAY_ATTEMPTS: int = int(os.getenv("MAX_REPLAY_ATTEMPTS", "3"))

    # CORS Origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
