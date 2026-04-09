from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db
from app.schemas.schemas import (
    EmergencyTriggerRequest, EmergencyTriggerResponse,
    EmergencyConfirmRequest, EmergencyConfirmResponse,
    EmergencyTrackResponse, AmbulanceLocation,
    EmergencyUpdateRequest, NearbyHospitalsRequest,
    HospitalRanking, ContactNotifyRequest
)
from app.services.emergency_service import (
    create_emergency, get_emergency_by_id, get_emergency_by_token,
    confirm_hospital_and_dispatch, update_emergency_status,
    get_emergency_updates, get_cached_emergency_data,
    cache_ambulance_location, get_ambulance_location
)
from app.services.hospital_service import get_nearby_hospitals, get_hospital_by_id
from app.services.notification_service import notify_emergency_contacts, send_status_update
from app.models.models import Ambulance, AmbulanceStatus
from sqlalchemy import select
import httpx
from app.core.config import settings


router = APIRouter(prefix="/emergency", tags=["Emergency"])


@router.post("/trigger", response_model=EmergencyTriggerResponse)
async def trigger_emergency(
    request: EmergencyTriggerRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger a new emergency SOS.
    
    Returns emergency ID, tracking token, and ranked hospital list.
    """
    # Create emergency session
    emergency = await create_emergency(
        db=db,
        user_id=request.user_id,
        emergency_type=request.emergency_type,
        latitude=request.latitude,
        longitude=request.longitude,
        description=request.description
    )
    
    # Get nearby hospitals with ranking
    hospitals = await get_nearby_hospitals(
        db=db,
        latitude=request.latitude,
        longitude=request.longitude,
        emergency_type=request.emergency_type,
        radius_km=50.0,
        limit=10
    )
    
    return EmergencyTriggerResponse(
        emergency_id=emergency.id,
        tracking_token=emergency.tracking_token,
        status=emergency.status.value,
        hospitals=hospitals,
        message="Emergency triggered successfully. Please select a hospital."
    )


@router.post("/{emergency_id}/confirm", response_model=EmergencyConfirmResponse)
async def confirm_hospital(
    emergency_id: int,
    request: EmergencyConfirmRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Confirm hospital selection and dispatch ambulance.
    """
    try:
        emergency, ambulance = await confirm_hospital_and_dispatch(
            db=db,
            emergency_id=emergency_id,
            hospital_id=request.hospital_id
        )
        
        # Get user's emergency contacts and notify them
        user = emergency.user
        if user and user.emergency_contacts:
            tracking_url = f"{settings.CORS_ORIGINS.split(',')[0]}/tracking/{emergency.tracking_token}"
            
            await notify_emergency_contacts(
                contacts=user.emergency_contacts,
                tracking_url=tracking_url,
                emergency_type=emergency.emergency_type.value,
                location_description=emergency.address or f"{emergency.latitude}, {emergency.longitude}"
            )
        
        # Estimate arrival time (mock calculation)
        estimated_arrival = 12  # minutes
        
        return EmergencyConfirmResponse(
            emergency_id=emergency.id,
            hospital_id=emergency.assigned_hospital_id,
            ambulance_id=ambulance.id,
            status=emergency.status.value,
            estimated_arrival_minutes=estimated_arrival,
            message=f"Ambulance {ambulance.vehicle_number} dispatched. ETA: {estimated_arrival} minutes"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{emergency_id}/track", response_model=EmergencyTrackResponse)
async def track_emergency(
    emergency_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get live tracking information for an emergency.
    
    Returns ambulance location, ETA, and status updates.
    """
    emergency = await get_emergency_by_id(db, emergency_id)
    
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency not found")
    
    # Get cached emergency data from Redis
    cached_data = await get_cached_emergency_data(emergency_id)
    
    # Get ambulance location
    ambulance_data = None
    if emergency.assigned_ambulance_id:
        redis_location = await get_ambulance_location(emergency.assigned_ambulance_id)
        
        if redis_location:
            # Calculate distance and ETA from Google Maps (mock for now)
            eta_minutes = int(redis_location.get("eta_minutes", 10))
            distance_km = round(float(redis_location.get("distance_km", 5.0)), 2)
            
            ambulance_data = AmbulanceLocation(
                latitude=float(redis_location["latitude"]),
                longitude=float(redis_location["longitude"]),
                eta_minutes=eta_minutes,
                distance_km=distance_km
            )
        else:
            # Fallback to database location
            ambulance = emergency.assigned_ambulance
            if ambulance and ambulance.latitude and ambulance.longitude:
                ambulance_data = AmbulanceLocation(
                    latitude=ambulance.latitude,
                    longitude=ambulance.longitude,
                    eta_minutes=10,
                    distance_km=5.0
                )
    
    # Get hospital info
    hospital_data = None
    if emergency.assigned_hospital:
        hospital_data = {
            "id": emergency.assigned_hospital.id,
            "name": emergency.assigned_hospital.name,
            "address": emergency.assigned_hospital.address,
            "phone": emergency.assigned_hospital.phone
        }
    
    # Get recent updates
    updates = await get_emergency_updates(db, emergency_id)
    updates_list = [
        {
            "status": u.status.value,
            "message": u.message,
            "timestamp": u.created_at.isoformat(),
            "latitude": u.latitude,
            "longitude": u.longitude
        }
        for u in updates[-10:]  # Last 10 updates
    ]
    
    # Calculate ETA based on status
    eta_minutes = None
    if emergency.status.value in ["ambulance_dispatched", "en_route_to_patient"]:
        eta_minutes = 12
    elif emergency.status.value == "patient_picked":
        eta_minutes = 8
    elif emergency.status.value == "en_route_to_hospital":
        eta_minutes = ambulance_data.eta_minutes if ambulance_data else None
    
    return EmergencyTrackResponse(
        emergency_id=emergency.id,
        status=emergency.status.value,
        ambulance=ambulance_data,
        hospital=hospital_data,
        eta_minutes=eta_minutes,
        updates=updates_list
    )


@router.post("/{emergency_id}/update")
async def update_emergency(
    emergency_id: int,
    request: EmergencyUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Update emergency status (used by ambulance driver app).
    """
    try:
        update_entry = await update_emergency_status(
            db=db,
            emergency_id=emergency_id,
            status=request.status,
            latitude=request.latitude,
            longitude=request.longitude,
            message=request.message,
            metadata=request.metadata
        )
        
        # If ambulance location is provided, cache it
        if request.latitude and request.longitude:
            emergency = await get_emergency_by_id(db, emergency_id)
            if emergency and emergency.assigned_ambulance_id:
                # Mock ETA calculation
                eta = 10 if request.status.value in ["en_route_to_patient"] else 5
                await cache_ambulance_location(
                    ambulance_id=emergency.assigned_ambulance_id,
                    latitude=request.latitude,
                    longitude=request.longitude,
                    eta_minutes=eta
                )
        
        # Send SMS updates to contacts at key milestones
        if request.status.value in ["ambulance_dispatched", "patient_picked", "arrived_at_hospital"]:
            emergency = await get_emergency_by_id(db, emergency_id)
            if emergency and emergency.user and emergency.user.emergency_contacts:
                for contact in emergency.user.emergency_contacts:
                    phone = contact.get("phone")
                    if phone:
                        await send_status_update(
                            phone_number=phone,
                            status=request.status.value,
                            eta_minutes=10 if request.status.value == "ambulance_dispatched" else None
                        )
        
        return {
            "success": True,
            "emergency_id": emergency_id,
            "new_status": request.status.value,
            "update_id": update_entry.id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/token/{token}/track", response_model=EmergencyTrackResponse)
async def track_emergency_by_token(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Track emergency by public tracking token.
    
    Used for family/friends tracking link.
    """
    emergency = await get_emergency_by_token(db, token)
    
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency not found")
    
    # Reuse the track logic
    return await track_emergency(emergency.id, db)


# Nearby hospitals endpoint (standalone)
@router.get("/hospitals/nearby", response_model=List[HospitalRanking])
async def get_nearby_hospitals_endpoint(
    latitude: float,
    longitude: float,
    emergency_type: str = "general",
    radius_km: float = 50.0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Get ranked list of nearby hospitals.
    """
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
