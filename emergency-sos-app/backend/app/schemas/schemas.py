from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class EmergencyType(str, Enum):
    CARDIAC = "cardiac"
    TRAUMA = "trauma"
    STROKE = "stroke"
    FIRE = "fire"
    ACCIDENT = "accident"
    GENERAL = "general"


class EmergencyStatus(str, Enum):
    TRIGGERED = "triggered"
    HOSPITAL_SELECTED = "hospital_selected"
    AMBULANCE_DISPATCHED = "ambulance_dispatched"
    EN_ROUTE_TO_PATIENT = "en_route_to_patient"
    PATIENT_PICKED = "patient_picked"
    EN_ROUTE_TO_HOSPITAL = "en_route_to_hospital"
    ARRIVED_AT_HOSPITAL = "arrived_at_hospital"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AmbulanceStatus(str, Enum):
    AVAILABLE = "available"
    DISPATCHED = "dispatched"
    EN_ROUTE = "en_route"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"


# User Schemas
class EmergencyContact(BaseModel):
    name: str
    phone: str
    relationship: str = "family"


class UserCreate(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    medical_conditions: Optional[str] = None
    emergency_contacts: Optional[List[EmergencyContact]] = []


class UserResponse(BaseModel):
    id: int
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    blood_type: Optional[str] = None
    emergency_contacts: Optional[List[Dict[str, Any]]] = []
    
    class Config:
        from_attributes = True


# Hospital Schemas
class HospitalRanking(BaseModel):
    id: int
    name: str
    address: str
    distance_km: float
    rating: float
    specialties: List[str]
    available_beds: int
    has_specialty_match: bool
    weighted_score: float
    
    class Config:
        from_attributes = True


class HospitalResponse(BaseModel):
    id: int
    name: str
    address: str
    phone: Optional[str] = None
    latitude: float
    longitude: float
    specialties: List[str]
    rating: float
    total_beds: int
    available_beds: int
    has_emergency_ward: bool
    has_trauma_center: bool
    has_cardiology: bool
    has_neurology: bool
    
    class Config:
        from_attributes = True


# Emergency Schemas
class EmergencyTriggerRequest(BaseModel):
    user_id: int
    emergency_type: EmergencyType
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    description: Optional[str] = None


class EmergencyTriggerResponse(BaseModel):
    emergency_id: int
    tracking_token: str
    status: str
    hospitals: List[HospitalRanking]
    message: str


class EmergencyConfirmRequest(BaseModel):
    hospital_id: int


class EmergencyConfirmResponse(BaseModel):
    emergency_id: int
    hospital_id: int
    ambulance_id: int
    status: str
    estimated_arrival_minutes: int
    message: str


class AmbulanceLocation(BaseModel):
    latitude: float
    longitude: float
    heading: Optional[float] = None
    speed_kmph: Optional[float] = None
    eta_minutes: Optional[int] = None
    distance_km: Optional[float] = None


class EmergencyTrackResponse(BaseModel):
    emergency_id: int
    status: str
    ambulance: Optional[AmbulanceLocation] = None
    hospital: Optional[Dict[str, Any]] = None
    eta_minutes: Optional[int] = None
    updates: List[Dict[str, Any]] = []


class EmergencyUpdateRequest(BaseModel):
    status: EmergencyStatus
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


# Contact Notification Schema
class ContactNotifyRequest(BaseModel):
    emergency_id: int
    contacts: List[EmergencyContact]
    tracking_url: str
    message: Optional[str] = None


# Nearby Hospitals Request
class NearbyHospitalsRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    emergency_type: Optional[EmergencyType] = EmergencyType.GENERAL
    radius_km: float = 50.0
    limit: int = 10
