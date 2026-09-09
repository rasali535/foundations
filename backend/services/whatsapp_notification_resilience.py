import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional

from services.notification_service import NotificationService
from services.therapist_notification_service import TherapistNotificationService


_RETRY_DELAYS_SECONDS = (0, 4, 8, 12)
_RETRYABLE_MARKERS = (
    "HTTP 502",
    "HTTP 503",
    "HTTP 504",
    "ConnectionError",
    "ConnectTimeout",
)


def _is_retryable_failure(result: Any) -> bool:
    if result is None:
        return False
    if getattr(result, "status", None) != "failed":
        return False
    error_message = str(getattr(result, "error_message", "") or "")
    return any(marker in error_message for marker in _RETRYABLE_MARKERS)


async def _retry_transient_adapter_failure(
    call: Callable[[], Awaitable[Any]],
    label: str,
) -> Any:
    """Retry only transient Baileys/Render transport failures.

    The Baileys adapter currently runs on a Render free web service and can be cold when
    a booking is created after a period of inactivity. The first outbound request may
    receive a 502/503/504 while Render starts the service or while the WhatsApp socket
    reconnects. Retry with the same idempotency key so a transient cold start does not
    cause a lost booking confirmation.
    """
    last_result: Optional[Any] = None

    for attempt, delay in enumerate(_RETRY_DELAYS_SECONDS, start=1):
        if delay:
            await asyncio.sleep(delay)

        last_result = await call()
        if not _is_retryable_failure(last_result):
            return last_result

        if attempt < len(_RETRY_DELAYS_SECONDS):
            logging.warning(
                "%s WhatsApp confirmation hit a transient adapter failure; retrying attempt %s/%s",
                label,
                attempt + 1,
                len(_RETRY_DELAYS_SECONDS),
            )

    return last_result


def install_whatsapp_retry_wrappers() -> None:
    """Install retry wrappers once for both client and therapist WhatsApp sends."""
    current_client = NotificationService.send_booking_whatsapp
    if getattr(current_client, "_fca_resilient_wrapper", False):
        return

    current_therapist = TherapistNotificationService.send_booking_whatsapp

    async def client_send(
        db,
        client,
        bookings,
        booking_batch_id=None,
    ):
        return await _retry_transient_adapter_failure(
            lambda: current_client(
                db,
                client,
                bookings,
                booking_batch_id=booking_batch_id,
            ),
            "Client",
        )

    async def therapist_send(
        db,
        therapist,
        client,
        bookings,
        booking_batch_id=None,
    ):
        return await _retry_transient_adapter_failure(
            lambda: current_therapist(
                db,
                therapist,
                client,
                bookings,
                booking_batch_id=booking_batch_id,
            ),
            "Therapist",
        )

    client_send._fca_resilient_wrapper = True
    therapist_send._fca_resilient_wrapper = True

    NotificationService.send_booking_whatsapp = staticmethod(client_send)
    TherapistNotificationService.send_booking_whatsapp = staticmethod(therapist_send)
