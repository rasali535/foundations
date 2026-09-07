import logging
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from models import (
    Therapist, TherapistCreate, TherapistUpdate,
    TherapistBlock, TherapistBlockCreate, now_iso
)
from services.audit_service import AuditService

DEFAULT_THERAPISTS = [
    {
        "id": "therapist-caroline-sithole",
        "name": "Caroline Sithole (Lead Clinician)",
        "email": "caroline@academyfoundations.com",
        "phone": "+267 71 000 001",
        "active": True,
        "supports_in_person": True,
        "supports_virtual": False,  # Dedicated In-Person Therapist
        "specializations": ["In-Person Individual Therapy", "Couple Therapy", "Family Systems", "Trauma & EAP"],
        "working_days": [0, 1, 2, 3, 4],  # Mon-Fri
        "working_hours_start": "08:00",
        "working_hours_end": "17:00",
        "slot_duration_minutes": 60,
        "default_location": "FCA Central Clinic, Gaborone (Plot 54368)",
        "virtual_meeting_link_template": None
    },
    {
        "id": "therapist-kagiso-moeti",
        "name": "Kagiso Moeti (Virtual Specialist)",
        "email": "kagiso@academyfoundations.com",
        "phone": "+267 71 000 002",
        "active": True,
        "supports_in_person": False,  # Dedicated Virtual Therapist
        "supports_virtual": True,
        "specializations": ["Virtual 1-on-1 Counselling", "Virtual Couple Consultations", "Youth & Workplace Resilience"],
        "working_days": [0, 1, 2, 3, 4, 5],  # Mon-Sat
        "working_hours_start": "08:00",
        "working_hours_end": "18:00",
        "slot_duration_minutes": 60,
        "default_location": "Virtual Telehealth Room",
        "virtual_meeting_link_template": "https://meet.academyfoundations.com/room/fca-virtual"
    },
    {
        "id": "therapist-dr-thabo-kgosi",
        "name": "Dr. Thabo Kgosi (Senior Consultant)",
        "email": "thabo@academyfoundations.com",
        "phone": "+267 71 000 003",
        "active": True,
        "supports_in_person": True,
        "supports_virtual": True,
        "specializations": ["Executive Coaching", "Couple Therapy", "Stress & Burnout", "Organisational Health"],
        "working_days": [0, 1, 2, 3, 4],
        "working_hours_start": "09:00",
        "working_hours_end": "18:00",
        "slot_duration_minutes": 60,
        "default_location": "FCA Central Clinic, Gaborone (Plot 54368)",
        "virtual_meeting_link_template": "https://meet.academyfoundations.com/room/dr-thabo"
    }
]

class TherapistService:
    @staticmethod
    async def seed_defaults_if_empty(db: AsyncIOMotorDatabase):
        try:
            count = await db.therapists.count_documents({})
            if count == 0:
                for t in DEFAULT_THERAPISTS:
                    t_doc = Therapist(**t).model_dump()
                    await db.therapists.insert_one(t_doc)
                logging.info(f"Seeded {len(DEFAULT_THERAPISTS)} default therapists into database.")
        except Exception as e:
            logging.warning(f"Could not seed default therapists: {e}")

    @staticmethod
    async def list_therapists(
        db: AsyncIOMotorDatabase,
        active_only: bool = False,
        session_mode: Optional[str] = None
    ) -> List[Therapist]:
        await TherapistService.seed_defaults_if_empty(db)
        filter_dict: Dict[str, Any] = {}
        if active_only:
            filter_dict["active"] = True
        if session_mode == "in_person":
            filter_dict["supports_in_person"] = True
        elif session_mode == "virtual":
            filter_dict["supports_virtual"] = True

        cursor = db.therapists.find(filter_dict, {"_id": 0}).sort("name", 1)
        docs = await cursor.to_list(100)
        return [Therapist(**d) for d in docs]

    @staticmethod
    async def get_therapist_by_id(db: AsyncIOMotorDatabase, therapist_id: str) -> Optional[Therapist]:
        await TherapistService.seed_defaults_if_empty(db)
        doc = await db.therapists.find_one({"id": therapist_id}, {"_id": 0})
        return Therapist(**doc) if doc else None

    @staticmethod
    async def create_therapist(
        db: AsyncIOMotorDatabase,
        data: TherapistCreate,
        actor_id: Optional[str] = None,
        actor_name: Optional[str] = None
    ) -> Therapist:
        therapist = Therapist(
            name=data.name,
            email=str(data.email),
            phone=data.phone,
            active=data.active,
            supports_in_person=data.supports_in_person,
            supports_virtual=data.supports_virtual,
            specializations=data.specializations,
            working_days=data.working_days,
            working_hours_start=data.working_hours_start,
            working_hours_end=data.working_hours_end,
            slot_duration_minutes=data.slot_duration_minutes,
            default_location=data.default_location or "FCA Central Clinic, Gaborone",
            virtual_meeting_link_template=data.virtual_meeting_link_template or f"https://meet.academyfoundations.com/room/{data.name.lower().replace(' ', '-')}",
            created_at=now_iso(),
            updated_at=now_iso()
        )
        await db.therapists.insert_one(therapist.model_dump())
        await AuditService.log_activity(
            db,
            action="therapist_created",
            actor_user_id=actor_id,
            actor_name=actor_name,
            metadata={"therapist_id": therapist.id, "name": therapist.name}
        )
        return therapist

    @staticmethod
    async def update_therapist(
        db: AsyncIOMotorDatabase,
        therapist_id: str,
        update_data: TherapistUpdate,
        actor_id: Optional[str] = None,
        actor_name: Optional[str] = None
    ) -> Optional[Therapist]:
        data = {k: v for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None}
        if "email" in data:
            data["email"] = str(data["email"])
        data["updated_at"] = now_iso()
        
        res = await db.therapists.update_one({"id": therapist_id}, {"$set": data})
        if res.matched_count == 0:
            return None
            
        updated = await TherapistService.get_therapist_by_id(db, therapist_id)
        if updated:
            await AuditService.log_activity(
                db,
                action="therapist_updated",
                actor_user_id=actor_id,
                actor_name=actor_name,
                metadata={"therapist_id": therapist_id, "updated_fields": list(data.keys())}
            )
        return updated

    # ==================== Therapist Routing ====================
    @staticmethod
    async def validate_and_route_therapist(
        db: AsyncIOMotorDatabase,
        session_mode: str,
        therapist_id: Optional[str] = None
    ) -> Tuple[Therapist, Optional[str]]:
        """
        Validates whether requested therapist supports session_mode.
        If therapist_id is omitted, auto-routes to the first active matching therapist.
        Returns (Therapist, error_message)
        """
        await TherapistService.seed_defaults_if_empty(db)
        if therapist_id:
            therapist = await TherapistService.get_therapist_by_id(db, therapist_id)
            if not therapist:
                return None, f"Therapist '{therapist_id}' not found."
            if not therapist.active:
                return None, f"Therapist '{therapist.name}' is currently inactive."
            if session_mode == "in_person" and not therapist.supports_in_person:
                return None, f"Therapist '{therapist.name}' does not support In-person appointments."
            if session_mode == "virtual" and not therapist.supports_virtual:
                return None, f"Therapist '{therapist.name}' does not support Virtual appointments."
            return therapist, None

        # Auto-routing fallback
        matching_therapists = await TherapistService.list_therapists(db, active_only=True, session_mode=session_mode)
        if not matching_therapists:
            return None, f"No active therapists available for {session_mode} sessions."
        return matching_therapists[0], None

    # ==================== Therapist Blocks & Leave ====================
    @staticmethod
    async def create_block(
        db: AsyncIOMotorDatabase,
        data: TherapistBlockCreate,
        actor_id: Optional[str] = None
    ) -> TherapistBlock:
        block = TherapistBlock(
            therapist_id=data.therapist_id,
            type=data.type,
            starts_at=data.starts_at,
            ends_at=data.ends_at,
            reason=data.reason,
            created_by=actor_id,
            created_at=now_iso()
        )
        await db.therapist_blocks.insert_one(block.model_dump())
        return block

    @staticmethod
    async def list_blocks(
        db: AsyncIOMotorDatabase,
        therapist_id: Optional[str] = None
    ) -> List[TherapistBlock]:
        filter_dict = {}
        if therapist_id:
            filter_dict["therapist_id"] = therapist_id
        cursor = db.therapist_blocks.find(filter_dict, {"_id": 0}).sort("starts_at", 1)
        docs = await cursor.to_list(500)
        return [TherapistBlock(**d) for d in docs]

    @staticmethod
    async def delete_block(db: AsyncIOMotorDatabase, block_id: str) -> bool:
        res = await db.therapist_blocks.delete_one({"id": block_id})
        return res.deleted_count > 0

    # ==================== Availability Calculation Engine ====================
    @staticmethod
    async def get_available_slots(
        db: AsyncIOMotorDatabase,
        therapist_id: str,
        start_date_str: str,  # YYYY-MM-DD
        days_ahead: int = 14
    ) -> List[Dict[str, Any]]:
        """
        Calculates available booking slots for a therapist starting from start_date.
        Takes into account:
        1. Working days of week
        2. Daily working hours
        3. Leave / blocked slots
        4. Existing active bookings (confirmed, pending)
        """
        therapist = await TherapistService.get_therapist_by_id(db, therapist_id)
        if not therapist or not therapist.active:
            return []

        try:
            start_d = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except Exception:
            start_d = datetime.now(timezone.utc).date()

        end_d = start_d + timedelta(days=days_ahead)
        start_iso = datetime.combine(start_d, time.min, tzinfo=timezone.utc).isoformat()
        end_iso = datetime.combine(end_d, time.max, tzinfo=timezone.utc).isoformat()

        # Fetch active bookings in range
        booking_cursor = db.bookings.find({
            "therapist_id": therapist_id,
            "status": {"$in": ["confirmed", "pending"]},
            "starts_at": {"$lte": end_iso},
            "ends_at": {"$gte": start_iso}
        }, {"_id": 0})
        existing_bookings = await booking_cursor.to_list(500)

        # Fetch blocks in range
        block_cursor = db.therapist_blocks.find({
            "therapist_id": therapist_id,
            "starts_at": {"$lte": end_iso},
            "ends_at": {"$gte": start_iso}
        }, {"_id": 0})
        existing_blocks = await block_cursor.to_list(500)

        # Parse busy intervals
        busy_intervals: List[Tuple[datetime, datetime]] = []
        for b in existing_bookings:
            try:
                b_start = datetime.fromisoformat(b["starts_at"].replace("Z", "+00:00"))
                b_end = datetime.fromisoformat(b["ends_at"].replace("Z", "+00:00"))
                busy_intervals.append((b_start, b_end))
            except Exception:
                pass

        for blk in existing_blocks:
            try:
                blk_start = datetime.fromisoformat(blk["starts_at"].replace("Z", "+00:00"))
                blk_end = datetime.fromisoformat(blk["ends_at"].replace("Z", "+00:00"))
                busy_intervals.append((blk_start, blk_end))
            except Exception:
                pass

        # Parse working hours
        try:
            w_start_h, w_start_m = map(int, therapist.working_hours_start.split(":"))
            w_end_h, w_end_m = map(int, therapist.working_hours_end.split(":"))
        except Exception:
            w_start_h, w_start_m = 8, 0
            w_end_h, w_end_m = 17, 0

        slot_mins = therapist.slot_duration_minutes or 60
        slots: List[Dict[str, Any]] = []

        curr_date = start_d
        while curr_date <= end_d:
            weekday = curr_date.weekday()  # 0=Monday, 6=Sunday
            if weekday in therapist.working_days:
                day_start = datetime.combine(curr_date, time(w_start_h, w_start_m), tzinfo=timezone.utc)
                day_end = datetime.combine(curr_date, time(w_end_h, w_end_m), tzinfo=timezone.utc)

                slot_cursor = day_start
                while slot_cursor + timedelta(minutes=slot_mins) <= day_end:
                    slot_start = slot_cursor
                    slot_end = slot_cursor + timedelta(minutes=slot_mins)

                    # Check collision with busy intervals
                    is_available = True
                    for (b_start, b_end) in busy_intervals:
                        if max(slot_start, b_start) < min(slot_end, b_end):
                            is_available = False
                            break

                    slots.append({
                        "therapist_id": therapist.id,
                        "therapist_name": therapist.name,
                        "starts_at": slot_start.isoformat(),
                        "ends_at": slot_end.isoformat(),
                        "date": curr_date.isoformat(),
                        "time_display": f"{slot_start.strftime('%H:%M')} - {slot_end.strftime('%H:%M')}",
                        "is_available": is_available
                    })
                    slot_cursor += timedelta(minutes=slot_mins)

            curr_date += timedelta(days=1)

        return slots
