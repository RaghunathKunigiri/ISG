from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: str = "development"
    APP_NAME: str = "ISG Progress & Performance Tracker"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "development-secret-key-must-be-min-32-characters-long"
    ALGORITHM: str = "HS256"

    # Token Lifetimes
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Lockout policy
    LOCKOUT_THRESHOLD: int = 5
    LOCKOUT_WINDOW_MINUTES: int = 15
    LOCKOUT_DURATION_MINUTES: int = 30

    # Rate Limiting
    AUTH_RATE_LIMIT: str = "5/minute"
    DEFAULT_RATE_LIMIT: str = "100/minute"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/isg_tracker"
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@localhost:5432/isg_tracker"

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Email / SMTP
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = False
    EMAILS_FROM_EMAIL: str = "notifications@isg-tracker.local"
    EMAILS_FROM_NAME: str = "ISG System"

    # S3 Object Storage
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "tracker-attachments"
    S3_REGION: str = "us-east-1"

    # OIDC SSO
    OIDC_ENABLED: bool = False
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_DISCOVERY_URL: str = ""


settings = Settings()

