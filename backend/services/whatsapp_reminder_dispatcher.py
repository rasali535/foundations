import asyncio
import logging
import os
from datetime import timedelta
from zoneinfo import ZoneInfo

from services.notification_outbox import NotificationOutbox, utc_datetime, utc_now

CAT_TZ = ZoneInfo('Africa/Gaborone')
POLL_SECONDS = int(os.environ.get('WHATSAPP_REMINDER_POLL_SECONDS', '60'))


def reminder_variables(booking, client, event):
    local = utc_datetime(booking['starts_at']).astimezone(CAT_TZ)
    variables = {'client_name': client.get('first_name') or 'Client',
                 'appointment_date': local.strftime('%a %d %b %Y'),
                 'appointment_time': local.strftime('%H:%M CAT')}
    if event == 'booking_reminder_2h':
        variables.pop('appointment_date')
    if event == 'virtual_session_link':
        variables['session_link'] = booking['virtual_meeting_link']
    return variables


class WhatsAppReminderDispatcher:
    EVENTS = (('booking_reminder_24h', 1440), ('booking_reminder_6h', 360),
              ('virtual_session_link', 180), ('booking_reminder_2h', 120))

    @staticmethod
    async def dispatch_due(db):
        now = utc_now()
        grace = timedelta(minutes=int(os.environ.get('WHATSAPP_REMINDER_GRACE_MINUTES', '60')))
        # Legacy records retain their offsets. Parse dates before comparing so
        # +02:00, +00:00 and Z represent the same instant correctly.
        async for booking in db.bookings.find({'status': 'confirmed'}, {'_id': 0}):
            try:
                start = utc_datetime(booking['starts_at'])
            except (ValueError, TypeError, KeyError):
                logging.warning('Reminder skipped: invalid booking timestamp id=%s', booking.get('id'))
                continue
            if start <= now:
                continue
            for event, lead in WhatsAppReminderDispatcher.EVENTS:
                due = start - timedelta(minutes=lead)
                if due > now or due < now - grace:
                    continue
                if event == 'virtual_session_link' and (booking.get('session_mode') != 'virtual' or not booking.get('virtual_meeting_link')):
                    continue
                # Honour successful claims from the previous dispatcher.
                old_claim = await db.whatsapp_dispatch_claims.find_one({'event_key': f"{booking['id']}:{event}"})
                if old_claim:
                    try:
                        if abs(utc_datetime(old_claim['created_at']) - due) <= grace:
                            continue
                    except (ValueError, KeyError, TypeError):
                        continue  # Unknown legacy delivery: do not risk a duplicate.
                key = f"reminder:{booking['id']}:{start.isoformat()}:{event}"
                await NotificationOutbox.enqueue(db, key, 'reminder', {
                    'booking_id': booking['id'], 'starts_at': start.isoformat(), 'event': event,
                }, due.isoformat())
        return await NotificationOutbox.dispatch(db)

    @staticmethod
    async def run_forever(db):
        while True:
            try:
                await WhatsAppReminderDispatcher.dispatch_due(db)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logging.warning('WhatsApp reminder dispatcher cycle failed: %s', exc.__class__.__name__)
            await asyncio.sleep(max(POLL_SECONDS, 30))
