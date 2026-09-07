from fastapi import APIRouter, HTTPException, Depends, Request, status, Query
from typing import List, Dict, Any, Optional
from models import (
    Booking, BookingCreateRequest, MultiBookingCreateRequest,
    BookingRescheduleRequest, BookingStatusUpdateRequest
)
from services.booking_service import BookingService

booking_router = APIRouter(prefix="/bookings", tags=["Bookings"])

def get_db(request: Request):
    return request.app.state.db

def get_current_user(request: Request) -> Dict[str, Any]:
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return {"user_id": user_id, "role": role, "name": request.session.get("name", user_id)}

def require_staff_or_therapist(request: Request):
    user = get_current_user(request)
    allowed = ["super_admin", "admin", "staff", "therapist", "clinical_admin"]
    if user.get("role") not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return user

@booking_router.get("")
async def list_bookings(
    request: Request,
    client_id: Optional[str] = Query(None),
    therapist_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    session_type: Optional[str] = Query(None),
    session_mode: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: Dict = Depends(require_staff_or_therapist)
):
    db = get_db(request)
    # If logged-in user is therapist, restrict to assigned therapist bookings
    if user.get("role") == "therapist" and user.get("therapist_id"):
        therapist_id = user.get("therapist_id")

    skip = (page - 1) * limit
    bookings, total = await BookingService.list_bookings(
        db,
        client_id=client_id,
        therapist_id=therapist_id,
        status=status,
        session_type=session_type,
        session_mode=session_mode,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )
    return {
        "bookings": bookings,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 1
    }

@booking_router.post("", response_model=Booking)
async def create_single_booking(
    payload: BookingCreateRequest,
    request: Request,
    user: Dict = Depends(require_staff_or_therapist)
):
    db = get_db(request)
    booking, err = await BookingService.create_booking(
        db,
        request=payload,
        actor_id=user.get("user_id"),
        actor_name=user.get("name")
    )
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    return booking

@booking_router.post("/multi")
async def create_multi_booking(
    payload: MultiBookingCreateRequest,
    request: Request,
    user: Dict = Depends(require_staff_or_therapist)
):
    db = get_db(request)
    result, err = await BookingService.create_multi_booking(
        db,
        request=payload,
        actor_id=user.get("user_id"),
        actor_name=user.get("name")
    )
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    return result

@booking_router.get("/{booking_id}", response_model=Booking)
async def get_booking_details(
    booking_id: str,
    request: Request,
    user: Dict = Depends(require_staff_or_therapist)
):
    db = get_db(request)
    booking_doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking_doc:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Therapist scope check
    if user.get("role") == "therapist" and user.get("therapist_id") and booking_doc.get("therapist_id") != user.get("therapist_id"):
        raise HTTPException(status_code=403, detail="Access to booking denied")

    return Booking(**booking_doc)

@booking_router.post("/{booking_id}/reschedule", response_model=Booking)
async def reschedule_booking(
    booking_id: str,
    payload: BookingRescheduleRequest,
    request: Request,
    user: Dict = Depends(require_staff_or_therapist)
):
    db = get_db(request)
    booking, err = await BookingService.reschedule_booking(
        db,
        booking_id=booking_id,
        request=payload,
        actor_id=user.get("user_id"),
        actor_name=user.get("name")
    )
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    return booking

@booking_router.post("/{booking_id}/status", response_model=Booking)
async def update_booking_status(
    booking_id: str,
    payload: BookingStatusUpdateRequest,
    request: Request,
    user: Dict = Depends(require_staff_or_therapist)
):
    db = get_db(request)
    booking, err = await BookingService.update_booking_status(
        db,
        booking_id=booking_id,
        request=payload,
        actor_id=user.get("user_id"),
        actor_name=user.get("name")
    )
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    return booking
