from twilio.rest import Client
from app.core.config import settings
import logging
from typing import List


logger = logging.getLogger(__name__)


def get_twilio_client() -> Client | None:
    """Get Twilio client if configured."""
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("Twilio credentials not configured. SMS notifications disabled.")
        return None
    
    try:
        return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    except Exception as e:
        logger.error(f"Failed to initialize Twilio client: {e}")
        return None


async def send_sms_notification(
    phone_number: str,
    message: str
) -> bool:
    """
    Send SMS notification via Twilio.
    
    Returns True if successful, False otherwise.
    """
    client = get_twilio_client()
    
    if not client:
        # Log but don't fail - this is expected in development
        logger.info(f"SMS would be sent to {phone_number}: {message}")
        return True
    
    try:
        message = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        logger.info(f"SMS sent successfully to {phone_number}. SID: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS to {phone_number}: {e}")
        return False


async def notify_emergency_contacts(
    contacts: List[dict],
    tracking_url: str,
    emergency_type: str,
    location_description: str
) -> dict:
    """
    Notify all emergency contacts via SMS.
    
    Returns summary of notifications sent.
    """
    results = {
        "total": len(contacts),
        "sent": 0,
        "failed": 0,
        "details": []
    }
    
    message_template = f"""
🚨 EMERGENCY ALERT 🚨

A {emergency_type} emergency has been triggered.

Location: {location_description}

Track the ambulance in real-time:
{tracking_url}

Stay tuned for updates. Help is on the way!

- Emergency SOS India
""".strip()
    
    for contact in contacts:
        name = contact.get("name", "Emergency Contact")
        phone = contact.get("phone", "")
        
        if not phone:
            results["failed"] += 1
            results["details"].append({
                "name": name,
                "phone": phone,
                "status": "failed",
                "reason": "No phone number"
            })
            continue
        
        # Personalize message
        message = f"Hi {name},\n\n" + message_template
        
        success = await send_sms_notification(phone, message)
        
        if success:
            results["sent"] += 1
            results["details"].append({
                "name": name,
                "phone": phone,
                "status": "sent"
            })
        else:
            results["failed"] += 1
            results["details"].append({
                "name": name,
                "phone": phone,
                "status": "failed",
                "reason": "SMS delivery failed"
            })
    
    return results


async def send_status_update(
    phone_number: str,
    status: str,
    eta_minutes: int | None = None,
    additional_info: str | None = None
) -> bool:
    """Send status update SMS to contacts."""
    
    status_messages = {
        "ambulance_dispatched": "🚑 Ambulance has been dispatched and is on the way!",
        "en_route_to_patient": "🚐 Ambulance is en route to the patient's location.",
        "patient_picked": "✅ Patient has been picked up by the ambulance.",
        "en_route_to_hospital": "🏥 En route to the hospital.",
        "arrived_at_hospital": "🏨 Ambulance has arrived at the hospital. Patient is receiving care."
    }
    
    base_message = status_messages.get(status, f"Status update: {status}")
    
    if eta_minutes:
        base_message += f"\n\nEstimated arrival: {eta_minutes} minutes"
    
    if additional_info:
        base_message += f"\n\n{additional_info}"
    
    base_message += "\n\n- Emergency SOS India"
    
    return await send_sms_notification(phone_number, base_message)
