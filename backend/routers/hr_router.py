from fastapi import APIRouter, HTTPException, Depends, Request, status, Query, Response
from typing import List, Dict, Any, Optional
from services.hr_service import HRReportingService
from services.audit_service import AuditService

hr_router = APIRouter(prefix="/hr", tags=["Corporate HR Portal"])

def get_db(request: Request):
    return request.app.state.db

def get_current_hr_user(request: Request) -> Dict[str, Any]:
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    org_id = request.session.get("organisation_id")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    
    allowed = ["hr_admin", "hr_viewer", "super_admin", "admin"]
    if role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Corporate HR credentials required.")
    
    return {
        "user_id": user_id,
        "role": role,
        "name": request.session.get("name", user_id),
        "organisation_id": org_id
    }

def require_hr_scoped_org(request: Request, user: Dict = Depends(get_current_hr_user)) -> str:
    role = user.get("role")
    session_org_id = user.get("organisation_id")
    query_org_id = request.query_params.get("organisation_id") or request.query_params.get("org_id")
    header_org_id = (
        request.headers.get("organisation_id") or
        request.headers.get("organisation") or
        request.headers.get("x-organisation-id")
    )

    if role in ["hr_admin", "hr_viewer"]:
        if not session_org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No corporate organisation associated with this HR account.")
        # Strict cross-tenant protection: if param or header is passed and doesn't match session, block with 403
        if query_org_id and query_org_id != session_org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access forbidden.")
        if header_org_id and header_org_id != session_org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access forbidden.")
        return session_org_id
    
    # Admins can inspect specific organisation if query param provided
    if query_org_id:
        return query_org_id
    if header_org_id:
        return header_org_id
    if session_org_id:
        return session_org_id
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="organisation_id required for admin inspection.")


@hr_router.get("/me")
async def get_hr_me(
    request: Request,
    user: Dict = Depends(get_current_hr_user),
    org_id: str = Depends(require_hr_scoped_org)
):
    db = get_db(request)
    org = await HRReportingService.get_organisation(db, org_id)
    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "role": user["role"],
        "organisation_id": org_id,
        "organisation_name": org.name if org else "Corporate Partner"
    }


@hr_router.get("/dashboard")
async def get_hr_dashboard(
    request: Request,
    period: str = Query("current_month", description="current_month, previous_month, quarter, year, all_time"),
    user: Dict = Depends(get_current_hr_user),
    org_id: str = Depends(require_hr_scoped_org)
):
    db = get_db(request)
    dashboard_data = await HRReportingService.get_dashboard(db, org_id, period=period)

    # Record safe audit event (Zero client PII stored)
    await AuditService.log_activity(
        db,
        action="hr_dashboard_viewed",
        actor_user_id=user["user_id"],
        actor_name=user["name"],
        metadata={"organisation_id": org_id, "period": period}
    )
    return dashboard_data


@hr_router.get("/contract")
async def get_hr_contract(
    request: Request,
    user: Dict = Depends(get_current_hr_user),
    org_id: str = Depends(require_hr_scoped_org)
):
    db = get_db(request)
    contract_data = await HRReportingService.get_contract_status(db, org_id)

    await AuditService.log_activity(
        db,
        action="hr_contract_viewed",
        actor_user_id=user["user_id"],
        actor_name=user["name"],
        metadata={"organisation_id": org_id}
    )
    return contract_data


@hr_router.get("/utilisation")
async def get_hr_utilisation(
    request: Request,
    granularity: str = Query("monthly", description="monthly"),
    user: Dict = Depends(get_current_hr_user),
    org_id: str = Depends(require_hr_scoped_org)
):
    db = get_db(request)
    trends = await HRReportingService.get_utilisation_trends(db, org_id, granularity=granularity)

    await AuditService.log_activity(
        db,
        action="hr_utilisation_report_viewed",
        actor_user_id=user["user_id"],
        actor_name=user["name"],
        metadata={"organisation_id": org_id, "granularity": granularity}
    )
    return trends


@hr_router.get("/session-types")
async def get_hr_session_types(
    request: Request,
    user: Dict = Depends(get_current_hr_user),
    org_id: str = Depends(require_hr_scoped_org)
):
    db = get_db(request)
    return await HRReportingService.get_session_types_breakdown(db, org_id)


@hr_router.get("/session-modes")
async def get_hr_session_modes(
    request: Request,
    user: Dict = Depends(get_current_hr_user),
    org_id: str = Depends(require_hr_scoped_org)
):
    db = get_db(request)
    return await HRReportingService.get_session_modes_breakdown(db, org_id)


@hr_router.get("/export/csv")
async def export_safe_hr_csv(
    request: Request,
    user: Dict = Depends(get_current_hr_user),
    org_id: str = Depends(require_hr_scoped_org)
):
    db = get_db(request)
    csv_content = await HRReportingService.generate_safe_aggregate_csv(db, org_id)

    await AuditService.log_activity(
        db,
        action="hr_report_exported",
        actor_user_id=user["user_id"],
        actor_name=user["name"],
        metadata={"organisation_id": org_id, "format": "csv"}
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fca_corporate_utilisation_aggregate.csv"}
    )
