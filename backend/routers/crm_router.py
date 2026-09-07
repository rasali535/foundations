from fastapi import APIRouter, HTTPException, Depends, Request, status, Query
from typing import List, Dict, Any, Optional
from models import (
    CRMClient, CRMClientCreate, CRMClientUpdate,
    CRMNote, CRMNoteCreate, CRMNoteUpdate
)
from services.crm_service import CRMService
from services.intake_service import IntakeService
from services.therapist_service import TherapistService
from services.booking_service import BookingService
from datetime import datetime, timezone, timedelta

crm_router = APIRouter(prefix="/crm", tags=["CRM"])

def get_db(request: Request):
    return request.app.state.db

def get_current_user(request: Request) -> Dict[str, Any]:
    user = request.state.user if hasattr(request.state, "user") else None
    if not user:
        user_id = request.session.get("user_id")
        role = request.session.get("role")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        user = {"user_id": user_id, "role": role, "name": request.session.get("name", user_id)}
    return user

def require_crm_access(request: Request):
    user = get_current_user(request)
    allowed = ["super_admin", "admin", "staff", "clinical_admin"]
    if user.get("role") not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to CRM operations")
    return user

# ==================== Dashboard Operational Metrics ====================
@crm_router.get("/dashboard")
async def get_crm_dashboard(request: Request, user: Dict = Depends(require_crm_access)):
    db = get_db(request)
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
    week_end = (now + timedelta(days=7)).isoformat()

    total_clients = await db.crm_clients.count_documents({})
    total_intakes = await db.crm_intake_submissions.count_documents({})
    
    # Today's Bookings
    today_bookings_cursor = db.bookings.find({
        "starts_at": {"$gte": today_start, "$lte": today_end}
    }, {"_id": 0}).sort("starts_at", 1)
    today_bookings = await today_bookings_cursor.to_list(100)

    # Upcoming Bookings (Next 7 days)
    upcoming_count = await db.bookings.count_documents({
        "starts_at": {"$gte": today_start, "$lte": week_end},
        "status": {"$in": ["confirmed", "pending"]}
    })

    # Cancellations & No-Shows total
    cancellations_count = await db.bookings.count_documents({"status": "cancelled"})
    noshow_count = await db.bookings.count_documents({"status": "no_show"})

    # Recent Clients
    recent_clients_cursor = db.crm_clients.find({}, {"_id": 0}).sort("created_at", -1).limit(5)
    recent_clients = await recent_clients_cursor.to_list(5)

    # Recent Intakes
    recent_intakes_cursor = db.crm_intake_submissions.find({}, {"_id": 0}).sort("created_at", -1).limit(5)
    recent_intakes = await recent_intakes_cursor.to_list(5)

    # Recent Activity
    recent_activity_cursor = db.crm_activity_log.find({}, {"_id": 0}).sort("created_at", -1).limit(10)
    recent_activity = await recent_activity_cursor.to_list(10)

    return {
        "kpis": {
            "total_clients": total_clients,
            "total_intakes": total_intakes,
            "today_appointments_count": len(today_bookings),
            "upcoming_appointments_count": upcoming_count,
            "cancellations_count": cancellations_count,
            "no_show_count": noshow_count
        },
        "today_bookings": today_bookings,
        "recent_clients": recent_clients,
        "recent_intakes": recent_intakes,
        "recent_activity": recent_activity
    }

# ==================== Clients Directory ====================
@crm_router.get("/clients")
async def list_clients(
    request: Request,
    query: str = Query("", description="Search name, email, phone, client number"),
    status: Optional[str] = Query(None),
    organisation_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    user: Dict = Depends(require_crm_access)
):
    db = get_db(request)
    skip = (page - 1) * limit
    clients, total = await CRMService.search_clients(
        db, query=query, status=status, organisation_id=organisation_id, skip=skip, limit=limit
    )
    return {
        "clients": clients,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 1
    }

@crm_router.post("/clients", response_model=CRMClient)
async def create_client_manual(
    payload: CRMClientCreate,
    request: Request,
    user: Dict = Depends(require_crm_access)
):
    db = get_db(request)
    client, _ = await CRMService.find_or_create_client(
        db,
        payload.model_dump(),
        actor_id=user.get("user_id"),
        actor_name=user.get("name")
    )
    return client

@crm_router.get("/clients/{client_id}")
async def get_client_profile(
    client_id: str,
    request: Request,
    user: Dict = Depends(require_crm_access)
):
    db = get_db(request)
    client = await CRMService.get_client_by_id(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Fetch Intakes
    intakes = await IntakeService.get_client_intakes(db, client_id)

    # Fetch Bookings
    bookings, _ = await BookingService.list_bookings(db, client_id=client_id, limit=100)

    # Fetch CRM Notes
    notes = await CRMService.list_notes(db, client_id)

    # Fetch Activity Log
    activity_cursor = db.crm_activity_log.find({"client_id": client_id}, {"_id": 0}).sort("created_at", -1).limit(50)
    activity_logs = await activity_cursor.to_list(50)

    return {
        "client": client,
        "intakes": intakes,
        "bookings": bookings,
        "notes": notes,
        "activity_logs": activity_logs
    }

@crm_router.put("/clients/{client_id}", response_model=CRMClient)
async def update_client_profile(
    client_id: str,
    payload: CRMClientUpdate,
    request: Request,
    user: Dict = Depends(require_crm_access)
):
    db = get_db(request)
    updated = await CRMService.update_client(
        db, client_id, payload, actor_id=user.get("user_id"), actor_name=user.get("name")
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Client not found")
    return updated

# ==================== Administrative CRM Notes ====================
@crm_router.post("/clients/{client_id}/notes", response_model=CRMNote)
async def add_crm_note(
    client_id: str,
    payload: CRMNoteCreate,
    request: Request,
    user: Dict = Depends(require_crm_access)
):
    db = get_db(request)
    client = await CRMService.get_client_by_id(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    note = await CRMService.create_note(
        db,
        client_id=client_id,
        note_data=payload,
        author_id=user.get("user_id"),
        author_name=user.get("name", "Staff")
    )
    return note

@crm_router.put("/notes/{note_id}", response_model=CRMNote)
async def update_crm_note(
    note_id: str,
    payload: CRMNoteUpdate,
    request: Request,
    user: Dict = Depends(require_crm_access)
):
    db = get_db(request)
    updated = await CRMService.update_note(
        db,
        note_id=note_id,
        update_data=payload,
        actor_id=user.get("user_id"),
        actor_name=user.get("name", "Staff")
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Note not found")
    return updated

@crm_router.delete("/notes/{note_id}")
async def delete_crm_note(
    note_id: str,
    request: Request,
    user: Dict = Depends(require_crm_access)
):
    db = get_db(request)
    success = await CRMService.delete_note(
        db, note_id, actor_id=user.get("user_id"), actor_name=user.get("name", "Staff")
    )
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "deleted", "note_id": note_id}

# ==================== Intake Submission Endpoint ====================
@crm_router.post("/intake")
async def submit_intake(payload: Dict[str, Any], request: Request):
    """
    Intake form ingestion endpoint:
    Atomically links submission to CRM client and logs intake event.
    """
    db = get_db(request)
    result = await IntakeService.process_intake_submission(db, payload, source="website_intake")
    return result
