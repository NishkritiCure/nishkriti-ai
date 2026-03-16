from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, HTTPException
from supabase import AsyncClient
from db.supabase_client import get_supabase_client
from services.exotel import validate_exotel_signature
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhooks"])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _verified_exotel_form(request: Request) -> dict:
    """Dependency: validates Exotel HMAC signature, returns parsed form data."""
    raw_body = await request.body()
    sig = request.headers.get("X-Exotel-Signature", "")
    if not validate_exotel_signature(raw_body, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")
    return dict(await request.form())


@router.post("/call-initiated")
async def handle_call_initiated(
    form: dict = Depends(_verified_exotel_form),
    db: AsyncClient = Depends(get_supabase_client),
):
    call_sid: str = form.get("CallSid", "")
    from_number: str = form.get("From", "")

    if not call_sid or not from_number:
        raise HTTPException(status_code=422, detail="Missing CallSid or From")

    # Upsert patient by phone number
    result = await db.table("patients").select("id").eq("phone", from_number).execute()
    if result.data:
        patient_id: str = result.data[0]["id"]
    else:
        insert = await db.table("patients").insert({"phone": from_number}).execute()
        patient_id = insert.data[0]["id"]

    # Insert call record — idempotent (ON CONFLICT DO NOTHING)
    await db.table("calls").upsert(
        {
            "patient_id": patient_id,
            "exotel_call_id": call_sid,
            "layer": 1,
            "status": "initiated",
            "started_at": _utc_now(),
        },
        on_conflict="exotel_call_id",
        ignore_duplicates=True,
    ).execute()

    logger.info("call_initiated", extra={"exotel_call_id": call_sid})
    return {"status": "ok"}


@router.post("/call-complete")
async def handle_call_complete(
    form: dict = Depends(_verified_exotel_form),
    db: AsyncClient = Depends(get_supabase_client),
):
    call_sid: str = form.get("CallSid", "")
    recording_url: str = form.get("RecordingUrl", "")
    duration_str: str = form.get("Duration", "0")

    if not call_sid:
        raise HTTPException(status_code=422, detail="Missing CallSid")

    duration_secs: int = int(duration_str) if duration_str.isdigit() else 0

    await db.table("calls").update(
        {
            "status": "completed",
            "recording_url": recording_url or None,
            "duration_secs": duration_secs,
            "ended_at": _utc_now(),
        }
    ).eq("exotel_call_id", call_sid).execute()

    logger.info(
        "call_complete",
        extra={"exotel_call_id": call_sid, "duration_secs": duration_secs},
    )
    return {"status": "ok"}
