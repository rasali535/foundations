import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from mongomock_motor import AsyncMongoMockClient

from models import BookingCreateRequest, CRMClient, Booking
from services.booking_service import BookingService
from services.slot_reservation_service import SlotReservationService, SlotUnavailable
from services.scheduling_service import SchedulingService
from services.setmore_service import SetmoreService


async def setup():
    db=AsyncMongoMockClient()['pending_holds']
    for index in range(2):
        client=CRMClient(id=f'client-{index}',client_number=f'FCA-{index}',first_name='Client',last_name=str(index),email=f'c{index}@example.com',phone=f'+2677123456{index}')
        await db.crm_clients.insert_one(client.model_dump())
    start=datetime.now(timezone.utc).replace(second=0,microsecond=0)+timedelta(days=2)
    return db, start


def request(client,start):
    return BookingCreateRequest(client_id=client,session_type='individual',session_mode='in_person',
        starts_at=start.isoformat(),ends_at=(start+timedelta(minutes=50)).isoformat(),source='whatsapp')


@pytest.mark.asyncio
async def test_pending_unassigned_blocks_other_client_and_partial_overlap():
    db,start=await setup()
    first,error=await BookingService.create_booking_request(db,request('client-0',start))
    assert not error and first.therapist_id is None
    for candidate in [start,start+timedelta(minutes=30)]:
        second,error=await BookingService.create_booking_request(db,request('client-1',candidate))
        assert second is None and 'reserved' in error
    adjacent,error=await BookingService.create_booking_request(db,request('client-1',start+timedelta(minutes=50)))
    assert not error and adjacent


@pytest.mark.asyncio
async def test_atomic_claims_close_simultaneous_submission_race(monkeypatch):
    db,start=await setup()
    # Force both writers past the availability read before either makes a claim.
    calls=0
    gate=asyncio.Event()
    original=SlotReservationService.busy
    async def simultaneous_read(db,exclude_booking_id=None):
        nonlocal calls
        result=await original(db,exclude_booking_id)
        calls+=1
        if calls==2:
            gate.set()
        await gate.wait()
        return result
    monkeypatch.setattr(SlotReservationService,'busy',simultaneous_read)
    results=await asyncio.gather(*(BookingService.create_booking_request(db,request(f'client-{i}',start)) for i in range(2)))
    assert sum(booking is not None for booking,error in results)==1
    assert sum(error is not None for booking,error in results)==1
    assert await db.bookings.count_documents({'status':'pending'})==1
    owners=await db.booking_slot_holds.distinct('booking_id')
    assert len(owners)==1


@pytest.mark.asyncio
async def test_both_availability_surfaces_hide_pending_and_owner_can_allocate(monkeypatch):
    db,start=await setup()
    pending,_=await BookingService.create_booking_request(db,request('client-0',start))
    monkeypatch.setattr(SchedulingService,'provider',staticmethod(lambda:'setmore'))
    monkeypatch.setattr(SetmoreService,'configured',staticmethod(lambda:True))
    async def slots(*args,**kwargs):
        return [{'starts_at':start.isoformat(),'ends_at':(start+timedelta(minutes=50)).isoformat(),'is_available':True},
                {'starts_at':(start+timedelta(hours=1)).isoformat(),'ends_at':(start+timedelta(hours=2)).isoformat(),'is_available':True}]
    monkeypatch.setattr(SetmoreService,'available_slots',slots)
    for therapist in ['therapist-1','therapist-2']:
        available=await SchedulingService.get_available_slots(db,therapist,start.date().isoformat(),1)
        assert available[0]['is_available'] is False and available[1]['is_available'] is True
    own=await SchedulingService.get_available_slots(db,'therapist-1',start.date().isoformat(),1,exclude_booking_id=pending.id)
    assert own[0]['is_available'] is True
    has_conflict,_=await BookingService.check_therapist_conflict(db,'therapist-1',pending.starts_at,pending.ends_at,exclude_booking_id=pending.id)
    assert not has_conflict


@pytest.mark.asyncio
async def test_legacy_cat_pending_and_cancellation_release():
    db,start=await setup()
    legacy=Booking(id='legacy',client_id='client-0',status='pending',therapist_id=None,session_type='individual',session_mode='virtual',
        starts_at=start.astimezone(timezone(timedelta(hours=2))).isoformat(),ends_at=(start+timedelta(minutes=50)).astimezone(timezone(timedelta(hours=2))).isoformat())
    await db.bookings.insert_one(legacy.model_dump())
    booking,error=await BookingService.create_booking_request(db,request('client-1',start))
    assert booking is None and error
    await db.bookings.update_one({'id':'legacy'},{'$set':{'status':'cancelled'}})
    booking,error=await BookingService.create_booking_request(db,request('client-1',start))
    assert booking and not error
    await db.bookings.update_one({'id':booking.id},{'$set':{'status':'cancelled'}})
    replacement,error=await BookingService.create_booking_request(db,request('client-0',start))
    assert replacement and not error


@pytest.mark.asyncio
async def test_failed_reschedule_retains_old_hold_and_rolls_back_new_claims():
    db,start=await setup()
    booking,_=await BookingService.create_booking_request(db,request('client-0',start))
    with pytest.raises(SlotUnavailable):
        async with SlotReservationService.hold(db,booking.id,start+timedelta(hours=2),start+timedelta(hours=3)):
            raise SlotUnavailable('Booking changed concurrently')
    holds=await db.booking_slot_holds.find({'booking_id':booking.id}).to_list(None)
    assert len(holds)==50
    assert all(datetime.fromisoformat(h['_id'])<start+timedelta(hours=1) for h in holds)
    async with SlotReservationService.hold(db,booking.id,start+timedelta(hours=2),start+timedelta(hours=3)):
        await db.bookings.update_one({'id':booking.id},{'$set':{'starts_at':(start+timedelta(hours=2)).isoformat(),'ends_at':(start+timedelta(hours=3)).isoformat()}})
    newholds=await db.booking_slot_holds.find({'booking_id':booking.id}).to_list(None)
    assert len(newholds)==60
    other,error=await BookingService.create_booking_request(db,request('client-1',start))
    assert other and not error


@pytest.mark.asyncio
async def test_whatsapp_assignment_lists_therapist_for_own_reserved_booking(monkeypatch):
    from types import SimpleNamespace
    from routers.meta_whatsapp_router import _available_therapists_for_booking
    from services.therapist_service import TherapistService
    db,start=await setup()
    pending,error=await BookingService.create_booking_request(db,request('client-0',start))
    assert not error
    monkeypatch.setattr(SchedulingService,'provider',staticmethod(lambda:'setmore'))
    monkeypatch.setattr(SetmoreService,'configured',staticmethod(lambda:True))
    monkeypatch.setattr(TherapistService,'list_therapists',AsyncMock(return_value=[SimpleNamespace(id='caroline',name='Caroline Sithole')]))
    async def slots(*args,**kwargs):
        return [{'starts_at':pending.starts_at,'ends_at':pending.ends_at,'is_available':True}]
    monkeypatch.setattr(SetmoreService,'available_slots',slots)
    listed=await _available_therapists_for_booking(db,pending.model_dump())
    assert listed == [{'id':'caroline','name':'Caroline Sithole'}]
    # The exception is confined to allocation of this booking: the public
    # gateway continues hiding its held interval from everyone else.
    public=await SchedulingService.get_available_slots(db,'caroline',start.date().isoformat(),1)
    assert public[0]['is_available'] is False
