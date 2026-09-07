import logging
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from models import CRMActivityLog, now_iso

class AuditService:
    @staticmethod
    async def log_activity(
        db: AsyncIOMotorDatabase,
        action: str,
        actor_user_id: Optional[str] = None,
        actor_name: Optional[str] = None,
        client_id: Optional[str] = None,
        booking_id: Optional[str] = None,
        booking_batch_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CRMActivityLog:
        """
        Record an immutable activity log entry.
        Never stores confidential clinical material in audit metadata.
        """
        entry = CRMActivityLog(
            actor_user_id=actor_user_id,
            actor_name=actor_name,
            client_id=client_id,
            booking_id=booking_id,
            booking_batch_id=booking_batch_id,
            action=action,
            metadata=metadata or {},
            created_at=now_iso()
        )
        try:
            await db.crm_activity_log.insert_one(entry.model_dump())
        except Exception as e:
            logging.error(f"Failed to record audit activity '{action}': {e}")
        return entry
