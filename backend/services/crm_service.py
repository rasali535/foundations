import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from models import (
    CRMClient, CRMClientCreate, CRMClientUpdate,
    CRMNote, CRMNoteCreate, CRMNoteUpdate, now_iso
)
from services.audit_service import AuditService

def normalize_email(email: Optional[str]) -> str:
    if not email:
        return ""
    return str(email).strip().lower()

def normalize_phone(phone: Optional[str]) -> str:
    if not phone:
        return ""
    # Strip whitespace, spaces, parentheses, dashes
    cleaned = re.sub(r'[\s\(\)\-\.]+', '', str(phone).strip())
    return cleaned

class CRMService:
    @staticmethod
    async def get_next_client_number(db: AsyncIOMotorDatabase) -> str:
        """
        Generate atomic sequence number in format FCA-000001
        """
        try:
            counter = await db.system_counters.find_one_and_update(
                {"_id": "client_number_seq"},
                {"$inc": {"seq": 1}},
                upsert=True,
                return_document=True
            )
            seq = counter.get("seq", 1) if counter else 1
            return f"FCA-{seq:06d}"
        except Exception:
            # Fallback based on total count
            count = await db.crm_clients.count_documents({})
            return f"FCA-{count + 1:06d}"

    @staticmethod
    async def find_or_create_client(
        db: AsyncIOMotorDatabase,
        client_data: Dict[str, Any],
        actor_id: Optional[str] = None,
        actor_name: Optional[str] = None
    ) -> Tuple[CRMClient, bool]:
        """
        Find existing client following the matching hierarchy:
        1. Explicit client_id
        2. Exact normalized email
        3. Exact normalized phone
        4. Otherwise create new client
        Returns (CRMClient, is_new: bool)
        """
        client_id = client_data.get("id") or client_data.get("client_id")
        email = normalize_email(client_data.get("email"))
        phone = normalize_phone(client_data.get("phone"))

        # 1. Match by ID
        if client_id:
            doc = await db.crm_clients.find_one({"id": client_id}, {"_id": 0})
            if doc:
                return CRMClient(**doc), False

        # 2. Match by exact normalized Email
        if email:
            doc = await db.crm_clients.find_one({"email": email}, {"_id": 0})
            if doc:
                # Update phone/details if provided
                update_fields = {}
                if phone and not doc.get("phone"):
                    update_fields["phone"] = phone
                if update_fields:
                    update_fields["updated_at"] = now_iso()
                    await db.crm_clients.update_one({"id": doc["id"]}, {"$set": update_fields})
                    doc.update(update_fields)
                return CRMClient(**doc), False

        # 3. Match by exact normalized Phone
        if phone:
            doc = await db.crm_clients.find_one({"phone": phone}, {"_id": 0})
            if doc:
                update_fields = {}
                if email and not doc.get("email"):
                    update_fields["email"] = email
                if update_fields:
                    update_fields["updated_at"] = now_iso()
                    await db.crm_clients.update_one({"id": doc["id"]}, {"$set": update_fields})
                    doc.update(update_fields)
                return CRMClient(**doc), False

        # 4. Create new client
        first_name = (client_data.get("first_name") or "").strip()
        last_name = (client_data.get("last_name") or "").strip()
        
        # If full_name was provided instead
        if not first_name and client_data.get("full_name"):
            parts = client_data["full_name"].strip().split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

        client_number = await CRMService.get_next_client_number(db)
        new_client = CRMClient(
            client_number=client_number,
            first_name=first_name or "Client",
            last_name=last_name or "",
            email=email,
            phone=phone,
            date_of_birth=client_data.get("date_of_birth") or client_data.get("dob"),
            gender=client_data.get("gender"),
            location=client_data.get("location"),
            preferred_contact_method=client_data.get("preferred_contact_method") or "Phone call",
            emergency_contact_name=client_data.get("emergency_contact_name"),
            emergency_contact_relationship=client_data.get("emergency_contact_relationship"),
            emergency_contact_phone=client_data.get("emergency_contact_phone"),
            organisation_id=client_data.get("organisation_id"),
            organisation_name=client_data.get("organisation_name"),
            status="active",
            tags=client_data.get("tags", []),
            created_at=now_iso(),
            updated_at=now_iso()
        )

        await db.crm_clients.insert_one(new_client.model_dump())
        await AuditService.log_activity(
            db,
            action="client_created",
            actor_user_id=actor_id,
            actor_name=actor_name,
            client_id=new_client.id,
            metadata={"client_number": new_client.client_number, "email": new_client.email}
        )
        return new_client, True

    @staticmethod
    async def get_client_by_id(db: AsyncIOMotorDatabase, client_id: str) -> Optional[CRMClient]:
        doc = await db.crm_clients.find_one({"id": client_id}, {"_id": 0})
        return CRMClient(**doc) if doc else None

    @staticmethod
    async def update_client(
        db: AsyncIOMotorDatabase,
        client_id: str,
        update_data: CRMClientUpdate,
        actor_id: Optional[str] = None,
        actor_name: Optional[str] = None
    ) -> Optional[CRMClient]:
        data = {k: v for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None}
        if "email" in data:
            data["email"] = normalize_email(data["email"])
        if "phone" in data:
            data["phone"] = normalize_phone(data["phone"])
        
        data["updated_at"] = now_iso()
        res = await db.crm_clients.update_one({"id": client_id}, {"$set": data})
        if res.matched_count == 0:
            return None

        updated_client = await CRMService.get_client_by_id(db, client_id)
        if updated_client:
            await AuditService.log_activity(
                db,
                action="client_updated",
                actor_user_id=actor_id,
                actor_name=actor_name,
                client_id=client_id,
                metadata={"updated_fields": list(data.keys())}
            )
        return updated_client

    @staticmethod
    async def search_clients(
        db: AsyncIOMotorDatabase,
        query: str = "",
        status: Optional[str] = None,
        organisation_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[CRMClient], int]:
        filter_dict: Dict[str, Any] = {}
        if status:
            filter_dict["status"] = status
        if organisation_id:
            filter_dict["organisation_id"] = organisation_id

        if query:
            clean_q = query.strip()
            regex = {"$regex": clean_q, "$options": "i"}
            filter_dict["$or"] = [
                {"first_name": regex},
                {"last_name": regex},
                {"email": regex},
                {"phone": regex},
                {"client_number": regex},
                {"organisation_name": regex}
            ]

        total = await db.crm_clients.count_documents(filter_dict)
        cursor = db.crm_clients.find(filter_dict, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(limit)
        clients = [CRMClient(**d) for d in docs]
        return clients, total

    # ==================== CRM Administrative Notes ====================
    @staticmethod
    async def create_note(
        db: AsyncIOMotorDatabase,
        client_id: str,
        note_data: CRMNoteCreate,
        author_id: str,
        author_name: str
    ) -> CRMNote:
        note = CRMNote(
            client_id=client_id,
            author_user_id=author_id,
            author_name=author_name,
            content=note_data.content,
            is_pinned=note_data.is_pinned,
            created_at=now_iso(),
            updated_at=now_iso()
        )
        await db.crm_notes.insert_one(note.model_dump())
        await AuditService.log_activity(
            db,
            action="note_created",
            actor_user_id=author_id,
            actor_name=author_name,
            client_id=client_id,
            metadata={"note_id": note.id, "is_pinned": note.is_pinned}
        )
        return note

    @staticmethod
    async def update_note(
        db: AsyncIOMotorDatabase,
        note_id: str,
        update_data: CRMNoteUpdate,
        actor_id: str,
        actor_name: str
    ) -> Optional[CRMNote]:
        data = {k: v for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None}
        data["updated_at"] = now_iso()
        
        note_doc = await db.crm_notes.find_one({"id": note_id}, {"_id": 0})
        if not note_doc:
            return None

        await db.crm_notes.update_one({"id": note_id}, {"$set": data})
        updated = await db.crm_notes.find_one({"id": note_id}, {"_id": 0})
        await AuditService.log_activity(
            db,
            action="note_updated",
            actor_user_id=actor_id,
            actor_name=actor_name,
            client_id=note_doc.get("client_id"),
            metadata={"note_id": note_id, "updated_fields": list(data.keys())}
        )
        return CRMNote(**updated) if updated else None

    @staticmethod
    async def delete_note(
        db: AsyncIOMotorDatabase,
        note_id: str,
        actor_id: str,
        actor_name: str
    ) -> bool:
        note_doc = await db.crm_notes.find_one({"id": note_id}, {"_id": 0})
        if not note_doc:
            return False

        res = await db.crm_notes.delete_one({"id": note_id})
        if res.deleted_count > 0:
            await AuditService.log_activity(
                db,
                action="note_deleted",
                actor_user_id=actor_id,
                actor_name=actor_name,
                client_id=note_doc.get("client_id"),
                metadata={"note_id": note_id}
            )
            return True
        return False

    @staticmethod
    async def list_notes(db: AsyncIOMotorDatabase, client_id: str) -> List[CRMNote]:
        cursor = db.crm_notes.find({"client_id": client_id}, {"_id": 0}).sort([("is_pinned", -1), ("created_at", -1)])
        docs = await cursor.to_list(500)
        return [CRMNote(**d) for d in docs]
