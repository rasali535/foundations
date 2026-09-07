import logging
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from models import CRMIntakeSubmission, CRMClient, now_iso
from services.crm_service import CRMService
from services.audit_service import AuditService

class IntakeService:
    @staticmethod
    async def process_intake_submission(
        db: AsyncIOMotorDatabase,
        payload: Dict[str, Any],
        source: str = "website_intake"
    ) -> Dict[str, Any]:
        """
        Process an incoming intake submission:
        1. Extract client identity details
        2. Find or create CRM client
        3. Save intake record in crm_intake_submissions linked to client_id
        4. Log immutable audit entry
        """
        # Safety / Triage assessment
        safety = payload.get("safety_screen", {})
        if isinstance(safety, dict):
            is_high_risk = (
                safety.get("self_harm") == "Yes" or
                safety.get("harm_others") == "Yes" or
                safety.get("unsafe_environment") == "Yes" or
                safety.get("abuse_experienced") == "Yes"
            )
        else:
            is_high_risk = (
                payload.get("self_harm") == "Yes" or
                payload.get("harm_others") == "Yes" or
                payload.get("unsafe") == "Yes" or
                payload.get("abuse") == "Yes"
            )

        triage_level = "HIGH_PRIORITY_ESCALATION" if is_high_risk else "ROUTINE_COUNSELLING"

        # Client profile fields extraction
        client_data = {
            "full_name": payload.get("full_name") or payload.get("name"),
            "first_name": payload.get("first_name"),
            "last_name": payload.get("last_name"),
            "email": payload.get("email"),
            "phone": payload.get("phone"),
            "dob": payload.get("dob") or payload.get("date_of_birth"),
            "gender": payload.get("gender"),
            "location": payload.get("location"),
            "preferred_contact_method": payload.get("preferred_contact_method") or payload.get("contact_method") or "Phone call",
            "emergency_contact_name": payload.get("emergency_contact_name") or payload.get("emergency_name"),
            "emergency_contact_relationship": payload.get("emergency_contact_relationship") or payload.get("emergency_relationship"),
            "emergency_contact_phone": payload.get("emergency_contact_phone") or payload.get("emergency_phone")
        }

        # Find or create CRM client
        crm_client, is_new = await CRMService.find_or_create_client(db, client_data)

        # Store intake submission record
        intake_record = CRMIntakeSubmission(
            client_id=crm_client.id,
            client_number=crm_client.client_number,
            submission_data=payload,
            triage_level=triage_level,
            is_high_risk=is_high_risk,
            source=source,
            version="1.0",
            submitted_at=now_iso(),
            created_at=now_iso()
        )

        await db.crm_intake_submissions.insert_one(intake_record.model_dump())

        # Audit log
        await AuditService.log_activity(
            db,
            action="intake_received",
            client_id=crm_client.id,
            metadata={
                "intake_id": intake_record.id,
                "client_number": crm_client.client_number,
                "triage_level": triage_level,
                "is_new_client": is_new,
                "source": source
            }
        )

        return {
            "status": "intake_received",
            "intake_id": intake_record.id,
            "client_id": crm_client.id,
            "client_number": crm_client.client_number,
            "is_new_client": is_new,
            "triage_level": triage_level,
            "escalation_advisory": "If you are in immediate danger or distress, please dial 999 immediately or contact emergency services." if is_high_risk else "Our clinical team will review your submission and contact you to schedule your session.",
            "created_at": intake_record.created_at
        }

    @staticmethod
    async def get_client_intakes(db: AsyncIOMotorDatabase, client_id: str) -> List[CRMIntakeSubmission]:
        cursor = db.crm_intake_submissions.find({"client_id": client_id}, {"_id": 0}).sort("created_at", -1)
        docs = await cursor.to_list(100)
        return [CRMIntakeSubmission(**d) for d in docs]
