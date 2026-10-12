import logging
from typing import Dict, Any
import requests
from config import Config

logger = logging.getLogger(__name__)

def send_whatsapp_alert(event_id: int, device_id: str, photo_count: int, has_audio: bool) -> Dict[str, str]:
    """
    Sends an alert notification via the official Meta WhatsApp Business Cloud API.
    
    If credentials are missing, returns 'not_configured' without failing.
    Never hard-codes tokens or simulates delivery.
    """
    if not Config.is_whatsapp_configured():
        msg = "WhatsApp alerts not configured (WHATSAPP_TOKEN / PHONE_NUMBER_ID / RECIPIENT missing in .env)"
        logger.info(msg)
        return {
            "status": "not_configured",
            "detail": msg
        }

    url = f"https://graph.facebook.com/v21.0/{Config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {Config.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    alert_body = (
        f"🚨 EMERGENCY ALERT: Women's Safety Device Triggered!\n\n"
        f"• Event ID: #{event_id}\n"
        f"• Device ID: {device_id}\n"
        f"• Photos captured: {photo_count}\n"
        f"• Audio recorded: {'Yes (~5s WAV)' if has_audio else 'None'}\n"
        f"• GPS Status: Not fitted / Not included in this hardware prototype\n\n"
        f"Check dashboard immediately: {Config.BASE_URL}"
    )

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": Config.WHATSAPP_RECIPIENT_PHONE_NUMBER,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": alert_body
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=8)
        if response.status_code in (200, 201):
            res_data = response.json()
            msg_id = res_data.get("messages", [{}])[0].get("id", "sent")
            logger.info("WhatsApp alert sent successfully: %s", msg_id)
            return {
                "status": "sent",
                "detail": f"Delivered via Meta Cloud API (Message ID: {msg_id})"
            }
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
            except Exception:
                error_msg = response.text
            
            logger.error("Meta WhatsApp Cloud API error (%s): %s", response.status_code, error_msg)
            return {
                "status": "failed",
                "detail": f"Meta API HTTP {response.status_code}: {error_msg}"
            }
    except requests.exceptions.RequestException as e:
        logger.error("Network error sending WhatsApp alert: %s", e)
        return {
            "status": "failed",
            "detail": f"Network exception: {str(e)}"
        }
