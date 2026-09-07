from fastapi import APIRouter, HTTPException, Depends, Request, status, Query
from typing import List, Dict, Any, Optional
from models import NotificationLog, CRMActivityLog
from services.notification_service import NotificationService

admin_router = APIRouter(prefix="/admin-ops", tags=["Admin Operations"])

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
    if user.get("role") not in ["super_admin", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user

def require_staff_or_above(request: Request):
    user = get_current_user(request)
    if user.get("role") not in ["super_admin", "admin", "staff", "therapist", "clinical_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return user

# ==================== Notification Logs & Config ====================
@admin_router.get("/notifications", response_model=List[NotificationLog])
async def list_notification_logs(
    request: Request,
    client_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    user: Dict = Depends(require_staff_or_above)
):
    db = get_db(request)
    return await NotificationService.list_notifications(db, client_id=client_id, limit=limit)

@admin_router.get("/notifications/config")
async def get_notification_config_status(
    request: Request,
    user: Dict = Depends(require_staff_or_above)
):
    return await NotificationService.get_config_status()

# ==================== Immutable Audit Logs ====================
@admin_router.get("/audit/logs")
async def list_audit_logs(
    request: Request,
    action: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    booking_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: Dict = Depends(require_admin)
):
    db = get_db(request)
    filter_dict = {}
    if action:
        filter_dict["action"] = action
    if client_id:
        filter_dict["client_id"] = client_id
    if booking_id:
        filter_dict["booking_id"] = booking_id

    skip = (page - 1) * limit
    total = await db.crm_activity_log.count_documents(filter_dict)
    cursor = db.crm_activity_log.find(filter_dict, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)

    return {
        "logs": docs,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 1
    }
