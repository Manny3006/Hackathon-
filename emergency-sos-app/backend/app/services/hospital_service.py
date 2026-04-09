from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_MakePoint, ST_SetSRID
from shapely.geometry import Point
from typing import List, Optional
from app.models.models import Hospital, EmergencyType
from app.schemas.schemas import HospitalRanking, EmergencyType as SchemaEmergencyType


# Mapping from emergency type to hospital specialty requirements
EMERGENCY_SPECIALTY_MAP = {
    SchemaEmergencyType.CARDIAC: ["cardiology", "cardiac"],
    SchemaEmergencyType.STROKE: ["neurology", "stroke"],
    SchemaEmergencyType.TRAUMA: ["trauma", "orthopedic"],
    SchemaEmergencyType.FIRE: ["burns", "trauma"],
    SchemaEmergencyType.ACCIDENT: ["trauma", "orthopedic", "surgery"],
    SchemaEmergencyType.GENERAL: [],
}


async def get_nearby_hospitals(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    emergency_type: SchemaEmergencyType = SchemaEmergencyType.GENERAL,
    radius_km: float = 50.0,
    limit: int = 10
) -> List[HospitalRanking]:
    """
    Query nearby hospitals using PostGIS with weighted ranking.
    
    Ranking factors:
    - Distance (closer = better, weighted 60%)
    - Rating (higher = better, weighted 30%)
    - Specialty match (bonus 10%)
    - Bed availability (tiebreaker)
    """
    
    # Create point for user location
    user_point = f"ST_SetSRID(ST_MakePoint({longitude}, {latitude}), 4326)"
    
    # Get required specialties for this emergency type
    required_specialties = EMERGENCY_SPECIALTY_MAP.get(emergency_type, [])
    
    # Build the query with PostGIS distance calculation
    query = text(f"""
        SELECT 
            h.id,
            h.name,
            h.address,
            h.latitude,
            h.longitude,
            h.specialties,
            h.rating,
            h.total_beds,
            h.available_beds,
            h.has_emergency_ward,
            h.has_trauma_center,
            h.has_cardiology,
            h.has_neurology,
            ST_Distance(
                h.location,
                {user_point}
            ) AS distance_meters
        FROM hospitals h
        WHERE ST_DWithin(
            h.location,
            {user_point},
            {radius_km * 1000}
        )
        ORDER BY distance_meters ASC
        LIMIT {limit * 2}
    """)
    
    result = await db.execute(query)
    hospitals_data = result.fetchall()
    
    if not hospitals_data:
        return []
    
    # Calculate weighted scores
    ranked_hospitals = []
    max_distance = max(h[17] for h in hospitals_data) if hospitals_data else 1
    
    for row in hospitals_data:
        hospital_id, name, address, lat, lon, specialties, rating, total_beds, available_beds, \
        has_emergency, has_trauma, has_cardio, has_neuro, distance_meters = row
        
        distance_km = distance_meters / 1000.0 if distance_meters else 0
        
        # Check specialty match
        has_specialty_match = False
        if required_specialties:
            hospital_specs = [s.lower() for s in (specialties or [])]
            has_specialty_match = any(
                req_spec in hospital_specs 
                for req_spec in required_specialties
            )
        
        # Normalize distance score (0-1, where 1 is best/closest)
        distance_score = 1 - (distance_km / radius_km) if radius_km > 0 else 1
        distance_score = max(0, min(1, distance_score))
        
        # Normalize rating score (0-1, where 1 is best/5 stars)
        rating_score = (rating or 0) / 5.0
        
        # Calculate weighted score
        weighted_score = (
            distance_score * 0.6 +  # 60% weight for distance
            rating_score * 0.3 +     # 30% weight for rating
            (0.1 if has_specialty_match else 0)  # 10% bonus for specialty match
        )
        
        ranked_hospitals.append(HospitalRanking(
            id=hospital_id,
            name=name,
            address=address,
            distance_km=round(distance_km, 2),
            rating=rating or 0,
            specialties=specialties or [],
            available_beds=available_beds or 0,
            has_specialty_match=has_specialty_match,
            weighted_score=round(weighted_score, 3)
        ))
    
    # Sort by weighted score descending
    ranked_hospitals.sort(key=lambda h: h.weighted_score, reverse=True)
    
    return ranked_hospitals[:limit]


async def get_hospital_by_id(db: AsyncSession, hospital_id: int) -> Optional[Hospital]:
    """Get a hospital by ID."""
    result = await db.execute(
        select(Hospital).where(Hospital.id == hospital_id)
    )
    return result.scalar_one_or_none()


async def check_bed_availability(hospital_id: int) -> dict:
    """
    Check real-time bed availability for a hospital.
    
    In production, this would call ABDM/NHA APIs.
    For now, returns mock data with integration point.
    """
    # TODO: Integrate with real ABDM/NHA hospital availability API
    # Example: https://abdm.gov.in/api/hospital-beds/{hospital_id}
    
    return {
        "hospital_id": hospital_id,
        "available_beds": None,  # Will be updated from DB
        "last_updated": None,
        "source": "mock"
    }
