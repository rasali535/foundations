from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mongomock_motor import AsyncMongoMockClient

from models import Booking, CRMClient
from services.booking_service import BookingService
from services.client_reschedule_service import ClientRescheduleService
from services.whatsapp_booking_bot_service import WhatsAppBookingBotService as Bot
from services.whatsapp_booking_bot_day_flow import install_day_first_flow
from services.aliana_conversation_service import AlianaConversationService
from services.notification_outbox import NotificationOutbox
from services.meta_whatsapp_template_service import MetaWhatsAppTemplateService
from services.notification_service import NotificationService
from services.therapist_service import TherapistService
from services.scheduling_service import SchedulingService
from routers.meta_whatsapp_router import _extract_message_text, _handle_therapist_booking_decision

install_day_first_flow(Bot)


async def fixture(monkeypatch):
    db = AsyncMongoMockClient()['reschedule']
    await NotificationOutbox.indexes(db)
    start = datetime.now(timezone.utc) + timedelta(days=3)
    client = CRMClient(id='client-1', client_number='FCA-1', first_name='Test', last_name='Client',
                       email='test@example.com', phone='+26771234567')
    booking = Booking(id='booking-12345', client_id=client.id, therapist_id='therapist-1',
        assignment_status='awaiting_acceptance', status='pending', session_type='individual',
        session_mode='in_person', starts_at=start.isoformat(), ends_at=(start+timedelta(minutes=50)).isoformat())
    await db.crm_clients.insert_one(client.model_dump())
    await db.bookings.insert_one(booking.model_dump())
    for i in range(2):
        await db.staff_users.insert_one({'user_id': f'admin-{i}', 'role': 'super_admin', 'active': True,
            'whatsapp_admin_enabled': True, 'whatsapp_phone': '+26770000000'})
    slot = {'therapist_id': 'therapist-2', 'starts_at': (start+timedelta(days=1)).isoformat(),
            'ends_at': (start+timedelta(days=1, minutes=50)).isoformat()}
    slots = AsyncMock(return_value=[slot])
    monkeypatch.setattr(ClientRescheduleService, 'slots', slots)
    return db, client, booking, slot, slots


@pytest.mark.asyncio
async def test_decline_request_client_date_time_and_acceptance(monkeypatch):
    db, client, booking, slot, slots = await fixture(monkeypatch)
    send = AsyncMock(return_value=SimpleNamespace(status='sent', provider_reference='sent-1', error_message=None))
    monkeypatch.setattr(MetaWhatsAppTemplateService, 'send', send)
    updated, error = await BookingService.therapist_decision(db, booking.id, 'therapist-1', 'decline', request_reschedule=True)
    assert not error and updated.reschedule_request_id
    await NotificationOutbox.dispatch(db)
    assert len([c for c in send.call_args_list if c.kwargs['event']=='admin_booking_declined']) == 2
    request_call = next(c for c in send.call_args_list if c.kwargs['event']=='reschedule_request')
    assert request_call.kwargs['variables']['reschedule_request_id'] == updated.reschedule_request_id
    payload = f'FCA_RESCHEDULE:{booking.id}:{updated.reschedule_request_id}'
    assert 'Choose an available day' in await AlianaConversationService.respond(db, 'whatsapp', client.phone, payload)
    assert 'CAT' in await Bot.handle_inbound(db, client.phone, '1')
    assert 'Confirm change' in await Bot.handle_inbound(db, client.phone, '1')
    assert 'Awaiting therapist confirmation' in await Bot.handle_inbound(db, client.phone, '1')
    saved = await db.bookings.find_one({'id': booking.id})
    assert saved['status'] == 'pending' and saved['assignment_status'] == 'awaiting_assignment'
    assert saved['starts_at'] == slot['starts_at'] and saved['therapist_id'] is None
    assert await db.bookings.count_documents({}) == 1
    assert 'no longer active' in await Bot.handle_inbound(db, client.phone, payload)
    assert not [c for c in send.call_args_list if c.kwargs['event']=='booking_confirmation']
    assert await db.admin_alerts.count_documents({'event': 'admin_booking_pending'}) == 1
    # Existing acceptance path is the only place that confirms and notifies.
    await db.bookings.update_one({'id': booking.id}, {'$set': {'therapist_id':'therapist-2', 'assignment_status':'awaiting_acceptance'}})
    monkeypatch.setattr(SchedulingService, 'provider', staticmethod(lambda:'local'))
    monkeypatch.setattr(TherapistService, 'get_therapist_by_id', AsyncMock(return_value=SimpleNamespace(id='therapist-2', default_location='FCA office')))
    monkeypatch.setattr(BookingService, 'check_therapist_conflict', AsyncMock(return_value=(False,None)))
    monkeypatch.setattr(NotificationService, 'send_booking_email', AsyncMock())
    confirmation = AsyncMock()
    monkeypatch.setattr(NotificationService, 'send_booking_whatsapp', confirmation)
    accepted, error = await BookingService.therapist_decision(db, booking.id, 'therapist-2', 'accept')
    assert not error and accepted.status == 'confirmed'
    confirmation.assert_awaited_once()


@pytest.mark.asyncio
async def test_ordinary_decline_does_not_request_and_authenticated_followup_deduplicates(monkeypatch):
    db, client, booking, *_ = await fixture(monkeypatch)
    declined, error = await BookingService.therapist_decision(db, booking.id, 'therapist-1', 'decline')
    assert not error and not declined.reschedule_request_id
    assert await db.notification_outbox.count_documents({'kind':'reschedule_request'}) == 0
    _, error = await ClientRescheduleService.request(db, booking.id, 'other-therapist')
    assert error
    await db.therapists.insert_one({'id':'therapist-1','name':'Therapist','active':True,'whatsapp_phone':'+26772222222'})
    assert 'queued' in await _handle_therapist_booking_decision(db, '+26772222222', f'RESCHEDULE {booking.id}')
    await ClientRescheduleService.request(db, booking.id, 'therapist-1')
    assert await db.notification_outbox.count_documents({'kind':'reschedule_request'}) == 1


@pytest.mark.asyncio
async def test_wrong_client_and_stale_request_rejected(monkeypatch):
    db, client, booking, *_ = await fixture(monkeypatch)
    requested, _ = await BookingService.therapist_decision(db, booking.id, 'therapist-1', 'decline', request_reschedule=True)
    await db.crm_clients.insert_one(CRMClient(id='other', client_number='FCA-2', first_name='Other', last_name='Client', email='other@example.com',phone='+26773333333').model_dump())
    payload = f'FCA_RESCHEDULE:{booking.id}:{requested.reschedule_request_id}'
    assert 'no longer active' in await Bot.handle_inbound(db, '+26773333333', payload)
    await db.bookings.update_one({'id':booking.id}, {'$set':{'assignment_status':'awaiting_acceptance','reschedule_request_id':None}})
    assert 'no longer active' in await Bot.handle_inbound(db, client.phone, payload)
    outcome = await NotificationOutbox._deliver(db, await db.notification_outbox.find_one({'kind':'reschedule_request'}))
    assert outcome[0] == 'cancelled'


@pytest.mark.asyncio
async def test_unavailable_selection_preserves_original_booking(monkeypatch):
    db, client, booking, slot, slots = await fixture(monkeypatch)
    requested, _ = await BookingService.therapist_decision(db, booking.id, 'therapist-1', 'decline', request_reschedule=True)
    await Bot.handle_inbound(db, client.phone, f'FCA_RESCHEDULE:{booking.id}:{requested.reschedule_request_id}')
    assert 'available day numbers' in await Bot.handle_inbound(db, client.phone, '0')
    await Bot.handle_inbound(db, client.phone, '1')
    await Bot.handle_inbound(db, client.phone, '1')
    slots.return_value=[]
    assert 'no longer available' in await Bot.handle_inbound(db, client.phone, '1')
    saved = await db.bookings.find_one({'id':booking.id})
    assert saved['starts_at']==booking.starts_at and saved['assignment_status']=='declined'


def test_template_button_payload_wins_over_label():
    payload = 'FCA_RESCHEDULE:booking-12345:request-id'
    assert _extract_message_text({'type':'button', 'button':{'text':'Choose another date', 'payload':payload}}) == payload


@pytest.mark.asyncio
@pytest.mark.parametrize('corporate', [False, True])
async def test_replacement_excludes_original_from_full_month_and_week(monkeypatch, corporate):
    from services.whatsapp_booking_bot_fast_slots import fast_slot_options
    from services.corporate_entitlement_service import CorporateEntitlementService
    db = AsyncMongoMockClient()['limits']
    start = datetime.now(timezone.utc) + timedelta(days=1)
    client = {'id':'client-limit', 'email':'member@example.com', 'monthly_session_limit':1}
    if corporate:
        client.update(organisation_id='org', organisation_contact_id='roster')
        await db.organisation_contacts.insert_one({'id':'roster','organisation_id':'org','active':True,
            'email_normalized':client['email'], 'base_session_allocation':1, 'extra_sessions_by_month':{}})
    await db.bookings.insert_one({'id':'original','client_id':client['id'],'organisation_id':client.get('organisation_id'),
        'starts_at':start.isoformat(), 'status':'pending'})
    therapist = SimpleNamespace(id='t', name='Therapist')
    monkeypatch.setattr(TherapistService, 'list_therapists', AsyncMock(return_value=[therapist]))
    monkeypatch.setattr(SchedulingService, 'get_available_slots', AsyncMock(return_value=[{
        'starts_at':(start+timedelta(hours=1)).isoformat(), 'ends_at':(start+timedelta(hours=2)).isoformat(), 'is_available':True}]))
    slots = await fast_slot_options(db, client, 'in_person', exclude_booking_id='original')
    assert len(slots)==1
    if corporate:
        ordinary = await CorporateEntitlementService.remaining_for_client(db, client, reference=start)
        assert ordinary['remaining']==0 and ordinary['used']==1
        assert await CorporateEntitlementService.has_weekly_booking(db, client, start)


@pytest.mark.asyncio
async def test_template_sends_three_body_variables_and_booking_bound_button(monkeypatch):
    import services.meta_whatsapp_template_service as module
    db = AsyncMongoMockClient()['template']
    monkeypatch.setattr(module, 'WHATSAPP_PHONE_NUMBER_ID','test-phone')
    monkeypatch.setattr(module, 'WHATSAPP_ACCESS_TOKEN','test-token')
    payloads=[]
    class Response:
        status_code=200
        content=b'{}'
        def json(self):
            return {'messages':[{'id':'meta-test'}]}
    def post(url, **kwargs):
        payloads.append(kwargs['json'])
        return Response()
    monkeypatch.setattr(module.requests,'post',post)
    await MetaWhatsAppTemplateService.send(db,phone='+26771234567', event='reschedule_request',
        variables={'client_name':'Test','appointment_date':'Tomorrow','appointment_time':'10:00 CAT','reschedule_request_id':'request-1'},
        client_id='client', booking_id='booking-12345')
    components=payloads[0]['template']['components']
    assert len(components[0]['parameters'])==3
    assert components[1]['parameters'][0]['payload']=='FCA_RESCHEDULE:booking-12345:request-1'


@pytest.mark.asyncio
async def test_old_reminder_cancelled_after_move_and_new_time_used(monkeypatch):
    from services.whatsapp_reminder_dispatcher import WhatsAppReminderDispatcher
    db, client, booking, slot, slots = await fixture(monkeypatch)
    requested, _ = await BookingService.therapist_decision(db, booking.id, 'therapist-1','decline', request_reschedule=True)
    await NotificationOutbox.enqueue(db, 'old-reminder','reminder', {'booking_id':booking.id,
        'starts_at':booking.starts_at, 'event':'booking_reminder_6h'})
    await Bot.handle_inbound(db,client.phone,f'FCA_RESCHEDULE:{booking.id}:{requested.reschedule_request_id}')
    for reply in ['1','1','1']:
        await Bot.handle_inbound(db,client.phone,reply)
    await db.bookings.update_one({'id':booking.id},{'$set':{'status':'confirmed','assignment_status':'accepted'}})
    old=await db.notification_outbox.find_one({'event_key':'old-reminder'})
    assert (await NotificationOutbox._deliver(db,old))[0]=='cancelled'
    due = datetime.fromisoformat(slot['starts_at'])-timedelta(hours=6)
    monkeypatch.setattr('services.whatsapp_reminder_dispatcher.utc_now',lambda:due)
    monkeypatch.setattr(NotificationOutbox,'dispatch',AsyncMock())
    await WhatsAppReminderDispatcher.dispatch_due(db)
    new=await db.notification_outbox.find_one({'kind':'reminder','payload.starts_at':slot['starts_at']})
    assert new and new['payload']['event']=='booking_reminder_6h'
