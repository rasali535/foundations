"""Global pending-slot holds until FCA allocates and confirms a therapist."""
from contextlib import asynccontextmanager
from datetime import timedelta
from pymongo.errors import DuplicateKeyError

from models import now_iso
from services.notification_outbox import utc_datetime


class SlotUnavailable(ValueError):
    pass


class SlotReservationService:
    @staticmethod
    def keys(start, end):
        start, end = utc_datetime(start), utc_datetime(end)
        if end <= start or end - start > timedelta(hours=24):
            raise SlotUnavailable('Appointment duration must be positive and at most 24 hours.')
        minute = start.replace(second=0, microsecond=0)
        keys = []
        while minute < end:
            keys.append(minute.isoformat())
            minute += timedelta(minutes=1)
        return keys

    @staticmethod
    def overlaps(start, end, row):
        return utc_datetime(start) < utc_datetime(row['ends_at']) and utc_datetime(end) > utc_datetime(row['starts_at'])

    @staticmethod
    async def busy(db, exclude_booking_id=None):
        bookings = await db.bookings.find({'status':'pending'}, {'_id':0}).to_list(None)
        intervals = [b for b in bookings if b['id'] != exclude_booking_id]
        holds = await db.booking_slot_holds.find({'booking_id': {'$ne':exclude_booking_id}}, {'_id':1,'booking_id':1,'provisional':1}).to_list(None)
        owners = {b['id']:b for b in bookings}
        missing_ids = list({h['booking_id'] for h in holds} - owners.keys())
        # A confirmed/cancelled/completed booking releases its pending capacity.
        other = await db.bookings.find({'id':{'$in':missing_ids}}, {'_id':0,'id':1,'status':1}).to_list(None) if missing_ids else []
        statuses = {b['id']:b['status'] for b in other}
        for h in holds:
            owner = owners.get(h['booking_id'])
            if h['booking_id'] in statuses:
                continue
            minute = utc_datetime(h['_id'])
            row = {'starts_at':minute.isoformat(), 'ends_at':(minute+timedelta(minutes=1)).isoformat()}
            # In-flight claims and claims whose owner has not yet been inserted
            # remain reserved; never expire a hold while a writer may be alive.
            if not owner or h.get('provisional') or SlotReservationService.overlaps(row['starts_at'],row['ends_at'],owner):
                intervals.append(row)
        return intervals

    @staticmethod
    async def release(db, booking_id):
        await db.booking_slot_holds.delete_many({"booking_id": booking_id})

    @staticmethod
    async def filter_slots(db, slots, exclude_booking_id=None):
        busy = await SlotReservationService.busy(db, exclude_booking_id)
        for slot in slots:
            if slot.get('is_available') and any(SlotReservationService.overlaps(slot['starts_at'],slot['ends_at'],b) for b in busy):
                slot['is_available'] = False
        return slots

    @staticmethod
    @asynccontextmanager
    async def hold(db, booking_id, starts_at, ends_at):
        keys = SlotReservationService.keys(starts_at, ends_at)
        inserted = []
        try:
            busy = await SlotReservationService.busy(db, booking_id)
            if any(SlotReservationService.overlaps(starts_at,ends_at,b) for b in busy):
                raise SlotUnavailable('This time is reserved by another booking request. Please choose another time.')
            for key in keys:
                for attempt in range(2):
                    try:
                        await db.booking_slot_holds.insert_one({'_id':key,'booking_id':booking_id,
                            'provisional':True,'created_at':now_iso()})
                        inserted.append(key)
                        break
                    except DuplicateKeyError:
                        current = await db.booking_slot_holds.find_one({'_id':key})
                        if current and current['booking_id']==booking_id:
                            break
                        owner = await db.bookings.find_one({'id':current['booking_id']}) if current else None
                        minute = utc_datetime(key)
                        stale = owner and (owner.get('status')!='pending' or (not current.get('provisional') and
                            not SlotReservationService.overlaps(key,(minute+timedelta(minutes=1)).isoformat(),owner)))
                        if stale and attempt==0:
                            await db.booking_slot_holds.delete_one({'_id':key,'booking_id':current['booking_id']})
                            continue
                        raise SlotUnavailable('This time was just reserved by another client. Please choose another time.')
            yield
        except BaseException:
            # Only release new claims from this attempt, preserving the old slot
            # during a failed reschedule. Crashed workers fail closed.
            await db.booking_slot_holds.delete_many({'_id':{'$in':inserted},'booking_id':booking_id})
            raise
        else:
            await db.booking_slot_holds.update_many({'booking_id':booking_id,'_id':{'$in':keys}}, {'$set':{'provisional':False}})
            await db.booking_slot_holds.delete_many({'booking_id':booking_id,'_id':{'$nin':keys}})
