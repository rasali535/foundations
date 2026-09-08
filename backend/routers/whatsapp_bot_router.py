import hashlib
import hmac
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from models import now_iso
from services.whatsapp_booking_bot_service import WhatsAppBookingBotService


whatsapp_bot_router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Booking Bot"])


class WhatsAppInboundMessage(BaseModel):
    sender: str = Field(..., min_length=8, max_length=32)
    text: str = Field(..., min_length=1, max_length=4096)
    message_id: Optional[str] = Field(default=None, max_length=256)


def _expected_token() -> Optional[str]:
    return os.environ.get("WHATSAPP_INBOUND_TOKEN") or os.environ.get("BAILEYS_SERVICE_TOKEN")


def _require_adapter_token(request: Request) -> None:
    expected = _expected_token()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp inbound adapter authentication is not configured",
        )
    supplied = request.headers.get("authorization", "")
    if not hmac.compare_digest(supplied, f"Bearer {expected}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@whatsapp_bot_router.post("/inbound")
async def whatsapp_inbound(payload: WhatsAppInboundMessage, request: Request):
    _require_adapter_token(request)
    db = request.app.state.db

    if payload.message_id:
        result = await db.whatsapp_inbound_events.update_one(
            {"message_id": payload.message_id},
            {
                "$setOnInsert": {
                    "message_id": payload.message_id,
                    "sender_hash": hashlib.sha256(payload.sender.encode("utf-8")).hexdigest(),
                    "created_at": now_iso(),
                }
            },
            upsert=True,
        )
        if result.matched_count > 0 and result.upserted_id is None:
            return {"status": "duplicate", "reply": None}

    reply = await WhatsAppBookingBotService.handle_inbound(db, payload.sender, payload.text)
    return {"status": "processed", "reply": reply}
