import asyncio
import hashlib
import hmac
import json
import logging
import os
from typing import Any, Dict, Iterable, Optional, Tuple

import requests
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse

from models import now_iso
from services.aliana_conversation_service import AlianaConversationService


meta_messenger_router = APIRouter(prefix="/messenger/meta", tags=["Messenger Meta"])

META_APP_SECRET = os.environ.get("META_APP_SECRET")
MESSENGER_VERIFY_TOKEN = os.environ.get("MESSENGER_WEBHOOK_VERIFY_TOKEN")
MESSENGER_PAGE_ACCESS_TOKEN = os.environ.get("MESSENGER_PAGE_ACCESS_TOKEN")
META_GRAPH_API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v23.0")
MESSENGER_API_URL = os.environ.get(
    "MESSENGER_API_URL", f"https://graph.facebook.com/{META_GRAPH_API_VERSION}"
).rstrip("/")


def _verify_signature(raw_body: bytes, supplied: Optional[str]) -> bool:
    if not META_APP_SECRET or not supplied:
        return False
    expected = "sha256=" + hmac.new(
        META_APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, supplied)


def _iter_messages(payload: Dict[str, Any]) -> Iterable[Tuple[str, str, Optional[str]]]:
    for entry in payload.get("entry") or []:
        for event in entry.get("messaging") or []:
            sender_id = str(((event.get("sender") or {}).get("id")) or "").strip()
            message = event.get("message") or {}
            # Ignore echoes from the Page itself.
            if message.get("is_echo"):
                continue
            text = str(message.get("text") or "").strip()
            mid = str(message.get("mid") or "").strip() or None
            if sender_id and text:
                yield sender_id, text, mid


async def _send_text(psid: str, text: str) -> None:
    if not MESSENGER_PAGE_ACCESS_TOKEN:
        logging.warning("Messenger reply skipped: Page access token not configured")
        return

    def _send():
        return requests.post(
            f"{MESSENGER_API_URL}/me/messages",
            params={"access_token": MESSENGER_PAGE_ACCESS_TOKEN},
            json={"recipient": {"id": psid}, "messaging_type": "RESPONSE", "message": {"text": text}},
            timeout=15,
        )

    try:
        response = await asyncio.to_thread(_send)
        if response.status_code not in (200, 201, 202):
            logging.warning("Messenger reply rejected: status=%s", response.status_code)
    except Exception as exc:
        logging.warning("Messenger reply failed: %s", exc.__class__.__name__)


async def _process(db: Any, payload: Dict[str, Any]) -> None:
    for sender_id, text, message_id in _iter_messages(payload):
        if message_id:
            result = await db.messenger_inbound_events.update_one(
                {"message_id": message_id},
                {"$setOnInsert": {
                    "message_id": message_id,
                    "sender_hash": hashlib.sha256(sender_id.encode("utf-8")).hexdigest(),
                    "created_at": now_iso(),
                }},
                upsert=True,
            )
            if result.matched_count > 0 and result.upserted_id is None:
                continue

        session_id = f"messenger:{sender_id}"
        await AlianaConversationService.log_turn(db, "messenger", session_id, "user", text)
        reply = await AlianaConversationService.respond(
            db, "messenger", sender_id, text, session_id=session_id
        )
        await AlianaConversationService.log_turn(db, "messenger", session_id, "assistant", reply)
        await _send_text(sender_id, reply)


@meta_messenger_router.get("/status")
async def messenger_status():
    return {
        "provider": "meta_messenger",
        "webhook_verify_token_configured": bool(MESSENGER_VERIFY_TOKEN),
        "app_secret_configured": bool(META_APP_SECRET),
        "page_access_token_configured": bool(MESSENGER_PAGE_ACCESS_TOKEN),
        "ready": bool(MESSENGER_VERIFY_TOKEN and META_APP_SECRET and MESSENGER_PAGE_ACCESS_TOKEN),
    }


@meta_messenger_router.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if (
        MESSENGER_VERIFY_TOKEN
        and mode == "subscribe"
        and token
        and challenge is not None
        and hmac.compare_digest(token, MESSENGER_VERIFY_TOKEN)
    ):
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@meta_messenger_router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    raw = await request.body()
    if not _verify_signature(raw, request.headers.get("x-hub-signature-256")):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    background_tasks.add_task(_process, request.app.state.db, payload)
    return {"status": "accepted"}
