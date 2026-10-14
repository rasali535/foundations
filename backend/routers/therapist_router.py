from fastapi import APIRouter, HTTPException, Depends, Request, status, Query
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from models import (
    TherapistCreate, TherapistUpdate,
    TherapistBlock, TherapistBlockCreate, now_iso
)
from services.therapist_service import TherapistService, TherapistRecord, DEFAULT_THERAPISTS
from services.audit_service import AuditService

therapist_router = APIRouter(prefix="/therapists", tags=["Therapists"])


class TherapistNotificationSettingsUpdate(BaseModel):
    whatsapp_phone: Optional[str] = None
    whatsapp_notifications_enabled: Optional[bool] = None


def get_db(request: Request):
    return request.app.state.db


def get_current_user(request: Request) -> Dict[str, Any]:
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return {"user_id": user_id, "role": role, "name": request.session.get("name", user_id)}


def require_admin(request: Request):
    user = get_current_user(request)
    if user.get("role") not in ["super_admin", "admin", "clinical_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required")
    return user


def require_staff_or_above(request: Request):
    user = get_current_user(request)
    if user.get("role") not in ["super_admin", "admin", "staff", "therapist", "clinical_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return user


@therapist_router.get("", response_model=List[TherapistRecord])
async def list_therapists(
    request: Request,
    active_only: bool = Query(False),
    session_mode: Optional[str] = Query(None),
    user: Dict = Depends(require_staff_or_above)
):
    db = get_db(request)
    return await TherapistService.list_therapists(db, active_only=active_only, session_mode=session_mode)



async def check_block_access(request: Request, therapist_id: str):
    user = get_current_user(request)
    if user["role"] in ("super_admin", "admin", "clinical_admin"):
        return user
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Access denied")
    account = await get_db(request).staff_users.find_one(
        {"user_id": user["user_id"], "role": "therapist", "active": {"$ne": False}},
        {"_id": 0, "therapist_id": 1},
    )
    if not account or account.get("therapist_id") != therapist_id:
        raise HTTPException(status_code=403, detail="Only your own availability can be modified")
    return user

# ==================== Blocks / Leave Management ====================
# Static /blocks routes MUST be registered before /{therapist_id}; otherwise FastAPI
# can resolve the literal word "blocks" as a therapist_id and return a false 404.
@therapist_router.post("/blocks", response_model=TherapistBlock)
async def create_therapist_block(
    payload: TherapistBlockCreate,
    request: Request,
    user: Dict = Depends(require_staff_or_above)
):
    await check_block_access(request, payload.therapist_id)
    db = get_db(request)
    try:
        start = datetime.fromisoformat(payload.starts_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(payload.ends_at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid interval")
    if not start.tzinfo or not end.tzinfo or end <= start or start.astimezone(timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Block must be a future time interval in CAT")
    if (end - start).days > 365:
        raise HTTPException(status_code=422, detail="Block may not exceed one year")
    if not await db.therapists.find_one({"id": payload.therapist_id}):
        raise HTTPException(status_code=404, detail="Therapist not found")
    # Do not silently cancel confirmed sessions when a therapist blocks time.
    bookings = await db.bookings.find({"therapist_id": payload.therapist_id, "status": {"$in": ["pending", "confirmed"]}}, {"_id": 0, "starts_at": 1, "ends_at": 1}).to_list(1000)
    for b in bookings:
        a = datetime.fromisoformat(b["starts_at"].replace("Z", "+00:00"))
        z = datetime.fromisoformat(b["ends_at"].replace("Z", "+00:00"))
        if start < z and end > a:
            raise HTTPException(status_code=409, detail="Block overlaps an existing appointment; contact administration")
    return await TherapistService.create_block(db, payload, actor_id=user.get("user_id"))


@therapist_router.get("/blocks", response_model=List[TherapistBlock])
async def list_therapist_blocks(
    request: Request,
    therapist_id: Optional[str] = Query(None),
    user: Dict = Depends(require_staff_or_above)
):
    if user["role"] == "therapist":
        account = await get_db(request).staff_users.find_one(
            {"user_id": user["user_id"], "role": "therapist", "active": {"$ne": False}},
            {"_id": 0, "therapist_id": 1},
        )
        if not account or not account.get("therapist_id"):
            raise HTTPException(status_code=403, detail="Therapist account is not linked")
        if therapist_id and therapist_id != account["therapist_id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        therapist_id = account["therapist_id"]
    elif user["role"] not in ("super_admin", "admin", "clinical_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    return await TherapistService.list_blocks(get_db(request), therapist_id=therapist_id)


@therapist_router.delete("/blocks/{block_id}")
async def delete_therapist_block(
    block_id: str,
    request: Request,
    user: Dict = Depends(require_staff_or_above)
):
    db = get_db(request)
    block = await db.therapist_blocks.find_one({"id": block_id})
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    await check_block_access(request, block["therapist_id"])
    success = await TherapistService.delete_block(db, block_id)
    if not success:
        raise HTTPException(status_code=404, detail="Block not found")
    return {"status": "deleted", "block_id": block_id}


@therapist_router.get("/{therapist_id}", response_model=TherapistRecord)
async def get_therapist_details(
    therapist_id: str,
    request: Request,
    user: Dict = Depends(require_staff_or_above)
):
    db = get_db(request)
    t = await TherapistService.get_therapist_by_id(db, therapist_id)
    if not t:
        raise HTTPException(status_code=404, detail="Therapist not found")
    return t


@therapist_router.post("", response_model=TherapistRecord)
async def create_therapist(
    payload: TherapistCreate,
    request: Request,
    user: Dict = Depends(require_admin)
):
    db = get_db(request)
    return await TherapistService.create_therapist(
        db, payload, actor_id=user.get("user_id"), actor_name=user.get("name")
    )


@therapist_router.put("/{therapist_id}", response_model=TherapistRecord)
async def update_therapist(
    therapist_id: str,
    payload: TherapistUpdate,
    request: Request,
    user: Dict = Depends(require_admin)
):
    db = get_db(request)
    updated = await TherapistService.update_therapist(
        db, therapist_id, payload, actor_id=user.get("user_id"), actor_name=user.get("name")
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Therapist not found")
    return updated


@therapist_router.patch("/{therapist_id}/notifications", response_model=TherapistRecord)
async def update_therapist_notification_settings(
    therapist_id: str,
    payload: TherapistNotificationSettingsUpdate,
    request: Request,
    user: Dict = Depends(require_admin)
):
    db = get_db(request)
    settings = payload.model_dump(exclude_unset=True)
    updated, err = await TherapistService.update_notification_settings(
        db,
        therapist_id,
        settings,
        actor_id=user.get("user_id"),
        actor_name=user.get("name")
    )
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    if not updated:
        raise HTTPException(status_code=404, detail="Therapist not found")
    return updated


@therapist_router.get("/{therapist_id}/availability")
async def get_therapist_availability(
    therapist_id: str,
    request: Request,
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    days_ahead: int = Query(14, ge=1, le=60),
    user: Dict = Depends(require_staff_or_above)
):
    db = get_db(request)
    slots = await TherapistService.get_available_slots(
        db, therapist_id=therapist_id, start_date_str=start_date, days_ahead=days_ahead
    )
    return {"therapist_id": therapist_id, "slots": slots}


@therapist_router.delete("/{therapist_id}")
async def delete_therapist(
    therapist_id: str,
    request: Request,
    user: Dict = Depends(require_admin)
):
    db = get_db(request)
    therapist = await db.therapists.find_one({"id": therapist_id}, {"_id": 0})
    if not therapist:
        raise HTTPException(status_code=404, detail="Therapist not found")

    protected_ids = {item.get("id") for item in DEFAULT_THERAPISTS}
    if therapist_id in protected_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This is a required FCA therapist record and cannot be deleted. Configure or deactivate it instead."
        )

    booking_count = await db.bookings.count_documents({"therapist_id": therapist_id})
    await db.therapist_blocks.delete_many({"therapist_id": therapist_id})

    if booking_count > 0:
        # Preserve historical booking references while removing the therapist from
        # the operational registry. This is a soft delete/archive, not a cascade.
        archived_at = now_iso()
        result = await db.therapists.update_one(
            {"id": therapist_id},
            {"$set": {
                "active": False,
                "whatsapp_notifications_enabled": False,
                "archived_at": archived_at,
                "archived_by": user.get("user_id"),
                "updated_at": archived_at
            }}
        )
        if result.matched_count != 1:
            raise HTTPException(status_code=404, detail="Therapist not found")

        await AuditService.log_activity(
            db,
            action="therapist_archived",
            actor_user_id=user.get("user_id"),
            actor_name=user.get("name"),
            metadata={
                "therapist_id": therapist_id,
                "name": therapist.get("name"),
                "booking_records_preserved": booking_count
            }
        )

        return {
            "status": "archived",
            "therapist_id": therapist_id,
            "booking_records_preserved": booking_count
        }

    result = await db.therapists.delete_one({"id": therapist_id})
    if result.deleted_count != 1:
        raise HTTPException(status_code=404, detail="Therapist not found")

    await AuditService.log_activity(
        db,
        action="therapist_deleted",
        actor_user_id=user.get("user_id"),
        actor_name=user.get("name"),
        metadata={
            "therapist_id": therapist_id,
            "name": therapist.get("name")
        }
    )

    return {"status": "deleted", "therapist_id": therapist_id}
