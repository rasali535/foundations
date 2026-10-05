"""Client-owned replacement of a declined, unconfirmed appointment."""
from datetime import datetime, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from models import Booking, now_iso
from services.notification_outbox import NotificationOutbox, utc_datetime
from services.whatsapp_booking_bot_fast_slots import fast_slot_options, MonthlySessionLimitReached, SchedulingAvailabilityError


class ClientRescheduleService:
    @staticmethod
    async def request(db, booking_id, therapist_id):
        query = {'id': booking_id, 'status': 'pending', 'assignment_status': 'declined',
                 'declined_by_therapist_id': therapist_id}
        booking = await db.bookings.find_one(query, {'_id': 0})
        if not booking:
            return None, 'This declined appointment is no longer available to this therapist.'
        if utc_datetime(booking['starts_at']) <= datetime.now(timezone.utc):
            return None, 'This appointment has already passed. Contact FCA administration.'
        request_id = booking.get('reschedule_request_id') or str(uuid4())
        if not booking.get('reschedule_request_id'):
            result = await db.bookings.update_one({**query, 'reschedule_request_id': None},
                {'$set': {'reschedule_request_id': request_id, 'updated_at': now_iso()}})
            if not result.modified_count:
                return None, 'The booking changed. Refresh and try again.'
        await NotificationOutbox.enqueue(db, f'reschedule-request:{booking_id}:{request_id}',
            'reschedule_request', {'booking_id': booking_id, 'request_id': request_id,
            'starts_at': utc_datetime(booking['starts_at']).isoformat()})
        booking['reschedule_request_id'] = request_id
        return Booking(**booking), None

    @staticmethod
    async def slots(db, client, booking):
        slots = await fast_slot_options(db, client, booking['session_mode'],
            booking['session_type'], exclude_booking_id=booking['id'])
        return [slot for slot in slots if utc_datetime(slot['starts_at']) != utc_datetime(booking['starts_at'])]

    @staticmethod
    async def handle(db, sender, text, bot):
        from services.whatsapp_booking_bot_day_flow import _day_key, _render_days, _render_times, _unique_time_slots
        upper = text.upper()
        session = await bot._get_session(db, sender)
        state = session.get('state', 'menu')
        command = upper.startswith('FCA_RESCHEDULE:') or upper in {'RESCHEDULE', 'CHOOSE ANOTHER DATE'} or (upper == '3' and state == 'menu')
        if upper in {'MENU', 'START', 'HELP', 'BOT', 'BOOK', 'BOOK APPOINTMENT', 'MY BOOKINGS', 'MY APPOINTMENTS', 'AGENT', 'HUMAN', 'FCA'} or upper.startswith('BOOK '):
            return None
        if not command and not state.startswith('reschedule_'):
            return None
        client, _ = await bot._resolve_client(db, sender)
        if not client:
            return 'We could not securely match this number to a client. Please contact FCA.'
        context = session.get('context') or {}
        if command:
            if upper.startswith('FCA_RESCHEDULE:'):
                parts = text.split(':')
                if len(parts) != 3:
                    return 'This reschedule request is invalid. Contact FCA.'
                booking_id, request_id = parts[1:]
            else:
                rows = await db.bookings.find({'client_id': client['id'], 'status': 'pending',
                    'assignment_status': 'declined', 'reschedule_request_id': {'$nin': [None, '']}}, {'_id': 0}).to_list(None)
                rows = [b for b in rows if utc_datetime(b['starts_at']) > datetime.now(timezone.utc)]
                if not rows:
                    return 'There are no active requests to choose another date. Contact FCA for help rescheduling an appointment.'
                if len(rows) > 1:
                    return 'Please tap Choose another date on the message for the appointment you want to change.'
                booking_id, request_id = rows[0]['id'], rows[0]['reschedule_request_id']
            context = {'booking_id': booking_id, 'request_id': request_id}
        booking = await db.bookings.find_one({'id': context.get('booking_id'), 'client_id': client['id'],
            'status': 'pending', 'assignment_status': 'declined',
            'reschedule_request_id': context.get('request_id')}, {'_id': 0})
        if not booking or not context.get('request_id'):
            await bot._save_session(db, sender, client['id'], 'menu', {})
            return 'This reschedule request is no longer active. Send MY BOOKINGS to view your appointments.'
        if utc_datetime(booking['starts_at']) <= datetime.now(timezone.utc):
            await bot._save_session(db, sender, client['id'], 'menu', {})
            return 'This appointment has passed. Please contact FCA for help.'

        async def show_days():
            try:
                slots = await ClientRescheduleService.slots(db, client, booking)
            except (MonthlySessionLimitReached, SchedulingAvailabilityError):
                return 'Available appointments could not be offered right now. Send MENU, then 6 to contact FCA. Your booking has not changed.'
            if not slots:
                return 'No alternative appointments are currently available. Send MENU, then 6 to contact FCA. Your booking has not changed.'
            context.update(slots=slots, day_keys=sorted({_day_key(s) for s in slots}))
            await bot._save_session(db, sender, client['id'], 'reschedule_day', context)
            return _render_days(context['day_keys'])

        if command or (state == 'reschedule_time' and text == '0') or (state == 'reschedule_confirm' and text == '2'):
            return await show_days()
        if state == 'reschedule_day':
            try:
                index = int(text) - 1
                if index < 0:
                    raise ValueError
                day = context['day_keys'][index]
            except (ValueError, IndexError, KeyError):
                return 'Please reply with one of the available day numbers.'
            context.update(selected_day=day, time_slots=_unique_time_slots([s for s in context['slots'] if _day_key(s) == day]))
            await bot._save_session(db, sender, client['id'], 'reschedule_time', context)
            return _render_times(day, context['time_slots'])
        if state == 'reschedule_time':
            try:
                index = int(text) - 1
                if index < 0:
                    raise ValueError
                context['selected_slot'] = context['time_slots'][index]
            except (ValueError, IndexError, KeyError):
                return 'Please reply with an available time number, or 0 to choose another day.'
            await bot._save_session(db, sender, client['id'], 'reschedule_confirm', context)
            local = utc_datetime(context['selected_slot']['starts_at']).astimezone(ZoneInfo('Africa/Gaborone'))
            return (f"Request this new appointment?\n{local.strftime('%a %d %b %Y at %H:%M CAT')}\n\n"
                    '1. Confirm change\n2. Choose another date\n\nThe new appointment will await therapist confirmation.')
        if state != 'reschedule_confirm' or text != '1':
            return 'Reply 1 to confirm the change or 2 to choose another date.'
        selected = context.get('selected_slot') or {}
        try:
            fresh = await ClientRescheduleService.slots(db, client, booking)
        except (MonthlySessionLimitReached, SchedulingAvailabilityError):
            return 'The new appointment could not be verified. Try again later or contact FCA. Your booking has not changed.'
        valid = next((s for s in fresh if s['therapist_id'] == selected.get('therapist_id')
            and utc_datetime(s['starts_at']) == utc_datetime(selected['starts_at'])
            and utc_datetime(s['ends_at']) == utc_datetime(selected['ends_at'])), None)
        if not valid:
            return 'That time is no longer available. Reply 2 to choose another date. Your booking has not changed.'
        from services.slot_reservation_service import SlotReservationService, SlotUnavailable
        try:
            async with SlotReservationService.hold(db, booking['id'], valid['starts_at'], valid['ends_at']):
                result = await db.bookings.update_one({'id': booking['id'], 'client_id': client['id'],
                    'status': 'pending', 'assignment_status': 'declined', 'reschedule_request_id': context['request_id'],
                    'starts_at': booking['starts_at']}, {'$set': {
                        'starts_at': utc_datetime(valid['starts_at']).isoformat(), 'ends_at': utc_datetime(valid['ends_at']).isoformat(),
                        'assignment_status': 'awaiting_assignment', 'reschedule_request_id': None,
                        'therapist_id': None, 'therapist_name': None, 'assigned_at': None, 'assigned_by': None,
                        'therapist_response_at': None, 'virtual_meeting_link': None, 'updated_at': now_iso(),
                    }})
                if not result.modified_count:
                    raise SlotUnavailable('This booking changed while you were choosing. Send MY BOOKINGS to check its status.')
        except SlotUnavailable as exc:
            return str(exc)
        await bot._save_session(db, sender, client['id'], 'menu', {})
        from services.audit_service import AuditService
        await AuditService.log_activity(db, action='booking_reschedule_requested', client_id=client['id'],
            booking_id=booking['id'], metadata={'previous_starts_at': booking['starts_at'], 'new_starts_at': valid['starts_at']})
        await NotificationOutbox.admin_alert(db, 'admin_booking_pending', f"{booking['id']}:{context['request_id']}",
            client['id'], booking_id=booking['id'], url='/admin/bookings')
        return 'Your new date and time have been requested. Status: Awaiting therapist confirmation. FCA will allocate a therapist and send confirmation after acceptance. Send MENU for more options.'
