import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
from typing import Any, Dict, Iterable, Optional, Tuple

import requests
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse

from services.aliana_conversation_service import AlianaConversationService
from services.booking_service import BookingService
from services.therapist_service import TherapistService
from services.scheduling_service import SchedulingService
from models import now_iso


meta_whatsapp_router = APIRouter(prefix="/whatsapp/meta", tags=["WhatsApp Meta"])

META_WEBHOOK_VERIFY_TOKEN = os.environ.get("META_WEBHOOK_VERIFY_TOKEN")
META_APP_SECRET = os.environ.get("META_APP_SECRET")
META_GRAPH_API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v23.0")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_API_URL = os.environ.get(
    "WHATSAPP_API_URL",
    f"https://graph.facebook.com/{META_GRAPH_API_VERSION}",
).rstrip("/")


def _normalize_sender(value: Optional[str]) -> Optional[str]:
    digits = re.sub(r"\D", "", str(value or ""))
    if not 8 <= len(digits) <= 15:
        return None
    return f"+{digits}"


def _verify_signature(raw_body: bytes, supplied_signature: Optional[str]) -> bool:
    if not META_APP_SECRET or not supplied_signature:
        return False
    expected = "sha256=" + hmac.new(
        META_APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, supplied_signature)


def _extract_booking_decision_payload(message: Dict[str, Any]) -> Optional[str]:
    """Return the opaque quick-reply payload used for therapist booking decisions."""
    message_type = str(message.get("type") or "").lower()
    if message_type == "button":
        button = message.get("button") or {}
        payload = str(button.get("payload") or "").strip()
        return payload or None

    if message_type == "interactive":
        interactive = message.get("interactive") or {}
        button = interactive.get("button_reply") or {}
        payload = str(button.get("id") or "").strip()
        return payload or None

    return None


async def _resolve_super_admin_by_whatsapp(db: Any, sender: str) -> Optional[Dict[str, Any]]:
    rows = await db.staff_users.find(
        {
            "role": "super_admin",
            "active": {"$ne": False},
            "whatsapp_admin_enabled": True,
            "whatsapp_phone": {"$exists": True, "$ne": None},
        },
        {"_id": 0, "user_id": 1, "name": 1, "role": 1, "whatsapp_phone": 1},
    ).to_list(100)
    for row in rows:
        if _normalize_sender(row.get("whatsapp_phone")) == sender:
            return row
    return None


async def _admin_assignment_session(db: Any, sender: str) -> Dict[str, Any]:
    key = hashlib.sha256(sender.encode("utf-8")).hexdigest()
    doc = await db.whatsapp_admin_sessions.find_one({"sender_hash": key}, {"_id": 0})
    return doc or {"sender_hash": key, "state": "idle", "context": {}}


async def _save_admin_assignment_session(
    db: Any,
    sender: str,
    state: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    key = hashlib.sha256(sender.encode("utf-8")).hexdigest()
    await db.whatsapp_admin_sessions.update_one(
        {"sender_hash": key},
        {"$set": {
            "sender_hash": key,
            "state": state,
            "context": context or {},
            "updated_at": now_iso(),
        }, "$setOnInsert": {"created_at": now_iso()}},
        upsert=True,
    )


def _booking_summary(row: Dict[str, Any], index: int) -> str:
    raw = str(row.get("starts_at") or "")
    try:
        dt = __import__("datetime").datetime.fromisoformat(raw.replace("Z", "+00:00"))
        when = dt.strftime("%a %d %b %Y, %H:%M UTC")
    except Exception:
        when = raw or "Unknown time"
    mode = "Virtual" if row.get("session_mode") == "virtual" else "In-Person"
    session_type = str(row.get("session_type") or "session").capitalize()
    return f"{index}. {when} · {session_type} · {mode}"


async def _available_therapists_for_booking(db: Any, booking: Dict[str, Any]) -> list[Dict[str, Any]]:
    mode = booking.get("session_mode")
    therapists = await TherapistService.list_therapists(db, active_only=True, session_mode=mode)
    available = []
    for therapist in therapists:
        has_conflict, _ = await BookingService.check_therapist_conflict(
            db,
            therapist.id,
            booking["starts_at"],
            booking["ends_at"],
            exclude_booking_id=booking.get("id"),
        )
        if has_conflict:
            continue
        if SchedulingService.provider() == "setmore":
            try:
                start_dt = __import__("datetime").datetime.fromisoformat(
                    str(booking["starts_at"]).replace("Z", "+00:00")
                )
                slots = await SchedulingService.get_available_slots(
                    db,
                    therapist_id=therapist.id,
                    start_date=start_dt.date().isoformat(),
                    days_ahead=1,
                    session_type=booking.get("session_type") or "individual",
                    session_mode=mode or "virtual",
                    funding_scope="private",
                )
                if not any(
                    slot.get("is_available")
                    and __import__("datetime").datetime.fromisoformat(
                        str(slot.get("starts_at") or "").replace("Z", "+00:00")
                    ).isoformat() == start_dt.isoformat()
                    for slot in slots
                    if slot.get("starts_at")
                ):
                    continue
            except Exception:
                continue
        available.append({
            "id": therapist.id,
            "name": therapist.name,
        })
    return available


async def _handle_super_admin_assignment_flow(
    db: Any,
    sender: str,
    text: str,
) -> Optional[str]:
    admin = await _resolve_super_admin_by_whatsapp(db, sender)
    if not admin:
        return None

    command = str(text or "").strip()
    upper = command.upper()
    session = await _admin_assignment_session(db, sender)

    if upper in {"CANCEL", "STOP", "ADMIN CANCEL"}:
        await _save_admin_assignment_session(db, sender, "idle", {})
        return "FCA admin booking assignment cancelled."

    if upper in {"ASSIGN", "PENDING", "PENDING BOOKINGS", "ADMIN BOOKINGS"}:
        rows = await db.bookings.find(
            {
                "status": "pending",
                "assignment_status": {"$in": ["awaiting_assignment", "declined"]},
            },
            {
                "_id": 0,
                "id": 1,
                "starts_at": 1,
                "ends_at": 1,
                "session_type": 1,
                "session_mode": 1,
            },
        ).sort("starts_at", 1).limit(9).to_list(9)
        if not rows:
            await _save_admin_assignment_session(db, sender, "idle", {})
            return "There are no booking requests waiting for therapist assignment."

        context = {"booking_ids": [row["id"] for row in rows]}
        await _save_admin_assignment_session(db, sender, "choose_booking", context)
        lines = ["Pending booking requests:"]
        lines.extend(_booking_summary(row, index) for index, row in enumerate(rows, 1))
        lines.append("\nReply with the booking number to assign, or CANCEL.")
        return "\n".join(lines)

    if session.get("state") == "choose_booking":
        try:
            index = int(command) - 1
        except Exception:
            return "Reply with one of the booking numbers shown, or CANCEL."

        booking_ids = (session.get("context") or {}).get("booking_ids") or []
        if not 0 <= index < len(booking_ids):
            return "That booking number is not available. Choose one of the listed numbers."

        booking = await db.bookings.find_one(
            {"id": booking_ids[index], "status": "pending"},
            {"_id": 0},
        )
        if not booking:
            await _save_admin_assignment_session(db, sender, "idle", {})
            return "That booking request is no longer pending. Send ASSIGN to refresh the list."

        therapists = await _available_therapists_for_booking(db, booking)
        if not therapists:
            await _save_admin_assignment_session(db, sender, "idle", {})
            return "No eligible therapists are currently available for that requested time."

        await _save_admin_assignment_session(
            db,
            sender,
            "choose_therapist",
            {
                "booking_id": booking["id"],
                "therapist_ids": [item["id"] for item in therapists],
            },
        )
        lines = ["Available therapists:"]
        lines.extend(f"{i}. {item['name']}" for i, item in enumerate(therapists, 1))
        lines.append("\nReply with the therapist number, or CANCEL.")
        return "\n".join(lines)

    if session.get("state") == "choose_therapist":
        try:
            index = int(command) - 1
        except Exception:
            return "Reply with one of the therapist numbers shown, or CANCEL."

        context = session.get("context") or {}
        therapist_ids = context.get("therapist_ids") or []
        booking_id = context.get("booking_id")
        if not booking_id or not 0 <= index < len(therapist_ids):
            return "That therapist number is not available. Choose one of the listed numbers."

        booking, error = await BookingService.assign_therapist(
            db,
            booking_id=booking_id,
            therapist_id=therapist_ids[index],
            actor_id=admin.get("user_id"),
            actor_name=admin.get("name") or "Super Admin",
        )
        await _save_admin_assignment_session(db, sender, "idle", {})
        if error or not booking:
            return f"FCA could not assign that therapist: {error or 'assignment failed.'}"

        return (
            "Therapist assigned successfully. ✅\n"
            "The therapist has been sent the appointment request for Accept / Decline."
        )

    if upper in {"ADMIN", "ADMIN MENU"}:
        return (
            "FCA Super Admin WhatsApp\n\n"
            "Send ASSIGN to view booking requests awaiting therapist assignment.\n"
            "Send CANCEL at any time to exit an assignment flow."
        )

    return None


async def _handle_therapist_booking_decision(
    db: Any,
    sender: str,
    payload: str,
) -> Optional[str]:
    match = re.fullmatch(r"FCA_BOOKING_(ACCEPT|DECLINE):([A-Za-z0-9-]{8,128})", payload or "")
    if not match:
        return None

    decision = "accept" if match.group(1) == "ACCEPT" else "decline"
    booking_id = match.group(2)

    therapist = None
    therapist_rows = await db.therapists.find(
        {"active": True, "whatsapp_phone": {"$exists": True, "$ne": None}},
        {"_id": 0, "id": 1, "name": 1, "whatsapp_phone": 1},
    ).to_list(200)
    for row in therapist_rows:
        if _normalize_sender(row.get("whatsapp_phone")) == sender:
            therapist = row
            break

    if not therapist:
        return (
            "FCA could not match this WhatsApp number to an active therapist profile. "
            "Please use the number registered in your therapist settings or contact administration."
        )

    booking, error = await BookingService.therapist_decision(
        db,
        booking_id=booking_id,
        therapist_id=therapist["id"],
        decision=decision,
        actor_id=f"whatsapp:{therapist['id']}",
        actor_name=therapist.get("name") or "Therapist",
    )
    if error or not booking:
        return f"FCA could not {decision} this appointment: {error or 'the request is no longer available.'}"

    if decision == "accept":
        return (
            "Appointment accepted. ✅\n"
            "The client confirmation has now been sent and the booking is confirmed."
        )

    return (
        "Appointment declined.\n"
        "The booking request has been returned to FCA administration for reassignment."
    )


def _extract_message_text(message: Dict[str, Any]) -> Optional[str]:
    message_type = str(message.get("type") or "").lower()
    if message_type == "text":
        body = ((message.get("text") or {}).get("body") or "").strip()
        return body or None

    if message_type == "interactive":
        interactive = message.get("interactive") or {}
        button = interactive.get("button_reply") or {}
        list_reply = interactive.get("list_reply") or {}
        return (
            str(button.get("id") or button.get("title") or "").strip()
            or str(list_reply.get("id") or list_reply.get("title") or "").strip()
            or None
        )

    if message_type == "button":
        button = message.get("button") or {}
        return str(button.get("text") or button.get("payload") or "").strip() or None

    return None


def _iter_statuses(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            if change.get("field") != "messages":
                continue
            value = change.get("value") or {}
            for status in value.get("statuses") or []:
                yield status


async def _process_status_updates(db: Any, payload: Dict[str, Any]) -> None:
    """Persist Meta delivery lifecycle against the outbound notification wamid."""
    for status in _iter_statuses(payload):
        message_id = str(status.get("id") or "").strip()
        meta_status = str(status.get("status") or "").lower().strip()
        if not message_id or meta_status not in {"sent", "delivered", "read", "failed"}:
            continue

        timestamp = status.get("timestamp")
        errors = status.get("errors") or []
        error_summary = None
        if errors:
            first = errors[0] or {}
            error_summary = str(
                first.get("message")
                or first.get("title")
                or ((first.get("error_data") or {}).get("details"))
                or "Meta reported message delivery failure"
            )[:500]

        now = now_iso()
        update_fields: Dict[str, Any] = {
            "status": meta_status,
            "meta_status": meta_status,
            "status_updated_at": now,
        }
        if timestamp:
            update_fields["meta_status_timestamp"] = str(timestamp)
        if meta_status == "sent":
            update_fields["sent_at"] = now
        elif meta_status == "delivered":
            update_fields["delivered_at"] = now
        elif meta_status == "read":
            update_fields["read_at"] = now
        elif meta_status == "failed":
            update_fields["failed_at"] = now
            update_fields["error_message"] = error_summary

        result = await db.notification_log.update_many(
            {"provider_reference": message_id},
            {"$set": update_fields},
        )
        if result.matched_count:
            logging.info(
                "Meta WhatsApp delivery status updated: status=%s matched=%s",
                meta_status,
                result.matched_count,
            )
        else:
            # Keep unmatched callbacks for diagnosis (for example bot free-text replies
            # that are not represented in notification_log).
            await db.whatsapp_meta_status_events.update_one(
                {"message_id": message_id, "status": meta_status},
                {
                    "$set": {
                        "message_id": message_id,
                        "status": meta_status,
                        "timestamp": str(timestamp or ""),
                        "error_message": error_summary,
                        "updated_at": now,
                    },
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )


def _iter_messages(payload: Dict[str, Any]) -> Iterable[Tuple[Dict[str, Any], Dict[str, Any]]]:
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            if change.get("field") != "messages":
                continue
            value = change.get("value") or {}
            for message in value.get("messages") or []:
                yield value, message


async def _send_meta_text(to_e164: str, text: str, phone_number_id: Optional[str] = None) -> None:
    target_phone_number_id = phone_number_id or WHATSAPP_PHONE_NUMBER_ID
    if not target_phone_number_id or not WHATSAPP_ACCESS_TOKEN:
        logging.warning("Meta WhatsApp reply skipped because outbound credentials are not configured")
        return

    recipient = re.sub(r"\D", "", to_e164)
    url = f"{WHATSAPP_API_URL}/{target_phone_number_id}/messages"

    def _send() -> requests.Response:
        return requests.post(
            url,
            headers={
                "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "text",
                "text": {"body": text},
            },
            timeout=15,
        )

    try:
        response = await asyncio.to_thread(_send)
        if response.status_code not in (200, 201, 202):
            logging.warning(
                "Meta WhatsApp bot reply rejected: status=%s",
                response.status_code,
            )
        else:
            logging.info("Meta WhatsApp bot reply accepted")
    except Exception as exc:
        logging.warning("Meta WhatsApp bot reply failed: %s", exc.__class__.__name__)


async def _process_webhook_payload(db: Any, payload: Dict[str, Any]) -> None:
    # Process outbound delivery receipts before handling inbound conversation messages.
    await _process_status_updates(db, payload)

    for value, message in _iter_messages(payload):
        sender = _normalize_sender(message.get("from"))
        decision_payload = _extract_booking_decision_payload(message)
        text = _extract_message_text(message)
        message_id = str(message.get("id") or "").strip() or None
        if not sender or (not text and not decision_payload):
            continue

        if message_id:
            result = await db.whatsapp_meta_inbound_events.update_one(
                {"message_id": message_id},
                {
                    "$setOnInsert": {
                        "message_id": message_id,
                        "sender_hash": hashlib.sha256(sender.encode("utf-8")).hexdigest(),
                        "created_at": now_iso(),
                    }
                },
                upsert=True,
            )
            if result.matched_count > 0 and result.upserted_id is None:
                continue

        if decision_payload:
            decision_reply = await _handle_therapist_booking_decision(db, sender, decision_payload)
            if decision_reply is not None:
                metadata = value.get("metadata") or {}
                await _send_meta_text(sender, decision_reply, metadata.get("phone_number_id"))
                continue

        admin_reply = await _handle_super_admin_assignment_flow(db, sender, text or "")
        if admin_reply is not None:
            metadata = value.get("metadata") or {}
            await _send_meta_text(sender, admin_reply, metadata.get("phone_number_id"))
            continue

        session_id = f"whatsapp:{sender}"
        await AlianaConversationService.log_turn(db, "whatsapp", session_id, "user", text)
        reply = await AlianaConversationService.respond(
            db, "whatsapp", sender, text, session_id=session_id
        )
        if reply:
            await AlianaConversationService.log_turn(db, "whatsapp", session_id, "assistant", reply)
        if not reply:
            continue

        metadata = value.get("metadata") or {}
        await _send_meta_text(sender, reply, metadata.get("phone_number_id"))


@meta_whatsapp_router.get("/status")
async def meta_whatsapp_status():
    """Non-secret readiness probe for production configuration."""
    return {
        "provider": "meta",
        "webhook_verify_token_configured": bool(META_WEBHOOK_VERIFY_TOKEN),
        "app_secret_configured": bool(META_APP_SECRET),
        "phone_number_id_configured": bool(WHATSAPP_PHONE_NUMBER_ID),
        "access_token_configured": bool(WHATSAPP_ACCESS_TOKEN),
        "graph_api_version": META_GRAPH_API_VERSION,
        "ready": bool(
            META_WEBHOOK_VERIFY_TOKEN
            and META_APP_SECRET
            and WHATSAPP_PHONE_NUMBER_ID
            and WHATSAPP_ACCESS_TOKEN
        ),
    }


@meta_whatsapp_router.get("/webhook")
async def verify_meta_webhook(request: Request):
    if not META_WEBHOOK_VERIFY_TOKEN:
        raise HTTPException(status_code=503, detail="Meta webhook verification is not configured")

    mode = request.query_params.get("hub.mode")
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if (
        mode == "subscribe"
        and verify_token
        and challenge is not None
        and hmac.compare_digest(verify_token, META_WEBHOOK_VERIFY_TOKEN)
    ):
        return PlainTextResponse(challenge, status_code=200)

    raise HTTPException(status_code=403, detail="Webhook verification failed")


@meta_whatsapp_router.post("/webhook")
async def receive_meta_webhook(request: Request, background_tasks: BackgroundTasks):
    if not META_APP_SECRET:
        raise HTTPException(status_code=503, detail="Meta webhook signature verification is not configured")

    raw_body = await request.body()
    if not _verify_signature(raw_body, request.headers.get("x-hub-signature-256")):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    # Meta expects a prompt 200 response. Booking-bot work runs after acknowledgement.
    background_tasks.add_task(_process_webhook_payload, request.app.state.db, payload)
    return {"status": "accepted"}
