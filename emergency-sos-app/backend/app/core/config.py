from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Core Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/emergency_sos"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "emergency_sos"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Google Maps
    GOOGLE_MAPS_API_KEY: str = ""

    # Twilio (SMS)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Firebase Cloud Messaging
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_PRIVATE_KEY: str = ""
    FIREBASE_CLIENT_EMAIL: str = ""

    # App Settings
    APP_NAME: str = "Emergency SOS India"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # CORS Origins
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8001,exp://localhost:19000"

    # Hospital API
    HOSPITAL_AVAILABILITY_API_URL: str = "https://mock-api.example.com/hospital-beds"

    # Ambulance Simulation
    AMBULANCE_UPDATE_INTERVAL_SECONDS: int = 5
    MOCK_AMBULANCE_FLEET_SIZE: int = 10

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
