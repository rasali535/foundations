from fastapi import APIRouter, HTTPException, Depends, Request, status, Query
from typing import List, Dict, Any, Optional
from models import (
    Therapist, TherapistCreate, TherapistUpdate,
    TherapistBlock, TherapistBlockCreate
)
from services.therapist_service import TherapistService

therapist_router = APIRouter(prefix="/therapists", tags=["Therapists"])

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

@therapist_router.get("", response_model=List[Therapist])
async def list_therapists(
    request: Request,
    active_only: bool = Query(False),
    session_mode: Optional[str] = Query(None),
    user: Dict = Depends(require_staff_or_above)
):
    db = get_db(request)
    return await TherapistService.list_therapists(db, active_only=active_only, session_mode=session_mode)

@therapist_router.get("/{therapist_id}", response_model=Therapist)
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

@therapist_router.post("", response_model=Therapist)
async def create_therapist(
    payload: TherapistCreate,
    request: Request,
    user: Dict = Depends(require_admin)
):
    db = get_db(request)
    return await TherapistService.create_therapist(
        db, payload, actor_id=user.get("user_id"), actor_name=user.get("name")
    )

@therapist_router.put("/{therapist_id}", response_model=Therapist)
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

# ==================== Blocks / Leave Management ====================
@therapist_router.post("/blocks", response_model=TherapistBlock)
async def create_therapist_block(
    payload: TherapistBlockCreate,
    request: Request,
    user: Dict = Depends(require_admin)
):
    db = get_db(request)
    return await TherapistService.create_block(db, payload, actor_id=user.get("user_id"))

@therapist_router.get("/blocks", response_model=List[TherapistBlock])
async def list_therapist_blocks(
    request: Request,
    therapist_id: Optional[str] = Query(None),
    user: Dict = Depends(require_staff_or_above)
):
    db = get_db(request)
    return await TherapistService.list_blocks(db, therapist_id=therapist_id)

@therapist_router.delete("/blocks/{block_id}")
async def delete_therapist_block(
    block_id: str,
    request: Request,
    user: Dict = Depends(require_admin)
):
    db = get_db(request)
    success = await TherapistService.delete_block(db, block_id)
    if not success:
        raise HTTPException(status_code=404, detail="Block not found")
    return {"status": "deleted", "block_id": block_id}
