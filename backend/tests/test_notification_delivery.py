from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from mongomock_motor import AsyncMongoMockClient

from models import NotificationLog
from services.notification_outbox import NotificationOutbox
from services.whatsapp_reminder_dispatcher import WhatsAppReminderDispatcher
from services.meta_whatsapp_template_service import MetaWhatsAppTemplateService
from services.phone_validation import international_phone


async def database():
    db = AsyncMongoMockClient()['notifications']
    await NotificationOutbox.indexes(db)
    return db


def clock(monkeypatch, now):
    monkeypatch.setattr('services.notification_outbox.utc_now', lambda: now)
    monkeypatch.setattr('services.whatsapp_reminder_dispatcher.utc_now', lambda: now)


@pytest.mark.asyncio
async def test_two_admins_dedup_and_no_clinical_content(monkeypatch):
    db = await database()
    for name in ('first', 'second'):
        await db.staff_users.insert_one({'user_id': name, 'role': 'super_admin', 'active': True,
            'whatsapp_admin_enabled': True, 'whatsapp_phone': '+26771234567'})
    await db.staff_users.insert_one({'user_id': 'disabled', 'role': 'super_admin', 'whatsapp_admin_enabled': False})
    await NotificationOutbox.admin_alert(db, 'admin_intake_received', 'intake-1', 'client-1')
    await NotificationOutbox.admin_alert(db, 'admin_intake_received', 'intake-1', 'client-1')
    assert await db.notification_outbox.count_documents({}) == 2
    assert await db.admin_alerts.count_documents({}) == 1
    calls = []
    async def send(db, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status='sent', provider_reference=str(len(calls)), error_message=None)
    monkeypatch.setattr(MetaWhatsAppTemplateService, 'send', send)
    await NotificationOutbox.dispatch(db)
    await NotificationOutbox.dispatch(db)
    assert len(calls) == 2
    assert set(calls[0]['variables']) == {'reference', 'submitted_at'}


@pytest.mark.asyncio
async def test_reminder_offset_catchup_and_no_duplicate(monkeypatch):
    db = await database()
    now = datetime(2026, 10, 5, 2, 5, tzinfo=timezone.utc)
    clock(monkeypatch, now)
    await db.crm_clients.insert_one({'id': 'c', 'first_name': 'Client', 'phone': '+26771234567'})
    await db.bookings.insert_one({'id': 'b', 'client_id': 'c', 'status': 'confirmed',
        'starts_at': '2026-10-05T10:00:00+02:00', 'session_mode': 'in_person'})
    calls = []
    async def send(db, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status='sent', provider_reference='wamid1', error_message=None)
    monkeypatch.setattr(MetaWhatsAppTemplateService, 'send', send)
    await WhatsAppReminderDispatcher.dispatch_due(db)
    await WhatsAppReminderDispatcher.dispatch_due(db)
    assert len(calls) == 1
    assert calls[0]['event'] == 'booking_reminder_6h'
    assert calls[0]['variables']['appointment_time'] == '10:00 CAT'


@pytest.mark.asyncio
async def test_virtual_link_requires_virtual_booking_and_link(monkeypatch):
    db = await database()
    clock(monkeypatch, datetime(2026, 10, 5, 5, 5, tzinfo=timezone.utc))
    await db.crm_clients.insert_one({'id': 'c', 'phone': '+26771234567'})
    for ident, mode, link in [('valid', 'virtual', 'https://example.com/session'), ('missing', 'virtual', ''), ('physical', 'in_person', 'https://example.com/session')]:
        await db.bookings.insert_one({'id': ident, 'client_id': 'c', 'status': 'confirmed',
            'starts_at': '2026-10-05T08:00:00Z', 'session_mode': mode, 'virtual_meeting_link': link})
    calls = []
    async def send(db, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status='sent', provider_reference='wamid', error_message=None)
    monkeypatch.setattr(MetaWhatsAppTemplateService, 'send', send)
    await WhatsAppReminderDispatcher.dispatch_due(db)
    assert len(calls) == 1
    assert calls[0]['booking_id'] == 'valid'
    assert calls[0]['event'] == 'virtual_session_link'


@pytest.mark.asyncio
async def test_retry_bounded_and_permanent_failures_stop(monkeypatch):
    db = await database()
    now = datetime(2026, 10, 5, tzinfo=timezone.utc)
    clock(monkeypatch, now)
    await NotificationOutbox.enqueue(db, 'retry', 'test', {})
    await NotificationOutbox.enqueue(db, 'permanent', 'test', {})
    async def deliver(db, job):
        return 'failed', None, 'HTTP 503' if job['event_key'] == 'retry' else 'Invalid phone'
    monkeypatch.setattr(NotificationOutbox, '_deliver', deliver)
    for _ in range(6):
        await NotificationOutbox.dispatch(db)
        now += timedelta(hours=1)
        clock(monkeypatch, now)
    jobs = {j['event_key']: j async for j in db.notification_outbox.find({})}
    assert jobs['retry']['attempts'] == 5 and jobs['retry']['status'] == 'failed'
    assert jobs['permanent']['attempts'] == 1


@pytest.mark.asyncio
async def test_lease_prevents_concurrent_sends_and_crash_is_unknown(monkeypatch):
    import asyncio
    db = await database()
    now = datetime(2026, 10, 5, tzinfo=timezone.utc)
    clock(monkeypatch, now)
    await NotificationOutbox.enqueue(db, 'one', 'test', {})
    calls = []
    async def deliver(db, job):
        calls.append(job['event_key'])
        await asyncio.sleep(0)
        return 'sent', 'wamid', None
    monkeypatch.setattr(NotificationOutbox, '_deliver', deliver)
    await asyncio.gather(NotificationOutbox.dispatch(db), NotificationOutbox.dispatch(db))
    assert calls == ['one']
    await db.notification_outbox.insert_one({'event_key': 'crash', 'status': 'processing', 'lease_until': (now-timedelta(minutes=1)).isoformat()})
    await NotificationOutbox.dispatch(db)
    assert (await db.notification_outbox.find_one({'event_key': 'crash'}))['status'] == 'delivery_unknown'


@pytest.mark.asyncio
async def test_stale_reminder_and_started_session_never_send(monkeypatch):
    db = await database()
    now = datetime(2026, 10, 5, 8, tzinfo=timezone.utc)
    clock(monkeypatch, now)
    await db.bookings.insert_one({'id': 'b', 'client_id': 'c', 'status': 'confirmed', 'starts_at': now.isoformat()})
    await NotificationOutbox.enqueue(db, 'started', 'reminder', {'booking_id': 'b', 'starts_at': now.isoformat(), 'event': 'booking_reminder_6h'})
    await NotificationOutbox.dispatch(db)
    assert (await db.notification_outbox.find_one({'event_key': 'started'}))['status'] == 'expired'
    await db.bookings.update_one({'id': 'b'}, {'$set': {'starts_at': (now+timedelta(hours=5)).isoformat()}})
    await NotificationOutbox.enqueue(db, 'rescheduled', 'reminder', {'booking_id': 'b', 'starts_at': (now+timedelta(hours=6)).isoformat(), 'event': 'booking_reminder_6h'})
    await NotificationOutbox.dispatch(db)
    assert (await db.notification_outbox.find_one({'event_key': 'rescheduled'}))['status'] == 'cancelled'


@pytest.mark.parametrize('bad', ['71234567', '26771234567', '+00012345678', '+267abc71234567'])
def test_phone_requires_explicit_country_code(bad):
    with pytest.raises(ValueError):
        international_phone(bad)


def test_phone_formatting_only():
    assert international_phone('+267 71-234-567') == '+26771234567'

@pytest.mark.asyncio
async def test_acknowledgement_is_per_admin_and_non_admin_is_denied():
    from starlette.requests import Request
    from fastapi import HTTPException
    from routers.admin_router import list_admin_alerts, acknowledge_admin_alerts, require_admin
    db = await database()
    await NotificationOutbox.admin_alert(db, 'admin_intake_received', 'i', 'c')
    def request(user, role, body=b'{"event_keys":["admin_intake_received:i"]}'):
        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}
        return Request({'type': 'http', 'session': {'user_id': user, 'role': role},
            'app': SimpleNamespace(state=SimpleNamespace(db=db))}, receive)
    first = request('first', 'super_admin')
    second = request('second', 'super_admin')
    assert (await list_admin_alerts(first, require_admin(first)))['unread'] == 1
    await acknowledge_admin_alerts(first, require_admin(first))
    assert (await list_admin_alerts(first, require_admin(first)))['unread'] == 0
    assert (await list_admin_alerts(second, require_admin(second)))['unread'] == 1
    with pytest.raises(HTTPException) as exc:
        require_admin(request('therapist', 'therapist'))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_meta_delivery_callback_updates_queue():
    from routers.meta_whatsapp_router import _process_status_updates
    db = await database()
    await db.notification_log.insert_one({'provider_reference': 'wamid-test', 'status': 'sent'})
    await db.notification_outbox.insert_one({'event_key': 'test', 'provider_reference': 'wamid-test', 'status': 'sent'})
    await _process_status_updates(db, {'entry': [{'changes': [{'field': 'messages', 'value': {'statuses': [{'id': 'wamid-test', 'status': 'delivered', 'timestamp': '100'}]}}]}]})
    assert (await db.notification_outbox.find_one({'event_key': 'test'}))['status'] == 'delivered'
    assert (await db.notification_log.find_one({'provider_reference': 'wamid-test'}))['status'] == 'delivered'


@pytest.mark.asyncio
async def test_concurrent_admin_allocations_do_not_overwrite(monkeypatch):
    import asyncio
    from services.booking_service import BookingService
    from services.scheduling_service import SchedulingService
    from services.therapist_notification_service import TherapistNotificationService
    from tests.test_booking_request_approval_flow import _seed
    from models import BookingCreateRequest
    db = await database()
    await _seed(db)
    monkeypatch.setattr(SchedulingService, 'provider', staticmethod(lambda: 'internal'))
    async def no_message(*args, **kwargs):
        return None
    monkeypatch.setattr(TherapistNotificationService, 'send_booking_whatsapp', no_message)
    request = BookingCreateRequest(client_id='client-pending-1', session_mode='in_person', session_type='individual',
        starts_at='2026-10-06T09:00:00+00:00', ends_at='2026-10-06T10:00:00+00:00', send_notifications=False)
    booking, error = await BookingService.create_booking_request(db, request)
    assert not error
    # Force both calls to observe the same unassigned record before CAS updates.
    original = BookingService.check_therapist_conflict
    arrived = 0
    ready = asyncio.Event()
    async def barrier(*args, **kwargs):
        nonlocal arrived
        arrived += 1
        if arrived == 2:
            ready.set()
        await ready.wait()
        return await original(*args, **kwargs)
    monkeypatch.setattr(BookingService, 'check_therapist_conflict', barrier)
    results = await asyncio.gather(*[BookingService.assign_therapist(db, booking.id, 'therapist-pending-1', actor_id=admin) for admin in ('first', 'second')])
    assert sum(result[0] is not None for result in results) == 1
    assert sum(result[1] is not None for result in results) == 1

@pytest.mark.asyncio
async def test_out_of_order_provider_callbacks_never_downgrade_read():
    from routers.meta_whatsapp_router import _process_status_updates
    db = await database()
    await db.notification_log.insert_one({'provider_reference': 'wamid-read', 'status': 'read'})
    await db.notification_outbox.insert_one({'event_key': 'read', 'provider_reference': 'wamid-read', 'status': 'read'})
    for status in ('sent', 'delivered', 'failed'):
        await _process_status_updates(db, {'entry': [{'changes': [{'field': 'messages', 'value': {'statuses': [{'id': 'wamid-read', 'status': status}]}}]}]})
    assert (await db.notification_log.find_one({'provider_reference': 'wamid-read'}))['status'] == 'read'
    assert (await db.notification_outbox.find_one({'event_key': 'read'}))['status'] == 'read'


@pytest.mark.asyncio
async def test_manual_retry_of_old_failed_confirmation_is_deduplicated():
    from routers.admin_router import retry_failed_transmission
    from starlette.requests import Request
    db = await database()
    start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    await db.bookings.insert_one({'id': 'b', 'client_id': 'c', 'status': 'confirmed', 'starts_at': start})
    await db.notification_log.insert_one({'id': 'old', 'channel': 'whatsapp', 'status': 'failed',
        'template': 'booking_confirmation', 'booking_id': 'b', 'client_id': 'c', 'error_message': 'Invalid phone'})
    request = Request({'type': 'http', 'app': SimpleNamespace(state=SimpleNamespace(db=db))})
    result = await retry_failed_transmission('old', request, {'user_id': 'admin'})
    await db.notification_outbox.update_one({'event_key': result['event_key']}, {'$set': {'status': 'delivered'}})
    await retry_failed_transmission('old', request, {'user_id': 'admin'})
    assert await db.notification_outbox.count_documents({}) == 1
    assert (await db.notification_outbox.find_one({}))['status'] == 'delivered'
