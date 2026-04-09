from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, init_db, close_db
from app.db.redis import init_redis, close_redis
from app.api import emergency
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    logger.info("Starting Emergency SOS API...")
    try:
        await init_redis()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
    
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Emergency SOS API...")
    await close_redis()
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Emergency SOS response system for India with real-time ambulance tracking",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(emergency.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Emergency SOS response system",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint."""
    try:
        # Check database connection
        await db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "version": settings.APP_VERSION
    }


# Additional utility endpoints
@app.get("/api/v1/hospitals/nearby")
async def get_hospitals_nearby(
    latitude: float,
    longitude: float,
    emergency_type: str = "general",
    radius_km: float = 50.0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get nearby hospitals ranked by distance and rating."""
    from app.services.hospital_service import get_nearby_hospitals
    from app.schemas.schemas import EmergencyType as SchemaEmergencyType
    
    try:
        etype = SchemaEmergencyType(emergency_type.lower())
    except ValueError:
        etype = SchemaEmergencyType.GENERAL
    
    hospitals = await get_nearby_hospitals(
        db=db,
        latitude=latitude,
        longitude=longitude,
        emergency_type=etype,
        radius_km=radius_km,
        limit=limit
    )
    
    return hospitals
