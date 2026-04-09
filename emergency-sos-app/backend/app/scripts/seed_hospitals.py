"""
Seed script to populate the database with mock hospitals across India.

Run with: python -m app.scripts.seed_hospitals
"""

import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.models.models import Hospital, Base
from app.db.session import DATABASE_URL
from typing import List, Dict, Any


# Mock hospital data for major Indian cities
HOSPITALS_DATA: List[Dict[str, Any]] = [
    # Delhi NCR
    {
        "name": "All India Institute of Medical Sciences (AIIMS)",
        "address": "Ansari Nagar, New Delhi, Delhi 110029",
        "phone": "+91-11-26588500",
        "latitude": 28.5672,
        "longitude": 77.2100,
        "specialties": ["cardiology", "neurology", "trauma", "oncology", "pediatrics"],
        "rating": 4.5,
        "total_beds": 2500,
        "available_beds": 150,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": True
    },
    {
        "name": "Apollo Hospital Delhi",
        "address": "Sarita Vihar, Mathura Road, New Delhi, Delhi 110076",
        "phone": "+91-11-26925858",
        "latitude": 28.5355,
        "longitude": 77.2670,
        "specialties": ["cardiology", "neurology", "orthopedic", "oncology"],
        "rating": 4.3,
        "total_beds": 800,
        "available_beds": 45,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": True
    },
    {
        "name": "Max Super Speciality Hospital Saket",
        "address": "Press Enclave Road, Saket, New Delhi, Delhi 110017",
        "phone": "+91-11-26515050",
        "latitude": 28.5244,
        "longitude": 77.2066,
        "specialties": ["cardiology", "neurology", "trauma", "surgery"],
        "rating": 4.4,
        "total_beds": 600,
        "available_beds": 30,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": False
    },
    
    # Mumbai
    {
        "name": "KEM Hospital",
        "address": "Acharya Donde Marg, Parel, Mumbai, Maharashtra 400012",
        "phone": "+91-22-24107000",
        "latitude": 19.0176,
        "longitude": 72.8562,
        "specialties": ["trauma", "cardiology", "neurology", "orthopedic"],
        "rating": 4.2,
        "total_beds": 1800,
        "available_beds": 100,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": True
    },
    {
        "name": "Lilavati Hospital",
        "address": "A-791, Bandra Reclamation, Bandra West, Mumbai, Maharashtra 400050",
        "phone": "+91-22-26567777",
        "latitude": 19.0544,
        "longitude": 72.8312,
        "specialties": ["cardiology", "neurology", "oncology", "orthopedic"],
        "rating": 4.4,
        "total_beds": 400,
        "available_beds": 25,
        "has_emergency_ward": True,
        "has_trauma_center": False,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": True
    },
    {
        "name": "Jaslok Hospital",
        "address": "15, Dr. Deshmukh Marg, Peddar Road, Mumbai, Maharashtra 400026",
        "phone": "+91-22-66573333",
        "latitude": 18.9647,
        "longitude": 72.8142,
        "specialties": ["cardiology", "neurology", "trauma", "surgery"],
        "rating": 4.3,
        "total_beds": 350,
        "available_beds": 20,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": False
    },
    
    # Bangalore
    {
        "name": "Narayana Health City",
        "address": "258/A, Bommasandra Industrial Area, Bangalore, Karnataka 560099",
        "phone": "+91-80-71222222",
        "latitude": 12.8410,
        "longitude": 77.6907,
        "specialties": ["cardiology", "cardiac", "neurology", "oncology"],
        "rating": 4.5,
        "total_beds": 1000,
        "available_beds": 60,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": True
    },
    {
        "name": "Manipal Hospital",
        "address": "98, HAL Airport Road, Bangalore, Karnataka 560017",
        "phone": "+91-80-25023344",
        "latitude": 12.9698,
        "longitude": 77.6493,
        "specialties": ["cardiology", "neurology", "trauma", "orthopedic"],
        "rating": 4.3,
        "total_beds": 600,
        "available_beds": 35,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": True
    },
    {
        "name": "Fortis Hospital Bannerghatta",
        "address": "245, Bannerghatta Main Road, Bangalore, Karnataka 560076",
        "phone": "+91-80-26399999",
        "latitude": 12.9010,
        "longitude": 77.5959,
        "specialties": ["cardiology", "neurology", "orthopedic", "surgery"],
        "rating": 4.2,
        "total_beds": 400,
        "available_beds": 22,
        "has_emergency_ward": True,
        "has_trauma_center": False,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": False
    },
    
    # Chennai
    {
        "name": "Apollo Hospitals Greams Road",
        "address": "21, Greams Lane, Greams Road, Chennai, Tamil Nadu 600006",
        "phone": "+91-44-28293333",
        "latitude": 13.0627,
        "longitude": 80.2792,
        "specialties": ["cardiology", "neurology", "trauma", "oncology"],
        "rating": 4.4,
        "total_beds": 700,
        "available_beds": 40,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": True
    },
    {
        "name": "MIOT International",
        "address": "4/112, Mount Poonamallee Road, Manapakkam, Chennai, Tamil Nadu 600089",
        "phone": "+91-44-22498000",
        "latitude": 13.0358,
        "longitude": 80.1619,
        "specialties": ["cardiology", "neurology", "orthopedic", "trauma"],
        "rating": 4.3,
        "total_beds": 600,
        "available_beds": 35,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": False
    },
    {
        "name": "Stanley Medical College Hospital",
        "address": "High Court Rd, Mannady, Chennai, Tamil Nadu 600001",
        "phone": "+91-44-25342222",
        "latitude": 13.1067,
        "longitude": 80.2924,
        "specialties": ["trauma", "cardiology", "neurology", "surgery"],
        "rating": 4.1,
        "total_beds": 1500,
        "available_beds": 80,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": True
    },
    
    # Kolkata
    {
        "name": "SSKM Hospital",
        "address": "AJC Bose Rd, Bhawanipore, Kolkata, West Bengal 700020",
        "phone": "+91-33-22232266",
        "latitude": 22.5354,
        "longitude": 88.3441,
        "specialties": ["trauma", "cardiology", "neurology", "orthopedic"],
        "rating": 4.0,
        "total_beds": 2000,
        "available_beds": 120,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": True
    },
    {
        "name": "AMRI Hospitals Dhakuria",
        "address": "66, Sarat Bose Rd, Dhakuria, Kolkata, West Bengal 700020",
        "phone": "+91-33-24645500",
        "latitude": 22.5167,
        "longitude": 88.3667,
        "specialties": ["cardiology", "neurology", "oncology", "orthopedic"],
        "rating": 4.3,
        "total_beds": 400,
        "available_beds": 25,
        "has_emergency_ward": True,
        "has_trauma_center": False,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": True
    },
    {
        "name": "Fortis Hospital Anandapur",
        "address": "Plot No. F-47, Anandapur, EM Bypass, Kolkata, West Bengal 700107",
        "phone": "+91-33-66284444",
        "latitude": 22.5204,
        "longitude": 88.3850,
        "specialties": ["cardiology", "neurology", "trauma", "surgery"],
        "rating": 4.2,
        "total_beds": 350,
        "available_beds": 20,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": False
    },
    
    # Hyderabad
    {
        "name": "Apollo Hospitals Jubilee Hills",
        "address": "Plot No. 77, Road No. 72, Jubilee Hills, Hyderabad, Telangana 500033",
        "phone": "+91-40-23607777",
        "latitude": 17.4239,
        "longitude": 78.4006,
        "specialties": ["cardiology", "neurology", "trauma", "oncology"],
        "rating": 4.4,
        "total_beds": 800,
        "available_beds": 45,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": True
    },
    {
        "name": "Yashoda Hospitals Secunderabad",
        "address": "Raj Bhavan Road, Somajiguda, Hyderabad, Telangana 500082",
        "phone": "+91-40-23444444",
        "latitude": 17.4275,
        "longitude": 78.4525,
        "specialties": ["cardiology", "neurology", "orthopedic", "surgery"],
        "rating": 4.2,
        "total_beds": 500,
        "available_beds": 30,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": False
    },
    {
        "name": "KIMS Hospital",
        "address": "1-8-31/38, Minister Rd, Krishna Nagar Colony, Secunderabad, Telangana 500003",
        "phone": "+91-40-27803333",
        "latitude": 17.4435,
        "longitude": 78.4944,
        "specialties": ["cardiology", "neurology", "trauma", "orthopedic"],
        "rating": 4.3,
        "total_beds": 600,
        "available_beds": 35,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": True
    },
    
    # Pune
    {
        "name": "Ruby Hall Clinic",
        "address": "40, Sassoon Road, Pune, Maharashtra 411001",
        "phone": "+91-20-26127100",
        "latitude": 18.5196,
        "longitude": 73.8789,
        "specialties": ["cardiology", "neurology", "trauma", "oncology"],
        "rating": 4.3,
        "total_beds": 500,
        "available_beds": 30,
        "has_emergency_ward": True,
        "has_trauma_center": True,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": True
    },
    {
        "name": "Deenanath Mangeshkar Hospital",
        "address": "892/1, Erandawane, Pune, Maharashtra 411004",
        "phone": "+91-20-25673333",
        "latitude": 18.5074,
        "longitude": 73.8278,
        "specialties": ["cardiology", "neurology", "orthopedic", "surgery"],
        "rating": 4.4,
        "total_beds": 400,
        "available_beds": 25,
        "has_emergency_ward": True,
        "has_trauma_center": False,
        "has_cardiology": True,
        "has_neurology": True,
        "has_pediatrics": False
    }
]


async def seed_hospitals():
    """Seed the database with mock hospital data."""
    print("🏥 Starting hospital seeding...")
    
    # Create engine and session
    engine = create_async_engine(
        DATABASE_URL.replace("postgresql+asyncpg", "postgresql+asyncpg"),
        echo=True
    )
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Clear existing hospitals
            await session.execute(text("DELETE FROM hospitals"))
            await session.commit()
            print("✅ Cleared existing hospitals")
            
            # Insert new hospitals
            for hospital_data in HOSPITALS_DATA:
                # Create location geometry
                location = f"POINT({hospital_data['longitude']} {hospital_data['latitude']})"
                
                hospital = Hospital(
                    name=hospital_data["name"],
                    address=hospital_data["address"],
                    phone=hospital_data["phone"],
                    latitude=hospital_data["latitude"],
                    longitude=hospital_data["longitude"],
                    location=location,
                    specialties=hospital_data["specialties"],
                    rating=hospital_data["rating"],
                    total_beds=hospital_data["total_beds"],
                    available_beds=hospital_data["available_beds"],
                    has_emergency_ward=hospital_data["has_emergency_ward"],
                    has_trauma_center=hospital_data["has_trauma_center"],
                    has_cardiology=hospital_data["has_cardiology"],
                    has_neurology=hospital_data["has_neurology"],
                    has_pediatrics=hospital_data["has_pediatrics"]
                )
                
                session.add(hospital)
            
            await session.commit()
            print(f"✅ Successfully seeded {len(HOSPITALS_DATA)} hospitals")
            
            # Verify count
            result = await session.execute(text("SELECT COUNT(*) FROM hospitals"))
            count = result.scalar()
            print(f"📊 Total hospitals in database: {count}")
            
    except Exception as e:
        print(f"❌ Error seeding hospitals: {e}")
        raise
    finally:
        await engine.dispose()
    
    print("🎉 Hospital seeding completed!")


if __name__ == "__main__":
    asyncio.run(seed_hospitals())
