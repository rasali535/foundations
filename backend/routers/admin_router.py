from fastapi import APIRouter, HTTPException, Depends, Request, status, Query
from typing import List, Dict, Any, Optional
import bcrypt
from models import (
    NotificationLog, CRMActivityLog,
    Organisation, OrganisationCreate, OrganisationUpdate,
    OrganisationUser, OrganisationUserCreate
)
from services.notification_service import NotificationService
from services.hr_service import HRReportingService

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

# ==================== Corporate Organisation Management ====================
@admin_router.get("/organisations", response_model=List[Organisation])
async def list_organisations(request: Request, user: Dict = Depends(require_admin)):
    db = get_db(request)
    return await HRReportingService.list_organisations(db)

@admin_router.post("/organisations", response_model=Organisation, status_code=status.HTTP_201_CREATED)
async def create_organisation(payload: OrganisationCreate, request: Request, user: Dict = Depends(require_admin)):
    db = get_db(request)
    clean_code = payload.code.strip().upper()
    existing = await db.organisations.find_one({"code": clean_code})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Organisation code '{clean_code}' already in use.")
    payload.code = clean_code
    return await HRReportingService.create_organisation(db, payload)

@admin_router.get("/organisations/{org_id}", response_model=Organisation)
async def get_organisation_detail(org_id: str, request: Request, user: Dict = Depends(require_admin)):
    db = get_db(request)
    org = await HRReportingService.get_organisation(db, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found.")
    return org

@admin_router.put("/organisations/{org_id}", response_model=Organisation)
async def update_organisation(org_id: str, payload: OrganisationUpdate, request: Request, user: Dict = Depends(require_admin)):
    db = get_db(request)
    if payload.code:
        payload.code = payload.code.strip().upper()
    updated = await HRReportingService.update_organisation(db, org_id, payload)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found.")
    return updated

@admin_router.post("/organisations/{org_id}/users", response_model=OrganisationUser, status_code=status.HTTP_201_CREATED)
async def create_organisation_user(org_id: str, payload: OrganisationUserCreate, request: Request, user: Dict = Depends(require_admin)):
    db = get_db(request)
    org = await HRReportingService.get_organisation(db, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found.")
    
    username = payload.username.strip().lower()
    from server import USERS_DB
    
    if username in USERS_DB:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Username '{username}' already exists.")
    
    USERS_DB[username] = {
        "password_hash": bcrypt.hashpw(payload.password.strip().encode(), bcrypt.gensalt()).decode(),
        "role": payload.role,
        "name": payload.name.strip(),
        "therapist_id": None,
        "organisation_id": org_id
    }
    
    return await HRReportingService.create_organisation_user(db, org_id, payload)

@admin_router.get("/organisations/{org_id}/users", response_model=List[OrganisationUser])
async def list_organisation_users(org_id: str, request: Request, user: Dict = Depends(require_admin)):
    db = get_db(request)
    return await HRReportingService.list_organisation_users(db, org_id)
