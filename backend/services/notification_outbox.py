"""Durable, bounded notification delivery. No clinical answers in queue payloads."""
import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from models import Booking, CRMClient


def utc_now():
    return datetime.now(timezone.utc)


def utc_datetime(value):
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def retryable(error):
    # A response timeout has an ambiguous outcome; do not blindly resend it.
    return any(marker in str(error or '') for marker in (
        'HTTP 429', 'HTTP 500', 'HTTP 502', 'HTTP 503', 'HTTP 504',
        'ConnectTimeout', 'ConnectionError',
    ))


def initial_failure_status(error):
    if any(marker in str(error or '') for marker in ('ReadTimeout', 'TimeoutError')):
        return 'delivery_unknown'
    return 'pending' if retryable(error) else 'failed'


class NotificationOutbox:
    @staticmethod
    async def indexes(db):
        await db.notification_outbox.create_index('event_key', unique=True)
        await db.notification_outbox.create_index([('status', 1), ('next_attempt_at', 1)])
        await db.admin_alerts.create_index('event_key', unique=True)

    @staticmethod
    async def enqueue(db, key, kind, payload, due_at=None, status="pending", error=None):
        now = utc_now().isoformat()
        doc = dict(event_key=key, kind=kind, payload=payload, status=status,
                   attempts=0, error_message=error, created_at=now, due_at=due_at or now, next_attempt_at=due_at or now)
        try:
            await db.notification_outbox.update_one(
                {'event_key': key}, {'$setOnInsert': doc}, upsert=True)
        except DuplicateKeyError:
            pass  # Another process queued this same logical notification.

    @staticmethod
    async def admin_alert(db, event, reference, client_id, booking_id=None, url=None):
        now = utc_now().isoformat()
        key = f'{event}:{reference}'
        try:
            await db.admin_alerts.update_one({'event_key': key}, {'$setOnInsert': {
                'event_key': key, 'event': event, 'reference': reference,
                'url': url or '/admin/dashboard', 'created_at': now, 'read_by': [],
            }}, upsert=True)
        except DuplicateKeyError:
            pass
        admins = await db.staff_users.find({
            'role': {'$in': ['admin', 'super_admin']}, 'active': {'$ne': False},
            'whatsapp_admin_enabled': True,
        }, {'_id': 0}).to_list(None)
        for admin in admins:
            recipient_key = hashlib.sha256(admin['user_id'].lower().encode()).hexdigest()
            await NotificationOutbox.enqueue(db, f'{key}:{recipient_key}', 'admin', {
                'staff_user_id': admin['user_id'], 'event': event,
                'reference': reference, 'submitted_at': now,
                'client_id': client_id, 'booking_id': booking_id,
            })

    @staticmethod
    async def _deliver(db, job):
        from services.meta_whatsapp_template_service import MetaWhatsAppTemplateService
        from services.therapist_notification_service import TherapistNotificationService
        from services.notification_service import NotificationService
        p = job['payload']
        if job['kind'] == 'admin':
            admin = await db.staff_users.find_one({'user_id': p['staff_user_id']}, {'_id': 0})
            if not admin or admin.get('active') is False or not admin.get('whatsapp_admin_enabled') or admin.get('role') not in ('admin', 'super_admin'):
                return 'cancelled', None, None
            booking = await db.bookings.find_one({'id': p.get('booking_id')}, {'_id': 0}) if p.get('booking_id') else None
            if p['event'] != 'admin_intake_received' and (not booking or booking.get('status') != 'pending' or booking.get('assignment_status') not in ('awaiting_assignment', 'declined')):
                return 'cancelled', None, None
            variables = {'reference': p['reference'], 'submitted_at': utc_datetime(p['submitted_at']).astimezone(ZoneInfo('Africa/Gaborone')).strftime('%d %b %Y at %H:%M CAT')}
            result = await MetaWhatsAppTemplateService.send(db, phone=admin.get('whatsapp_phone'),
                event=p['event'], variables=variables, client_id=p['client_id'], booking_id=p.get('booking_id'))
        elif job['kind'] == 'intake_email':
            result = await NotificationService.send_secure_intake_alert(p)
            await db.crm_intake_submissions.update_one({'id': p['intake_id']}, {'$set': {
                'notification_status': result['notification_status'], 'notification_reference': result.get('notification_reference'),
                'notification_updated_at': utc_now().isoformat(),
            }})
            return result['notification_status'], result.get('notification_reference'), result.get('notification_error')
        elif job['kind'] == 'client_intake':
            client = await db.crm_clients.find_one({'id': p['client_id']}, {'_id': 0})
            if not client:
                return 'cancelled', None, None
            result = await MetaWhatsAppTemplateService.send(db, phone=client.get('phone'),
                event='intake_received', variables={'client_name': client.get('first_name') or 'Client'}, client_id=p['client_id'])
        else:
            booking = await db.bookings.find_one({'id': p['booking_id']}, {'_id': 0})
            if not booking or booking.get('status') not in ('pending', 'confirmed'):
                return 'cancelled', None, None
            if p.get('starts_at') and utc_datetime(booking['starts_at']).isoformat() != p['starts_at']:
                return 'cancelled', None, None
            if utc_datetime(booking['starts_at']) <= utc_now():
                return 'expired', None, None
            if job['kind'] == 'reschedule_request':
                if booking.get('assignment_status') != 'declined' or booking.get('reschedule_request_id') != p['request_id']:
                    return 'cancelled', None, None
                client = await db.crm_clients.find_one({'id': booking['client_id']}, {'_id': 0})
                if not client:
                    return 'failed', None, 'Client record unavailable'
                local = utc_datetime(booking['starts_at']).astimezone(ZoneInfo('Africa/Gaborone'))
                result = await MetaWhatsAppTemplateService.send(db, phone=client.get('phone'),
                    event='reschedule_request', variables={'client_name': client.get('first_name') or 'Client',
                    'appointment_date': local.strftime('%a %d %b %Y'), 'appointment_time': local.strftime('%H:%M CAT'),
                    'reschedule_request_id': p['request_id']}, client_id=client['id'], booking_id=booking['id'])
            elif job['kind'] == 'client_booking':
                if booking.get('status') != 'confirmed':
                    return 'cancelled', None, None
                client = await db.crm_clients.find_one({'id': booking['client_id']}, {'_id': 0})
                if not client:
                    return 'failed', None, 'Client record unavailable'
                result = await NotificationService.send_booking_whatsapp(db, CRMClient(**client), [Booking(**booking)])
            elif job['kind'] == 'therapist':
                if booking.get('therapist_id') != p['therapist_id'] or booking.get('assignment_status') not in ('awaiting_acceptance', 'accepted'):
                    return 'cancelled', None, None
                therapist = await db.therapists.find_one({'id': p['therapist_id']}, {'_id': 0})
                client = await db.crm_clients.find_one({'id': booking['client_id']}, {'_id': 0})
                if not therapist or not client:
                    return 'failed', None, 'Therapist or client record unavailable'
                from types import SimpleNamespace
                result = await TherapistNotificationService.send_booking_whatsapp(
                    db, SimpleNamespace(**therapist), CRMClient(**client), [Booking(**booking)])
                if result is None:
                    return 'cancelled', None, None
            else:
                if booking.get('status') != 'confirmed':
                    return 'cancelled', None, None
                grace = int(os.environ.get('WHATSAPP_REMINDER_GRACE_MINUTES', '60'))
                if utc_datetime(job.get('due_at', job['next_attempt_at'])) < utc_now() - timedelta(minutes=grace):
                    return 'expired', None, 'Reminder missed its delivery grace period'
                if p['event'] == 'virtual_session_link' and (booking.get('session_mode') != 'virtual' or not booking.get('virtual_meeting_link')):
                    return 'cancelled', None, None
                client = await db.crm_clients.find_one({'id': booking['client_id']}, {'_id': 0})
                if not client:
                    return 'failed', None, 'Client record unavailable'
                from services.whatsapp_reminder_dispatcher import reminder_variables
                result = await MetaWhatsAppTemplateService.send(db, phone=client.get('phone'),
                    event=p['event'], variables=reminder_variables(booking, client, p['event']),
                    client_id=booking['client_id'], booking_id=booking['id'], booking_batch_id=booking.get('booking_batch_id'))
        return result.status, result.provider_reference, result.error_message

    @staticmethod
    async def dispatch(db, limit=100):
        now = utc_now()
        # A crashed sender may already have reached Meta. Keep it visible for review
        # rather than automatically sending a possible duplicate.
        await db.notification_outbox.update_many(
            {'status': 'processing', 'lease_until': {'$lt': now.isoformat()}},
            {'$set': {'status': 'delivery_unknown', 'error_message': 'Sender interrupted; verify delivery before retrying'}})
        # Reconcile callbacks that arrived before the sender stored its reference.
        async for accepted in db.notification_outbox.find({'status': 'sent', 'provider_reference': {'$ne': None}}, {'_id': 0}):
            log = await db.notification_log.find_one({'provider_reference': accepted['provider_reference']}, {'_id': 0})
            if log and log.get('status') in ('delivered', 'read', 'failed'):
                await db.notification_outbox.update_one({'event_key': accepted['event_key'], 'status': 'sent'},
                    {'$set': {'status': log['status'], 'error_message': log.get('error_message'), 'updated_at': utc_now().isoformat()}})
        count = 0
        for _ in range(limit):
            token = str(uuid.uuid4())
            job = await db.notification_outbox.find_one_and_update(
                {'status': {'$in': ['pending', 'retrying']}, 'next_attempt_at': {'$lte': utc_now().isoformat()}},
                {'$set': {'status': 'processing', 'lease_token': token,
                          'lease_until': (utc_now() + timedelta(minutes=10)).isoformat()}, '$inc': {'attempts': 1}},
                sort=[('next_attempt_at', 1)], return_document=ReturnDocument.AFTER)
            if not job:
                break
            try:
                status, reference, error = await NotificationOutbox._deliver(db, job)
            except Exception as exc:
                status, reference, error = 'delivery_unknown', None, exc.__class__.__name__
                logging.warning('Notification delivery interrupted event=%s error=%s', job['event_key'], error)
            update = {'status': status, 'provider_reference': reference, 'error_message': error,
                      'updated_at': utc_now().isoformat()}
            if status == 'failed' and retryable(error) and job['attempts'] < 5:
                update.update(status='retrying', next_attempt_at=(utc_now() + timedelta(minutes=2 ** job['attempts'])).isoformat())
            elif status == 'failed' and any(x in str(error) for x in ('ReadTimeout', 'TimeoutError')):
                update['status'] = 'delivery_unknown'
            await db.notification_outbox.update_one({'event_key': job['event_key'], 'lease_token': token}, {'$set': update})
            count += 1
        return count
