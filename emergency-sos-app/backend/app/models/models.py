from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
import sqlalchemy as sa
from datetime import datetime
from app.db.session import Base
import enum


class EmergencyType(str, enum.Enum):
    """Types of emergencies supported."""
    CARDIAC = "cardiac"
    TRAUMA = "trauma"
    STROKE = "stroke"
    FIRE = "fire"
    ACCIDENT = "accident"
    GENERAL = "general"


class EmergencyStatus(str, enum.Enum):
    """Status of an emergency session."""
    TRIGGERED = "triggered"
    HOSPITAL_SELECTED = "hospital_selected"
    AMBULANCE_DISPATCHED = "ambulance_dispatched"
    EN_ROUTE_TO_PATIENT = "en_route_to_patient"
    PATIENT_PICKED = "patient_picked"
    EN_ROUTE_TO_HOSPITAL = "en_route_to_hospital"
    ARRIVED_AT_HOSPITAL = "arrived_at_hospital"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AmbulanceStatus(str, enum.Enum):
    """Status of an ambulance."""
    AVAILABLE = "available"
    DISPATCHED = "dispatched"
    EN_ROUTE = "en_route"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"


class User(Base):
    """User model with profile and emergency contacts."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone = Column(String(20), unique=True, index=True, nullable=True)
    name = Column(String(255), nullable=True)
    
    # Medical Information
    blood_type = Column(String(5), nullable=True)
    allergies = Column(Text, nullable=True)
    medical_conditions = Column(Text, nullable=True)
    
    # Emergency Contacts (stored as JSON)
    emergency_contacts = Column(JSON, default=list)
    
    # Location
    home_address = Column(Text, nullable=True)
    home_latitude = Column(Float, nullable=True)
    home_longitude = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=sa.func.now())
    
    # Relationships
    emergencies = relationship("Emergency", back_populates="user", cascade="all, delete-orphan")


class Hospital(Base):
    """Hospital model with PostGIS location."""
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    address = Column(Text, nullable=False)
    phone = Column(String(20), nullable=True)
    
    # Location (PostGIS Point)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location = Column(Geometry('POINT', srid=4326), nullable=False)
    
    # Hospital Details
    specialties = Column(JSON, default=list)  # ['cardiology', 'trauma', 'neurology', etc.]
    rating = Column(Float, default=0.0)  # 0-5 star rating
    total_beds = Column(Integer, default=0)
    available_beds = Column(Integer, default=0)
    
    # Emergency Capabilities
    has_emergency_ward = Column(Boolean, default=True)
    has_trauma_center = Column(Boolean, default=False)
    has_cardiology = Column(Boolean, default=False)
    has_neurology = Column(Boolean, default=False)
    has_pediatrics = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=sa.func.now())
    
    # Relationships
    emergencies = relationship("Emergency", back_populates="assigned_hospital")


class Ambulance(Base):
    """Ambulance model with real-time location tracking."""
    __tablename__ = "ambulances"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_number = Column(String(20), unique=True, nullable=False)
    driver_name = Column(String(255), nullable=True)
    driver_phone = Column(String(20), nullable=True)
    
    # Current Location
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location = Column(Geometry('POINT', srid=4326), nullable=True)
    
    # Status
    status = Column(SQLEnum(AmbulanceStatus), default=AmbulanceStatus.AVAILABLE)
    
    # Assignment
    assigned_emergency_id = Column(Integer, ForeignKey("emergencies.id"), nullable=True)
    
    # Equipment
    has_life_support = Column(Boolean, default=True)
    has_defibrillator = Column(Boolean, default=True)
    has_oxygen = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=sa.func.now())
    
    # Relationships
    assigned_emergency = relationship("Emergency", back_populates="assigned_ambulance")


class Emergency(Base):
    """Emergency session tracking the full lifecycle."""
    __tablename__ = "emergencies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Emergency Details
    emergency_type = Column(SQLEnum(EmergencyType), nullable=False)
    description = Column(Text, nullable=True)
    
    # Location at trigger time
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location = Column(Geometry('POINT', srid=4326), nullable=False)
    address = Column(Text, nullable=True)
    
    # Assignments
    assigned_hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    assigned_ambulance_id = Column(Integer, ForeignKey("ambulances.id"), nullable=True)
    
    # Status
    status = Column(SQLEnum(EmergencyStatus), default=EmergencyStatus.TRIGGERED)
    
    # Tracking Token (for family sharing)
    tracking_token = Column(String(64), unique=True, index=True, nullable=True)
    
    # Timestamps
    triggered_at = Column(TIMESTAMP(timezone=True), server_default=sa.func.now())
    confirmed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    ambulance_dispatched_at = Column(TIMESTAMP(timezone=True), nullable=True)
    arrived_at_hospital_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="emergencies")
    assigned_hospital = relationship("Hospital", back_populates="emergencies")
    assigned_ambulance = relationship("Ambulance", back_populates="assigned_emergency")
    updates = relationship("EmergencyUpdate", back_populates="emergency", cascade="all, delete-orphan")


class EmergencyUpdate(Base):
    """Timeline of status events for an emergency session."""
    __tablename__ = "emergency_updates"

    id = Column(Integer, primary_key=True, index=True)
    emergency_id = Column(Integer, ForeignKey("emergencies.id"), nullable=False)
    
    # Update Details
    status = Column(SQLEnum(EmergencyStatus), nullable=False)
    message = Column(Text, nullable=False)
    
    # Location snapshot (optional)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Additional data (JSON)
    metadata = Column(JSON, default=dict)
    
    # Timestamp
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.func.now())
    
    # Relationships
    emergency = relationship("Emergency", back_populates="updates")
