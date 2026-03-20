import hmac
import hashlib
import os

EXOTEL_WEBHOOK_SECRET: str = os.getenv("EXOTEL_WEBHOOK_SECRET", "")

def validate_exotel_signature(raw_body: bytes, signature_header: str) -> bool:
    """
    Returns True if X-Exotel-Signature matches HMAC-SHA256(raw_body, secret).
    Returns False on any invalid input or mismatch. Never raises.
    """
    if not EXOTEL_WEBHOOK_SECRET or not signature_header:
        return False
    try:
        expected = hmac.new(
            EXOTEL_WEBHOOK_SECRET.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature_header.lower())
    except Exception:
        return False
