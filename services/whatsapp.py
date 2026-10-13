import logging
from typing import Dict
import requests
from config import Config

logger = logging.getLogger(__name__)


def _format_whatsapp_number(num: str) -> str:
    """Ensures phone number is formatted as 'whatsapp:+<digits>' for Twilio."""
    n = num.strip().replace(" ", "").replace("-", "")
    if n.startswith("whatsapp:"):
        n = n[len("whatsapp:"):].strip()
    if not n.startswith("+"):
        n = "+" + n
    return f"whatsapp:{n}"


def send_whatsapp_alert(event_id: int, device_id: str, photo_count: int, has_audio: bool) -> Dict[str, str]:
    """
    Sends an emergency alert notification via Twilio WhatsApp API (primary)
    or Meta WhatsApp Business Cloud API (fallback).
    
    If credentials are missing, returns 'not_configured' without failing.
    """
    alert_body = (
        f"🚨 *EMERGENCY ALERT: Women's Safety Device Triggered!*\n\n"
        f"• *Device ID:* {device_id}\n"
        f"• *Photos captured:* {photo_count}\n"
        f"• *Audio recorded:* {'Yes (WAV)' if has_audio else 'None'}\n"
        f"• *GPS Status:* Not fitted in prototype\n\n"
        f"🔗 *Open Live Dashboard Immediately:*\n{Config.BASE_URL}"
    )

    # 1. Try Twilio WhatsApp API first if configured
    if Config.is_twilio_configured():
        sid = Config.TWILIO_ACCOUNT_SID
        token = Config.TWILIO_AUTH_TOKEN
        from_num = _format_whatsapp_number(Config.TWILIO_WHATSAPP_FROM or "+17372583742")
        to_raw = Config.TWILIO_WHATSAPP_TO or Config.WHATSAPP_RECIPIENT_PHONE_NUMBER
        to_num = _format_whatsapp_number(to_raw)
        content_sid = Config.TWILIO_CONTENT_SID

        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

        try:
            # First try sending the custom alert body
            response = requests.post(
                url,
                data={"From": from_num, "To": to_num, "Body": alert_body},
                auth=(sid, token),
                timeout=10
            )
            # If Twilio Trial Sandbox requires ContentSid (HTTP 400 code 21654), fall back to ContentSid
            if response.status_code == 400 and content_sid:
                logger.info("Twilio requires ContentSid on Trial Sandbox; sending with ContentSid %s", content_sid)
                response = requests.post(
                    url,
                    data={"From": from_num, "To": to_num, "ContentSid": content_sid},
                    auth=(sid, token),
                    timeout=10
                )

            if response.status_code in (200, 201):
                res_data = response.json()
                msg_sid = res_data.get("sid", "sent")
                logger.info("Twilio WhatsApp alert sent successfully: %s", msg_sid)
                return {
                    "status": "sent",
                    "detail": f"Delivered via Twilio WhatsApp (SID: {msg_sid})"
                }
            else:
                try:
                    err_json = response.json()
                    err_msg = err_json.get("message", response.text)
                except Exception:
                    err_msg = response.text
                logger.error("Twilio WhatsApp API error (%s): %s", response.status_code, err_msg)
                return {
                    "status": "failed",
                    "detail": f"Twilio HTTP {response.status_code}: {err_msg}"
                }
        except requests.exceptions.RequestException as e:
            logger.error("Network error sending Twilio WhatsApp alert: %s", e)
            return {
                "status": "failed",
                "detail": f"Twilio network error: {str(e)}"
            }

    # 2. Try Meta WhatsApp Cloud API if configured
    if Config.is_meta_whatsapp_configured():
        url = f"https://graph.facebook.com/v21.0/{Config.WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {Config.WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
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

    # 3. Neither configured
    msg = "WhatsApp alerts not configured (Set TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_WHATSAPP_TO in Environment)"
    logger.info(msg)
    return {
        "status": "not_configured",
        "detail": msg
    }
