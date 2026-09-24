from fastapi import APIRouter, HTTPException, Depends, Request, status, Query
from typing import List, Dict, Any, Optional
import bcrypt
from models import (
    NotificationLog, CRMActivityLog,
    Organisation, OrganisationCreate, OrganisationUpdate,
    OrganisationUser, OrganisationUserCreate,
    OrganisationContact, OrganisationContactBulkRequest,
    SessionAllocationApprovalRequest, InvoiceProfile, now_iso
)
from services.notification_service import NotificationService
from services.hr_service import HRReportingService
from services.audit_service import AuditService
from services.corporate_entitlement_service import CorporateEntitlementService

admin_router = APIRouter(prefix="/admin-ops", tags=["Admin Operations"])

def get_db(request: Request):
    return request.app.state.db

def get_current_user(request: Request) -> Dict[str, Any]:
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return {
        "user_id": user_id,
        "role": role,
        "name": request.session.get("name", user_id),
        "therapist_id": request.session.get("therapist_id"),
    }

def require_admin(request: Request):
    user = get_current_user(request)
    if user.get("role") not in ["super_admin", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def require_super_admin(request: Request):
    user = get_current_user(request)
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")
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
@admin_router.patch("/organisations/{org_id}", response_model=Organisation)
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
    
    pwd_hash = bcrypt.hashpw(payload.password.strip().encode(), bcrypt.gensalt()).decode()
    USERS_DB[username] = {
        "password_hash": pwd_hash,
        "role": payload.role,
        "name": payload.name.strip(),
        "therapist_id": None,
        "organisation_id": org_id
    }
    
    return await HRReportingService.create_organisation_user(db, org_id, payload, password_hash=pwd_hash)

@admin_router.get("/organisations/{org_id}/users", response_model=List[OrganisationUser])
async def list_organisation_users(org_id: str, request: Request, user: Dict = Depends(require_admin)):
    db = get_db(request)
    return await HRReportingService.list_organisation_users(db, org_id)


@admin_router.delete("/organisations/{org_id}/users/{account_id}")
async def delete_organisation_user(
    org_id: str,
    account_id: str,
    request: Request,
    user: Dict = Depends(require_super_admin),
):
    db = get_db(request)
    account = await db.organisation_users.find_one(
        {"id": account_id, "organisation_id": org_id},
        {"_id": 0}
    )
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="HR portal user not found.")

    await db.organisation_users.delete_one({"id": account_id, "organisation_id": org_id})

    from server import USERS_DB
    account_user_id = str(account.get("user_id") or "").strip().lower()
    if account_user_id:
        USERS_DB.pop(account_user_id, None)

    await AuditService.log_activity(
        db,
        action="organisation_user_deleted",
        actor_user_id=user.get("user_id"),
        actor_name=user.get("name"),
        metadata={
            "organisation_id": org_id,
            "deleted_user_id": account_user_id,
            "deleted_name": account.get("name"),
        },
    )
    return {"status": "deleted"}


@admin_router.get("/staff-users")
async def list_staff_users(
    request: Request,
    user: Dict = Depends(require_super_admin),
):
    db = get_db(request)
    return await db.staff_users.find(
        {},
        {
            "_id": 0,
            "user_id": 1,
            "name": 1,
            "role": 1,
            "active": 1,
            "organisation_id": 1,
            "therapist_id": 1,
        },
    ).sort("name", 1).to_list(5000)


@admin_router.delete("/staff-users/{staff_user_id:path}")
async def delete_staff_user(
    staff_user_id: str,
    request: Request,
    user: Dict = Depends(require_super_admin),
):
    db = get_db(request)
    normalized = str(staff_user_id or "").strip().lower()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID is required.")
    if normalized == str(user.get("user_id") or "").strip().lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account.")

    account = await db.staff_users.find_one(
        {"user_id": {"$regex": f"^{__import__('re').escape(normalized)}$", "$options": "i"}},
        {"_id": 0},
    )
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found.")

    if account.get("role") == "super_admin" and account.get("active") is not False:
        active_super_admins = await db.staff_users.count_documents(
            {"role": "super_admin", "active": {"$ne": False}}
        )
        if active_super_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete the last active super admin account.",
            )

    await db.staff_users.delete_one({"user_id": account.get("user_id")})
    from server import USERS_DB
    USERS_DB.pop(normalized, None)

    await AuditService.log_activity(
        db,
        action="staff_user_deleted",
        actor_user_id=user.get("user_id"),
        actor_name=user.get("name"),
        metadata={
            "deleted_user_id": normalized,
            "deleted_name": account.get("name"),
            "deleted_role": account.get("role"),
        },
    )
    return {"status": "deleted", "user_id": normalized}


# ==================== Corporate Employee Roster & Entitlements ====================
@admin_router.get("/organisations/{org_id}/contacts")
async def list_organisation_contacts(
    org_id: str,
    request: Request,
    user: Dict = Depends(require_admin)
):
    db = get_db(request)
    org = await db.organisations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found.")

    contacts = await db.organisation_contacts.find(
        {"organisation_id": org_id},
        {"_id": 0}
    ).sort("name", 1).to_list(50000)
    pool = await CorporateEntitlementService.organisation_pool_summary(db, org_id)
    return {"contacts": contacts, "pool": pool}


@admin_router.post("/organisations/{org_id}/contacts/bulk")
async def bulk_upsert_organisation_contacts(
    org_id: str,
    payload: OrganisationContactBulkRequest,
    request: Request,
    user: Dict = Depends(require_admin)
):
    db = get_db(request)
    org = await db.organisations.find_one({"id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found.")

    if not payload.contacts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one contact is required.")

    inserted = 0
    updated = 0
    seen = set()
    for row in payload.contacts:
        email = CorporateEntitlementService.normalize_email(row.email)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Every corporate roster member must have an email address so their four-session allocation can be tracked."
            )
        if email in seen:
            continue
        seen.add(email)

        existing = await db.organisation_contacts.find_one(
            {"organisation_id": org_id, "email_normalized": email},
            {"_id": 0}
        )
        now = now_iso()
        update_fields = {
            "name": row.name.strip(),
            "email": email,
            "email_normalized": email,
            "phone": str(row.phone or "").strip() or None,
            "job_title": str(row.job_title or "").strip() or None,
            "department": str(row.department or "").strip() or None,
            "contact_type": str(row.contact_type or "employee").strip().lower(),
            "active": True,
            "updated_at": now,
        }

        if existing:
            await db.organisation_contacts.update_one(
                {"id": existing["id"]},
                {"$set": update_fields}
            )
            updated += 1
        else:
            contact = OrganisationContact(
                organisation_id=org_id,
                name=update_fields["name"],
                email=email,
                phone=update_fields["phone"],
                job_title=update_fields["job_title"],
                department=update_fields["department"],
                contact_type=update_fields["contact_type"],
                base_session_allocation=4,
                extra_sessions_approved=0,
                active=True,
                created_at=now,
                updated_at=now,
            )
            doc = contact.model_dump()
            doc["email_normalized"] = email
            await db.organisation_contacts.insert_one(doc)
            inserted += 1

        # If this person already completed an FCA intake under the organisation,
        # bind the CRM client to the roster entry without exposing that link to HR.
        contact_doc = await db.organisation_contacts.find_one(
            {"organisation_id": org_id, "email_normalized": email},
            {"_id": 0}
        )
        if contact_doc:
            await db.crm_clients.update_many(
                {"organisation_id": org_id, "email": {"$regex": f"^{__import__('re').escape(email)}$", "$options": "i"}},
                {"$set": {"organisation_contact_id": contact_doc["id"], "updated_at": now}}
            )

    pool = await CorporateEntitlementService.organisation_pool_summary(db, org_id)
    contacts = await db.organisation_contacts.find(
        {"organisation_id": org_id},
        {"_id": 0}
    ).sort("name", 1).to_list(50000)

    await AuditService.log_activity(
        db,
        action="organisation_roster_bulk_updated",
        actor_user_id=user.get("user_id"),
        actor_name=user.get("name"),
        metadata={
            "organisation_id": org_id,
            "inserted": inserted,
            "updated": updated,
            "member_count": pool["member_count"],
            "allocated_sessions": pool["allocated_sessions"],
        }
    )
    return {"inserted": inserted, "updated": updated, "contacts": contacts, "pool": pool}


@admin_router.patch("/organisations/{org_id}/contacts/{contact_id}/status")
async def set_organisation_contact_status(
    org_id: str,
    contact_id: str,
    request: Request,
    active: bool = Query(...),
    user: Dict = Depends(require_admin)
):
    db = get_db(request)
    result = await db.organisation_contacts.update_one(
        {"id": contact_id, "organisation_id": org_id},
        {"$set": {"active": active, "updated_at": now_iso()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corporate roster member not found.")
    pool = await CorporateEntitlementService.organisation_pool_summary(db, org_id)
    return {"status": "updated", "active": active, "pool": pool}


@admin_router.delete("/organisations/{org_id}/contacts/{contact_id}")
async def delete_organisation_contact(
    org_id: str,
    contact_id: str,
    request: Request,
    user: Dict = Depends(require_super_admin),
):
    db = get_db(request)
    contact = await db.organisation_contacts.find_one(
        {"id": contact_id, "organisation_id": org_id},
        {"_id": 0}
    )
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corporate roster member not found.")

    await db.organisation_contacts.delete_one({"id": contact_id, "organisation_id": org_id})
    await db.crm_clients.update_many(
        {"organisation_id": org_id, "organisation_contact_id": contact_id},
        {"$unset": {"organisation_contact_id": ""}, "$set": {"updated_at": now_iso()}},
    )

    await AuditService.log_activity(
        db,
        action="organisation_contact_deleted",
        actor_user_id=user.get("user_id"),
        actor_name=user.get("name"),
        metadata={
            "organisation_id": org_id,
            "contact_id": contact_id,
            "deleted_email": contact.get("email"),
        },
    )
    pool = await CorporateEntitlementService.organisation_pool_summary(db, org_id)
    return {"status": "deleted", "pool": pool}


def require_therapist_approval_role(request: Request):
    user = get_current_user(request)
    if user.get("role") not in ["therapist", "clinical_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Additional corporate sessions require therapist or clinical lead approval."
        )
    return user


@admin_router.post("/organisations/{org_id}/contacts/{contact_id}/approve-extra-sessions")
async def approve_extra_sessions(
    org_id: str,
    contact_id: str,
    payload: SessionAllocationApprovalRequest,
    request: Request,
    user: Dict = Depends(require_therapist_approval_role)
):
    if payload.extra_sessions <= 0 or payload.extra_sessions > 20:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Extra sessions must be between 1 and 20.")

    db = get_db(request)
    contact = await db.organisation_contacts.find_one(
        {"id": contact_id, "organisation_id": org_id, "active": True},
        {"_id": 0}
    )
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corporate roster member not found.")

    month_key = payload.month or CorporateEntitlementService.month_key()
    monthly_map = contact.get("extra_sessions_by_month") or {}
    new_extra = int(monthly_map.get(month_key) or 0) + int(payload.extra_sessions)
    now = now_iso()
    await db.organisation_contacts.update_one(
        {"id": contact_id, "organisation_id": org_id},
        {"$set": {
            f"extra_sessions_by_month.{month_key}": new_extra,
            "extra_sessions_approved": new_extra,
            "extra_sessions_approved_by": user.get("therapist_id") or user.get("user_id"),
            "extra_sessions_approved_by_name": user.get("name"),
            "extra_sessions_approved_at": now,
            "extra_sessions_approval_reason": payload.reason,
            "updated_at": now,
        }}
    )

    await AuditService.log_activity(
        db,
        action="corporate_extra_sessions_approved",
        actor_user_id=user.get("user_id"),
        actor_name=user.get("name"),
        metadata={
            "organisation_id": org_id,
            "contact_id": contact_id,
            "extra_sessions_added": payload.extra_sessions,
            "new_extra_session_total": new_extra,
            "month": month_key,
        }
    )
    pool = await CorporateEntitlementService.organisation_pool_summary(db, org_id, reference=f"{month_key}-01T00:00:00+02:00")
    return {"status": "approved", "extra_sessions_approved": new_extra, "month": month_key, "pool": pool}


# ==================== Invoice Identity / Company Profile ====================
@admin_router.get("/invoice-profile", response_model=InvoiceProfile)
async def get_invoice_profile(
    request: Request,
    user: Dict = Depends(require_admin)
):
    db = get_db(request)
    doc = await db.invoice_profiles.find_one({"_id": "default"})
    if not doc:
        return InvoiceProfile()
    doc.pop("_id", None)
    return InvoiceProfile(**doc)


@admin_router.put("/invoice-profile", response_model=InvoiceProfile)
async def update_invoice_profile(
    payload: InvoiceProfile,
    request: Request,
    user: Dict = Depends(require_admin)
):
    db = get_db(request)
    data = payload.model_dump()
    data["updated_at"] = now_iso()
    await db.invoice_profiles.update_one(
        {"_id": "default"},
        {"$set": data},
        upsert=True
    )
    await AuditService.log_activity(
        db,
        action="invoice_profile_updated",
        actor_user_id=user.get("user_id"),
        actor_name=user.get("name"),
        metadata={"profile": "default"}
    )
    return InvoiceProfile(**data)


@admin_router.get("/corporate-entitlements/client/{client_id}")
async def get_client_corporate_entitlement(
    client_id: str,
    request: Request,
    user: Dict = Depends(require_staff_or_above)
):
    db = get_db(request)
    client = await db.crm_clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    if not client.get("organisation_id"):
        return {"corporate": False}

    contact = await CorporateEntitlementService.get_contact_for_client(db, client)
    entitlement = await CorporateEntitlementService.remaining_for_client(db, client)
    org = await db.organisations.find_one({"id": client.get("organisation_id")}, {"_id": 0})
    return {
        "corporate": True,
        "organisation": {
            "id": client.get("organisation_id"),
            "name": (org or {}).get("name") or client.get("organisation_name"),
        },
        "roster_member": {
            "id": contact.get("id"),
            "name": contact.get("name"),
            "email": contact.get("email"),
            "base_session_allocation": contact.get("base_session_allocation", 4),
            "extra_sessions_approved": contact.get("extra_sessions_approved", 0),
            "extra_sessions_approved_by_name": contact.get("extra_sessions_approved_by_name"),
            "extra_sessions_approved_at": contact.get("extra_sessions_approved_at"),
            "extra_sessions_approval_reason": contact.get("extra_sessions_approval_reason"),
        } if contact else None,
        "entitlement": entitlement,
    }


@admin_router.post("/corporate-entitlements/client/{client_id}/approve-extra")
async def approve_client_extra_sessions(
    client_id: str,
    payload: SessionAllocationApprovalRequest,
    request: Request,
    user: Dict = Depends(require_therapist_approval_role)
):
    if payload.extra_sessions <= 0 or payload.extra_sessions > 20:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Extra sessions must be between 1 and 20.")

    db = get_db(request)
    client = await db.crm_clients.find_one({"id": client_id}, {"_id": 0})
    if not client or not client.get("organisation_id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corporate client not found.")

    contact = await CorporateEntitlementService.get_contact_for_client(db, client)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This corporate client is not linked to an active employee roster entry."
        )

    month_key = payload.month or CorporateEntitlementService.month_key()
    monthly_map = contact.get("extra_sessions_by_month") or {}
    new_extra = int(monthly_map.get(month_key) or 0) + int(payload.extra_sessions)
    now = now_iso()
    await db.organisation_contacts.update_one(
        {"id": contact["id"], "organisation_id": client["organisation_id"]},
        {"$set": {
            f"extra_sessions_by_month.{month_key}": new_extra,
            "extra_sessions_approved": new_extra,
            "extra_sessions_approved_by": user.get("therapist_id") or user.get("user_id"),
            "extra_sessions_approved_by_name": user.get("name"),
            "extra_sessions_approved_at": now,
            "extra_sessions_approval_reason": payload.reason,
            "updated_at": now,
        }}
    )

    await AuditService.log_activity(
        db,
        action="corporate_extra_sessions_approved",
        actor_user_id=user.get("user_id"),
        actor_name=user.get("name"),
        client_id=client_id,
        metadata={
            "organisation_id": client["organisation_id"],
            "contact_id": contact["id"],
            "extra_sessions_added": payload.extra_sessions,
            "new_extra_session_total": new_extra,
            "month": month_key,
        }
    )
    entitlement = await CorporateEntitlementService.remaining_for_client(
        db, client, reference=f"{month_key}-01T00:00:00+02:00"
    )
    return {"status": "approved", "month": month_key, "entitlement": entitlement}
