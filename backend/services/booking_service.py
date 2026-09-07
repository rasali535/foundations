import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from models import (
    Booking, BookingBatch, BookingParticipant,
    BookingCreateRequest, MultiBookingCreateRequest,
    BookingRescheduleRequest, BookingStatusUpdateRequest,
    CRMClient, now_iso
)
from services.crm_service import CRMService
from services.therapist_service import TherapistService
from services.notification_service import NotificationService
from services.audit_service import AuditService

def parse_iso(dt_str: str) -> datetime:
    clean = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(clean)

class BookingService:
    # ==================== Conflict / Double-Booking Validator ====================
    @staticmethod
    async def check_therapist_conflict(
        db: AsyncIOMotorDatabase,
        therapist_id: str,
        starts_at_str: str,
        ends_at_str: str,
        exclude_booking_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates whether a therapist is available for the given time slot.
        Returns (has_conflict: bool, conflict_reason: Optional[str])
        """
        try:
            req_start = parse_iso(starts_at_str)
            req_end = parse_iso(ends_at_str)
        except Exception as e:
            return True, f"Invalid date/time format: {e}"

        if req_end <= req_start:
            return True, "Appointment end time must be after start time."

        # 1. Check existing active bookings
        query = {
            "therapist_id": therapist_id,
            "status": {"$in": ["confirmed", "pending"]},
            "starts_at": {"$lt": req_end.isoformat()},
            "ends_at": {"$gt": req_start.isoformat()}
        }
        if exclude_booking_id:
            query["id"] = {"$ne": exclude_booking_id}

        existing = await db.bookings.find_one(query, {"_id": 0})
        if existing:
            return True, f"Therapist already has an active appointment scheduled from {existing.get('starts_at')} to {existing.get('ends_at')}."

        # 2. Check therapist blocks / leave
        block_query = {
            "therapist_id": therapist_id,
            "starts_at": {"$lt": req_end.isoformat()},
            "ends_at": {"$gt": req_start.isoformat()}
        }
        existing_block = await db.therapist_blocks.find_one(block_query, {"_id": 0})
        if existing_block:
            reason = existing_block.get("reason") or "Unavailable / On Leave"
            return True, f"Therapist is blocked during this time ({reason})."

        return False, None

    # ==================== Single Booking Creation ====================
    @staticmethod
    async def create_booking(
        db: AsyncIOMotorDatabase,
        request: BookingCreateRequest,
        actor_id: Optional[str] = None,
        actor_name: Optional[str] = None
    ) -> Tuple[Optional[Booking], Optional[str]]:
        """
        Creates a single appointment with validation, conflict protection, and notifications.
        """
        # 1. Resolve or Create CRM Client
        client = None
        if request.client_id:
            client = await CRMService.get_client_by_id(db, request.client_id)
        if not client:
            if not request.client_first_name or not request.client_email:
                return None, "Client information (ID or first_name + email) is required."
            client_dict = {
                "first_name": request.client_first_name,
                "last_name": request.client_last_name or "",
                "email": request.client_email,
                "phone": request.client_phone or "",
            }
            client, _ = await CRMService.find_or_create_client(db, client_dict, actor_id=actor_id, actor_name=actor_name)

        # 2. Validate Session Type and Session Mode
        valid_types = ["individual", "couple", "family"]
        if request.session_type.lower() not in valid_types:
            return None, f"Invalid session_type '{request.session_type}'. Must be one of {valid_types}."

        valid_modes = ["in_person", "virtual"]
        if request.session_mode.lower() not in valid_modes:
            return None, f"Invalid session_mode '{request.session_mode}'. Must be one of {valid_modes}."

        session_type = request.session_type.lower()
        session_mode = request.session_mode.lower()

        # 3. Route & Validate Therapist
        therapist, err = await TherapistService.validate_and_route_therapist(
            db, session_mode=session_mode, therapist_id=request.therapist_id
        )
        if err or not therapist:
            return None, err or "Failed to assign a compatible therapist."

        # 4. Resolve Starts/Ends At
        try:
            start_dt = parse_iso(request.starts_at)
            if request.ends_at:
                end_dt = parse_iso(request.ends_at)
            else:
                slot_duration = therapist.slot_duration_minutes or 60
                end_dt = start_dt + timedelta(minutes=slot_duration)
        except Exception as e:
            return None, f"Invalid start/end timestamps: {e}"

        starts_at_iso = start_dt.isoformat()
        ends_at_iso = end_dt.isoformat()

        # 5. Check Double-Booking Conflict
        has_conflict, conflict_msg = await BookingService.check_therapist_conflict(
            db, therapist.id, starts_at_iso, ends_at_iso
        )
        if has_conflict:
            return None, conflict_msg

        # 6. Build Location & Meeting Link
        location = request.location or (therapist.default_location if session_mode == "in_person" else None)
        virtual_link = request.virtual_meeting_link or (therapist.virtual_meeting_link_template if session_mode == "virtual" else None)

        # 7. Build Participants
        participants_list: List[BookingParticipant] = []
        # Primary client participant
        primary_part = BookingParticipant(
            client_id=client.id,
            name=f"{client.first_name} {client.last_name}".strip(),
            email=client.email,
            phone=client.phone,
            participant_role="primary_client",
            created_at=now_iso()
        )
        participants_list.append(primary_part)

        # Additional participants for Couple or Family
        for p in request.participants:
            part_obj = BookingParticipant(
                name=p.get("name", "Participant"),
                email=p.get("email"),
                phone=p.get("phone"),
                participant_role=p.get("participant_role", "partner" if session_type == "couple" else "family_member"),
                created_at=now_iso()
            )
            participants_list.append(part_obj)

        # 8. Create Booking Record
        booking = Booking(
            client_id=client.id,
            client_number=client.client_number,
            client_name=f"{client.first_name} {client.last_name}".strip(),
            client_email=client.email,
            client_phone=client.phone,
            therapist_id=therapist.id,
            therapist_name=therapist.name,
            session_type=session_type,
            session_mode=session_mode,
            starts_at=starts_at_iso,
            ends_at=ends_at_iso,
            status="confirmed",
            location=location,
            virtual_meeting_link=virtual_link,
            participants=participants_list,
            notes=request.notes,
            created_at=now_iso(),
            updated_at=now_iso()
        )

        for p in booking.participants:
            p.booking_id = booking.id

        await db.bookings.insert_one(booking.model_dump())

        # 9. Audit Log
        await AuditService.log_activity(
            db,
            action="booking_created",
            actor_user_id=actor_id,
            actor_name=actor_name,
            client_id=client.id,
            booking_id=booking.id,
            metadata={
                "session_type": session_type,
                "session_mode": session_mode,
                "therapist_id": therapist.id,
                "therapist_name": therapist.name,
                "starts_at": starts_at_iso,
                "source": request.source
            }
        )

        # 10. Notifications
        if request.send_notifications:
            try:
                await NotificationService.send_booking_email(db, client, [booking])
                await NotificationService.send_booking_whatsapp(db, client, [booking])
            except Exception as e:
                logging.warning(f"Failed to dispatch booking notification: {e}")

        return booking, None

    # ==================== Multi-Booking / Batch Creation ====================
    @staticmethod
    async def create_multi_booking(
        db: AsyncIOMotorDatabase,
        request: MultiBookingCreateRequest,
        actor_id: Optional[str] = None,
        actor_name: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Creates multiple bookings in one batch (e.g. 4 monthly sessions).
        Atomically validates all slots first. Rejects if any slot is conflicted.
        """
        if not request.slots or len(request.slots) == 0:
            return None, "At least one slot must be provided for multi-booking."

        # 1. Resolve Client
        client = None
        if request.client_id:
            client = await CRMService.get_client_by_id(db, request.client_id)
        if not client:
            if not request.client_first_name or not request.client_email:
                return None, "Client information is required for multi-booking."
            client_dict = {
                "first_name": request.client_first_name,
                "last_name": request.client_last_name or "",
                "email": request.client_email,
                "phone": request.client_phone or "",
            }
            client, _ = await CRMService.find_or_create_client(db, client_dict, actor_id=actor_id, actor_name=actor_name)

        session_type = request.session_type.lower()
        session_mode = request.session_mode.lower()

        # 2. Route & Validate Therapist
        therapist, err = await TherapistService.validate_and_route_therapist(
            db, session_mode=session_mode, therapist_id=request.therapist_id
        )
        if err or not therapist:
            return None, err or "Failed to assign a compatible therapist."

        # 3. Pre-validate All Slots for Conflicts
        slot_duration = therapist.slot_duration_minutes or 60
        validated_slots: List[Tuple[str, str, Optional[str]]] = []

        for idx, s in enumerate(request.slots, 1):
            try:
                s_dt = parse_iso(s.starts_at)
                e_dt = parse_iso(s.ends_at) if s.ends_at else (s_dt + timedelta(minutes=slot_duration))
            except Exception as e:
                return None, f"Slot #{idx} has invalid timestamp: {e}"

            s_iso = s_dt.isoformat()
            e_iso = e_dt.isoformat()

            has_conflict, conflict_msg = await BookingService.check_therapist_conflict(
                db, therapist.id, s_iso, e_iso
            )
            if has_conflict:
                return None, f"Slot #{idx} ({s.starts_at[:10]} {s.starts_at[11:16]} UTC) cannot be booked: {conflict_msg}"

            validated_slots.append((s_iso, e_iso, s.notes))

        # 4. Create Booking Batch Record
        batch = BookingBatch(
            client_id=client.id,
            client_number=client.client_number,
            source=request.source,
            created_by=actor_id,
            total_slots=len(validated_slots),
            notes=request.notes,
            created_at=now_iso()
        )
        await db.booking_batches.insert_one(batch.model_dump())

        # 5. Create Individual Independent Booking Records
        created_bookings: List[Booking] = []
        location = request.location or (therapist.default_location if session_mode == "in_person" else None)
        virtual_link = request.virtual_meeting_link or (therapist.virtual_meeting_link_template if session_mode == "virtual" else None)

        for (s_iso, e_iso, slot_note) in validated_slots:
            participants_list: List[BookingParticipant] = []
            primary_part = BookingParticipant(
                client_id=client.id,
                name=f"{client.first_name} {client.last_name}".strip(),
                email=client.email,
                phone=client.phone,
                participant_role="primary_client",
                created_at=now_iso()
            )
            participants_list.append(primary_part)

            for p in request.participants:
                part_obj = BookingParticipant(
                    name=p.get("name", "Participant"),
                    email=p.get("email"),
                    phone=p.get("phone"),
                    participant_role=p.get("participant_role", "partner" if session_type == "couple" else "family_member"),
                    created_at=now_iso()
                )
                participants_list.append(part_obj)

            booking = Booking(
                booking_batch_id=batch.id,
                client_id=client.id,
                client_number=client.client_number,
                client_name=f"{client.first_name} {client.last_name}".strip(),
                client_email=client.email,
                client_phone=client.phone,
                therapist_id=therapist.id,
                therapist_name=therapist.name,
                session_type=session_type,
                session_mode=session_mode,
                starts_at=s_iso,
                ends_at=e_iso,
                status="confirmed",
                location=location,
                virtual_meeting_link=virtual_link,
                participants=participants_list,
                notes=slot_note or request.notes,
                created_at=now_iso(),
                updated_at=now_iso()
            )

            for p in booking.participants:
                p.booking_id = booking.id

            await db.bookings.insert_one(booking.model_dump())
            created_bookings.append(booking)

            await AuditService.log_activity(
                db,
                action="booking_created",
                actor_user_id=actor_id,
                actor_name=actor_name,
                client_id=client.id,
                booking_id=booking.id,
                booking_batch_id=batch.id,
                metadata={
                    "batch_id": batch.id,
                    "session_type": session_type,
                    "session_mode": session_mode,
                    "starts_at": s_iso
                }
            )

        # 6. Dispatch Consolidated Notification
        if request.send_notifications:
            try:
                await NotificationService.send_booking_email(db, client, created_bookings, booking_batch_id=batch.id)
                await NotificationService.send_booking_whatsapp(db, client, created_bookings, booking_batch_id=batch.id)
            except Exception as e:
                logging.warning(f"Failed to dispatch multi-booking notification: {e}")

        return {
            "batch_id": batch.id,
            "total_created": len(created_bookings),
            "bookings": created_bookings,
            "client_id": client.id,
            "client_number": client.client_number
        }, None

    # ==================== Lifecycle: Reschedule, Status Update, Query ====================
    @staticmethod
    async def reschedule_booking(
        db: AsyncIOMotorDatabase,
        booking_id: str,
        request: BookingRescheduleRequest,
        actor_id: Optional[str] = None,
        actor_name: Optional[str] = None
    ) -> Tuple[Optional[Booking], Optional[str]]:
        booking_doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
        if not booking_doc:
            return None, "Booking not found."

        current_booking = Booking(**booking_doc)
        therapist_id = request.therapist_id or current_booking.therapist_id
        therapist = await TherapistService.get_therapist_by_id(db, therapist_id)
        if not therapist:
            return None, "Therapist not found."

        try:
            new_start_dt = parse_iso(request.new_starts_at)
            if request.new_ends_at:
                new_end_dt = parse_iso(request.new_ends_at)
            else:
                slot_duration = therapist.slot_duration_minutes or 60
                new_end_dt = new_start_dt + timedelta(minutes=slot_duration)
        except Exception as e:
            return None, f"Invalid reschedule timestamp: {e}"

        new_starts_at_iso = new_start_dt.isoformat()
        new_ends_at_iso = new_end_dt.isoformat()

        # Check Conflict
        has_conflict, conflict_msg = await BookingService.check_therapist_conflict(
            db, therapist.id, new_starts_at_iso, new_ends_at_iso, exclude_booking_id=booking_id
        )
        if has_conflict:
            return None, f"Cannot reschedule to requested time: {conflict_msg}"

        # Update Booking
        update_fields = {
            "starts_at": new_starts_at_iso,
            "ends_at": new_ends_at_iso,
            "therapist_id": therapist.id,
            "therapist_name": therapist.name,
            "status": "confirmed",
            "updated_at": now_iso()
        }
        if request.reason:
            update_fields["notes"] = f"Rescheduled: {request.reason}. (Previous: {current_booking.starts_at})"

        await db.bookings.update_one({"id": booking_id}, {"$set": update_fields})
        updated_doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
        updated_booking = Booking(**updated_doc)

        # Audit Log
        await AuditService.log_activity(
            db,
            action="booking_rescheduled",
            actor_user_id=actor_id,
            actor_name=actor_name,
            client_id=updated_booking.client_id,
            booking_id=booking_id,
            metadata={
                "previous_starts_at": current_booking.starts_at,
                "new_starts_at": new_starts_at_iso,
                "reason": request.reason
            }
        )

        # Dispatch Reschedule Notification
        if request.send_notifications:
            client = await CRMService.get_client_by_id(db, updated_booking.client_id)
            if client:
                try:
                    await NotificationService.send_booking_email(db, client, [updated_booking])
                    await NotificationService.send_booking_whatsapp(db, client, [updated_booking])
                except Exception as e:
                    logging.warning(f"Notification error on reschedule: {e}")

        return updated_booking, None

    @staticmethod
    async def update_booking_status(
        db: AsyncIOMotorDatabase,
        booking_id: str,
        request: BookingStatusUpdateRequest,
        actor_id: Optional[str] = None,
        actor_name: Optional[str] = None
    ) -> Tuple[Optional[Booking], Optional[str]]:
        booking_doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
        if not booking_doc:
            return None, "Booking not found."

        valid_statuses = ["pending", "confirmed", "completed", "cancelled", "no_show"]
        if request.status not in valid_statuses:
            return None, f"Invalid status '{request.status}'. Must be one of {valid_statuses}."

        update_fields = {
            "status": request.status,
            "updated_at": now_iso()
        }
        if request.cancellation_reason:
            update_fields["cancellation_reason"] = request.cancellation_reason
        if request.notes:
            update_fields["notes"] = request.notes

        await db.bookings.update_one({"id": booking_id}, {"$set": update_fields})
        updated_doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
        updated_booking = Booking(**updated_doc)

        action_name = f"booking_{request.status}"
        await AuditService.log_activity(
            db,
            action=action_name,
            actor_user_id=actor_id,
            actor_name=actor_name,
            client_id=updated_booking.client_id,
            booking_id=booking_id,
            metadata={
                "new_status": request.status,
                "cancellation_reason": request.cancellation_reason
            }
        )

        return updated_booking, None

    @staticmethod
    async def list_bookings(
        db: AsyncIOMotorDatabase,
        client_id: Optional[str] = None,
        therapist_id: Optional[str] = None,
        status: Optional[str] = None,
        session_type: Optional[str] = None,
        session_mode: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Booking], int]:
        filter_dict: Dict[str, Any] = {}
        if client_id:
            filter_dict["client_id"] = client_id
        if therapist_id:
            filter_dict["therapist_id"] = therapist_id
        if status:
            filter_dict["status"] = status
        if session_type:
            filter_dict["session_type"] = session_type
        if session_mode:
            filter_dict["session_mode"] = session_mode
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            filter_dict["starts_at"] = date_filter

        total = await db.bookings.count_documents(filter_dict)
        cursor = db.bookings.find(filter_dict, {"_id": 0}).sort("starts_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(limit)
        return [Booking(**d) for d in docs], total
