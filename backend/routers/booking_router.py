import hashlib
import hmac
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Request, status, Query
from pydantic import BaseModel, Field

from models import (
    Booking, BookingCreateRequest, MultiBookingCreateRequest,
    BookingRescheduleRequest, BookingStatusUpdateRequest, now_iso
)
from services.booking_service import BookingService
from services.whatsapp_booking_bot_service import WhatsAppBookingBotService
from services.whatsapp_booking_bot_fast_slots import fast_slot_options
from services.whatsapp_booking_bot_day_flow import install_day_first_flow
from services.whatsapp_notification_resilience import install_whatsapp_retry_wrappers
from services.therapist_service import TherapistService
from services.scheduling_service import SchedulingService

# Keep slot discovery optimized and present WhatsApp availability as day -> time.
# The existing booking service remains authoritative for conflict checks, CRM writes,
# entitlement validation and notifications.
WhatsAppBookingBotService._slot_options = staticmethod(fast_slot_options)
install_day_first_flow(WhatsAppBookingBotService)
install_whatsapp_retry_wrappers()

booking_router = APIRouter(prefix="/bookings", tags=["Bookings"])


class WhatsAppInboundMessage(BaseModel):
    sender: str = Field(..., min_length=8, max_length=32)
    text: str = Field(..., min_length=1, max_length=4096)
    message_id: Optional[str] = Field(default=None, max_length=256)


def get_db(request: Request):
    return request.app.state.db


def get_current_user(request: Request) -> Dict[str, Any]:
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return {"user_id": user_id, "role": role, "name": request.session.get("name", user_id)}


def require_staff_or_therapist(request: Request):
    user = get_current_user(request)
    allowed = ["super_admin", "admin", "staff", "therapist", "clinical_admin"]
    if user.get("role") not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return user


def require_baileys_adapter(request: Request) -> None:
    expected = os.environ.get("WHATSAPP_INBOUND_TOKEN") or os.environ.get("BAILEYS_SERVICE_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp inbound adapter authentication is not configured",
        )
    supplied = request.headers.get("authorization", "")
    if not hmac.compare_digest(supplied, f"Bearer {expected}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@booking_router.post("/whatsapp/inbound")
async def whatsapp_booking_inbound(payload: WhatsAppInboundMessage, request: Request):
    require_baileys_adapter(request)
    db = get_db(request)

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




class PublicBookingCreate(BaseModel):
    client_id: str
    therapist_id: str
    session_type: str = "individual"
    session_mode: str
    starts_at: str
    ends_at: Optional[str] = None
    organisation_code: Optional[str] = None


@booking_router.get("/public/availability")
async def public_booking_availability(
    request: Request,
    session_mode: str = Query(...),
    start_date: str = Query(...),
    days_ahead: int = Query(14, ge=1, le=30),
    client_id: Optional[str] = Query(None),
):
    """Public, privacy-safe slot discovery for the post-intake booking step."""
    mode = session_mode.lower()
    if mode not in ("virtual", "in_person"):
        raise HTTPException(status_code=400, detail="Invalid session mode")

    db = get_db(request)
    client_doc = None
    funding_scope = "private"
    if client_id:
        client_doc = await db.crm_clients.find_one({"id": client_id}, {"_id": 0, "organisation_id": 1})
        if client_doc and client_doc.get("organisation_id"):
            funding_scope = "organisation"

    therapists = await TherapistService.list_therapists(db, active_only=True, session_mode=mode)
    available = []
    now = datetime.now(timezone.utc)
    scheduling_errors = []
    for therapist in therapists:
        try:
            slots = await SchedulingService.get_available_slots(
                db, therapist_id=therapist.id, start_date=start_date, days_ahead=days_ahead,
                session_mode=mode,
                funding_scope=funding_scope,
            )
        except Exception as exc:
            scheduling_errors.append(exc)
            logging.exception(
                "PUBLIC_BOOKING_AVAILABILITY_FAILED therapist_id=%s mode=%s provider=%s",
                therapist.id,
                mode,
                SchedulingService.provider(),
            )
            continue

        for slot in slots:
            if not slot.get("is_available"):
                continue
            try:
                if datetime.fromisoformat(slot["starts_at"].replace("Z", "+00:00")) <= now:
                    continue
            except Exception:
                continue
            available.append({
                "therapist_id": therapist.id,
                "therapist_name": therapist.name,
                "starts_at": slot["starts_at"],
                "ends_at": slot["ends_at"],
                "date": slot["date"],
                "time_display": slot["time_display"],
            })

    if therapists and len(scheduling_errors) == len(therapists):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live booking availability is temporarily unavailable. Please try again shortly.",
        )

    available.sort(key=lambda x: x["starts_at"])
    return {"session_mode": mode, "funding_scope": funding_scope, "slots": available}


@booking_router.post("/public", response_model=Booking)
async def create_public_booking(payload: PublicBookingCreate, request: Request):
    """Create a booking only for a CRM client produced by the intake workflow."""
    db = get_db(request)
    client = await db.crm_clients.find_one({"id": payload.client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Please complete the intake form before booking.")

    if payload.organisation_code:
        organisation = await db.organisations.find_one(
            {"code": {"$regex": f"^{__import__('re').escape(payload.organisation_code.strip())}$", "$options": "i"}, "status": "active"},
            {"_id": 0},
        )
        if not organisation or client.get("organisation_id") != organisation.get("id"):
            raise HTTPException(status_code=400, detail="Corporate booking link does not match this intake.")
    elif client.get("organisation_id"):
        raise HTTPException(status_code=400, detail="Please use the corporate intake link assigned to your organisation.")

    booking_request = BookingCreateRequest(
        client_id=payload.client_id,
        therapist_id=payload.therapist_id,
        session_type=payload.session_type,
        session_mode=payload.session_mode,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        send_notifications=True,
        source="website_intake",
    )
    booking, err = await BookingService.create_booking(
        db, request=booking_request, actor_id="public_intake", actor_name="Website Intake"
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    return booking

@booking_router.get("")
async def list_bookings(
    request: Request,
    client_id: Optional[str] = Query(None),
    therapist_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    session_type: Optional[str] = Query(None),
    session_mode: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: Dict = Depends(require_staff_or_therapist)
):
    db = get_db(request)
    if user.get("role") == "therapist" and user.get("therapist_id"):
        therapist_id = user.get("therapist_id")

    skip = (page - 1) * limit
    bookings, total = await BookingService.list_bookings(
        db,
        client_id=client_id,
        therapist_id=therapist_id,
        status=status,
        session_type=session_type,
        session_mode=session_mode,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )
    return {
        "bookings": bookings,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 1
    }


@booking_router.post("", response_model=Booking)
async def create_single_booking(
    payload: BookingCreateRequest,
    request: Request,
    user: Dict = Depends(require_staff_or_therapist)
):
    db = get_db(request)
    booking, err = await BookingService.create_booking(
        db,
        request=payload,
        actor_id=user.get("user_id"),
        actor_name=user.get("name")
    )
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    return booking


@booking_router.post("/multi")
async def create_multi_booking(
    payload: MultiBookingCreateRequest,
    request: Request,
    user: Dict = Depends(require_staff_or_therapist)
):
    db = get_db(request)
    result, err = await BookingService.create_multi_booking(
        db,
        request=payload,
        actor_id=user.get("user_id"),
        actor_name=user.get("name")
    )
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    return result


@booking_router.get("/{booking_id}", response_model=Booking)
async def get_booking_details(
    booking_id: str,
    request: Request,
    user: Dict = Depends(require_staff_or_therapist)
):
    db = get_db(request)
    booking_doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking_doc:
        raise HTTPException(status_code=404, detail="Booking not found")

    if (
        user.get("role") == "therapist"
        and user.get("therapist_id")
        and booking_doc.get("therapist_id") != user.get("therapist_id")
    ):
        raise HTTPException(status_code=403, detail="Access to booking denied")

    return Booking(**booking_doc)


@booking_router.post("/{booking_id}/reschedule", response_model=Booking)
async def reschedule_booking(
    booking_id: str,
    payload: BookingRescheduleRequest,
    request: Request,
    user: Dict = Depends(require_staff_or_therapist)
):
    db = get_db(request)
    booking, err = await BookingService.reschedule_booking(
        db,
        booking_id=booking_id,
        request=payload,
        actor_id=user.get("user_id"),
        actor_name=user.get("name")
    )
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    return booking


@booking_router.post("/{booking_id}/status", response_model=Booking)
async def update_booking_status(
    booking_id: str,
    payload: BookingStatusUpdateRequest,
    request: Request,
    user: Dict = Depends(require_staff_or_therapist)
):
    db = get_db(request)
    booking, err = await BookingService.update_booking_status(
        db,
        booking_id=booking_id,
        request=payload,
        actor_id=user.get("user_id"),
        actor_name=user.get("name")
    )
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    return booking
