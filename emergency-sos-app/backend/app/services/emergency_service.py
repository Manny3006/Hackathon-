from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload
from typing import Optional, List, Dict, Any
import uuid
import json
from datetime import datetime
from app.models.models import (
    Emergency, EmergencyUpdate, Ambulance, Hospital, User,
    EmergencyType as ModelEmergencyType, EmergencyStatus as ModelEmergencyStatus,
    AmbulanceStatus
)
from app.schemas.schemas import EmergencyStatus as SchemaEmergencyStatus
from app.db.redis import redis_client


async def create_emergency(
    db: AsyncSession,
    user_id: int,
    emergency_type: SchemaEmergencyStatus,
    latitude: float,
    longitude: float,
    description: Optional[str] = None
) -> Emergency:
    """Create a new emergency session."""
    
    # Generate unique tracking token
    tracking_token = str(uuid.uuid4())
    
    # Create emergency record
    emergency = Emergency(
        user_id=user_id,
        emergency_type=ModelEmergencyType(emergency_type.value),
        latitude=latitude,
        longitude=longitude,
        location=f"POINT({longitude} {latitude})",
        description=description,
        tracking_token=tracking_token,
        status=ModelEmergencyStatus.TRIGGERED
    )
    
    db.add(emergency)
    await db.flush()
    await db.refresh(emergency)
    
    # Create initial update entry
    initial_update = EmergencyUpdate(
        emergency_id=emergency.id,
        status=ModelEmergencyStatus.TRIGGERED,
        message="Emergency triggered. Searching for nearby hospitals...",
        latitude=latitude,
        longitude=longitude,
        metadata={"emergency_type": emergency_type.value}
    )
    
    db.add(initial_update)
    await db.commit()
    await db.refresh(emergency)
    
    # Store in Redis for fast access
    await cache_emergency_data(emergency.id, {
        "status": emergency.status.value,
        "latitude": latitude,
        "longitude": longitude,
        "tracking_token": tracking_token
    })
    
    return emergency


async def get_emergency_by_id(db: AsyncSession, emergency_id: int) -> Optional[Emergency]:
    """Get emergency by ID with related data."""
    result = await db.execute(
        select(Emergency)
        .options(
            joinedload(Emergency.user),
            joinedload(Emergency.assigned_hospital),
            joinedload(Emergency.assigned_ambulance)
        )
        .where(Emergency.id == emergency_id)
    )
    return result.scalar_one_or_none()


async def get_emergency_by_token(db: AsyncSession, token: str) -> Optional[Emergency]:
    """Get emergency by tracking token."""
    result = await db.execute(
        select(Emergency)
        .options(
            joinedload(Emergency.user),
            joinedload(Emergency.assigned_hospital),
            joinedload(Emergency.assigned_ambulance)
        )
        .where(Emergency.tracking_token == token)
    )
    return result.scalar_one_or_none()


async def confirm_hospital_and_dispatch(
    db: AsyncSession,
    emergency_id: int,
    hospital_id: int
) -> tuple[Emergency, Ambulance]:
    """Confirm hospital selection and dispatch nearest available ambulance."""
    
    # Get emergency
    emergency = await get_emergency_by_id(db, emergency_id)
    if not emergency:
        raise ValueError(f"Emergency {emergency_id} not found")
    
    # Verify hospital exists
    hospital = await db.get(Hospital, hospital_id)
    if not hospital:
        raise ValueError(f"Hospital {hospital_id} not found")
    
    # Update emergency with hospital assignment
    emergency.assigned_hospital_id = hospital_id
    emergency.status = ModelEmergencyStatus.HOSPITAL_SELECTED
    emergency.confirmed_at = datetime.utcnow()
    
    # Find nearest available ambulance
    ambulance_query = text("""
        SELECT a.id
        FROM ambulances a
        WHERE a.status = 'available'
        ORDER BY ST_Distance(
            a.location,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
        ) ASC
        LIMIT 1
    """)
    
    result = await db.execute(
        ambulance_query,
        {"lon": emergency.longitude, "lat": emergency.latitude}
    )
    ambulance_row = result.first()
    
    if not ambulance_row:
        # No ambulance available - create a mock one
        ambulance = Ambulance(
            vehicle_number=f"AMB-{uuid.uuid4().hex[:6].upper()}",
            driver_name="Mock Driver",
            driver_phone="+919876543210",
            latitude=emergency.latitude + 0.01,  # Start nearby
            longitude=emergency.longitude + 0.01,
            location=f"POINT({emergency.longitude + 0.01} {emergency.latitude + 0.01})",
            status=AmbulanceStatus.DISPATCHED,
            assigned_emergency_id=emergency.id
        )
        db.add(ambulance)
        await db.flush()
        await db.refresh(ambulance)
    else:
        ambulance_id = ambulance_row[0]
        ambulance = await db.get(Ambulance, ambulance_id)
        ambulance.status = AmbulanceStatus.DISPATCHED
        ambulance.assigned_emergency_id = emergency.id
    
    emergency.assigned_ambulance_id = ambulance.id
    emergency.status = ModelEmergencyStatus.AMBULANCE_DISPATCHED
    emergency.ambulance_dispatched_at = datetime.utcnow()
    
    # Create update entry
    dispatch_update = EmergencyUpdate(
        emergency_id=emergency.id,
        status=ModelEmergencyStatus.AMBULANCE_DISPATCHED,
        message=f"Ambulance {ambulance.vehicle_number} dispatched. ETA: 10-15 minutes",
        latitude=emergency.latitude,
        longitude=emergency.longitude,
        metadata={
            "ambulance_id": ambulance.id,
            "ambulance_vehicle": ambulance.vehicle_number,
            "hospital_id": hospital.id,
            "hospital_name": hospital.name
        }
    )
    db.add(dispatch_update)
    
    # Reserve bed at hospital (update Redis cache)
    await reserve_hospital_bed(hospital.id, emergency.id)
    
    # Notify hospital (simulated)
    await notify_hospital(hospital, emergency, ambulance)
    
    await db.commit()
    await db.refresh(emergency)
    await db.refresh(ambulance)
    
    # Cache updated data
    await cache_emergency_data(emergency.id, {
        "status": emergency.status.value,
        "ambulance_id": ambulance.id,
        "hospital_id": hospital.id
    })
    
    return emergency, ambulance


async def update_emergency_status(
    db: AsyncSession,
    emergency_id: int,
    status: SchemaEmergencyStatus,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> EmergencyUpdate:
    """Update emergency status and create timeline entry."""
    
    model_status = ModelEmergencyStatus(status.value)
    
    # Update emergency
    emergency = await get_emergency_by_id(db, emergency_id)
    if not emergency:
        raise ValueError(f"Emergency {emergency_id} not found")
    
    emergency.status = model_status
    
    # Set timestamp based on status
    now = datetime.utcnow()
    if status == SchemaEmergencyStatus.ARRIVED_AT_HOSPITAL:
        emergency.arrived_at_hospital_at = now
    elif status == SchemaEmergencyStatus.COMPLETED:
        emergency.completed_at = now
    
    # Create update entry
    update_entry = EmergencyUpdate(
        emergency_id=emergency_id,
        status=model_status,
        message=message or f"Status updated to {status.value}",
        latitude=latitude or emergency.latitude,
        longitude=longitude or emergency.longitude,
        metadata=metadata or {}
    )
    
    db.add(update_entry)
    await db.commit()
    await db.refresh(update_entry)
    
    # Update Redis cache
    await cache_emergency_data(emergency_id, {
        "status": status.value,
        "latitude": latitude,
        "longitude": longitude
    })
    
    # Publish update via Redis pub/sub for real-time tracking
    await publish_emergency_update(emergency_id, {
        "status": status.value,
        "message": message,
        "timestamp": now.isoformat(),
        "latitude": latitude,
        "longitude": longitude
    })
    
    return update_entry


async def get_emergency_updates(db: AsyncSession, emergency_id: int) -> List[EmergencyUpdate]:
    """Get all updates for an emergency."""
    result = await db.execute(
        select(EmergencyUpdate)
        .where(EmergencyUpdate.emergency_id == emergency_id)
        .order_by(EmergencyUpdate.created_at.asc())
    )
    return result.scalars().all()


async def cache_emergency_data(emergency_id: int, data: Dict[str, Any]):
    """Cache emergency data in Redis for fast access."""
    key = f"emergency:{emergency_id}"
    await redis_client.hset(key, mapping=data)
    await redis_client.expire(key, 3600)  # 1 hour TTL


async def get_cached_emergency_data(emergency_id: int) -> Optional[Dict[str, Any]]:
    """Get cached emergency data from Redis."""
    key = f"emergency:{emergency_id}"
    return await redis_client.hgetall(key)


async def cache_ambulance_location(ambulance_id: int, latitude: float, longitude: float, eta_minutes: int):
    """Cache ambulance location in Redis for real-time tracking."""
    key = f"ambulance:{ambulance_id}:location"
    data = {
        "latitude": latitude,
        "longitude": longitude,
        "eta_minutes": eta_minutes,
        "timestamp": datetime.utcnow().isoformat()
    }
    await redis_client.hset(key, mapping=data)
    await redis_client.expire(key, 300)  # 5 minutes TTL
    
    # Publish to pub/sub channel
    await redis_client.publish(
        f"ambulance:{ambulance_id}",
        json.dumps(data)
    )


async def get_ambulance_location(ambulance_id: int) -> Optional[Dict[str, Any]]:
    """Get cached ambulance location from Redis."""
    key = f"ambulance:{ambulance_id}:location"
    return await redis_client.hgetall(key)


async def publish_emergency_update(emergency_id: int, data: Dict[str, Any]):
    """Publish emergency update to Redis pub/sub."""
    await redis_client.publish(
        f"emergency:{emergency_id}:updates",
        json.dumps(data)
    )


async def reserve_hospital_bed(hospital_id: int, emergency_id: int):
    """Reserve a bed at the hospital (Redis cache)."""
    key = f"hospital:{hospital_id}:beds"
    await redis_client.decr(key)
    await redis_client.set(
        f"hospital:{hospital_id}:reservation:{emergency_id}",
        "reserved",
        ex=3600  # 1 hour reservation
    )


async def notify_hospital(hospital: Hospital, emergency: Emergency, ambulance: Ambulance):
    """
    Notify hospital about incoming emergency.
    
    In production, this would call hospital's API endpoint.
    For now, logs the notification.
    """
    # TODO: Integrate with hospital notification system
    # Example: POST https://hospital-api.example.com/emergency-alert
    print(f"""
    === HOSPITAL NOTIFICATION ===
    Hospital: {hospital.name}
    Emergency ID: {emergency.id}
    Type: {emergency.emergency_type.value}
    Patient Location: {emergency.latitude}, {emergency.longitude}
    Ambulance: {ambulance.vehicle_number}
    ETA: ~10-15 minutes
    Bed Reservation: Confirmed
    ===========================
    """)
