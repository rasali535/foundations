import logging
from fastapi import APIRouter, HTTPException, Depends, Request, status, Query, Response
from typing import List, Dict, Any, Optional
from services.hr_service import HRReportingService
from services.audit_service import AuditService

hr_router = APIRouter(prefix="/hr", tags=["Corporate HR Portal"])

# Defense-in-depth privacy boundary for HR-facing payloads.
# HR may receive organisation-level aggregates only — never client or booking rows.
_HR_FORBIDDEN_RESPONSE_KEYS = {
    "client_id", "client_number", "client_name", "first_name", "last_name",
    "email", "phone", "employee_id", "booking_id", "booking_batch_id",
    "therapist_id", "therapist_name", "starts_at", "ends_at", "participants",
    "submission_data", "intake", "intakes", "reason", "notes",
    "emergency_contact_name", "emergency_contact_phone", "recipient"
}


def _assert_hr_aggregate_only(payload: Any) -> None:
    """
    Fail closed if an HR endpoint ever attempts to return row-level client data.

    This protects against future regressions even if a reporting service is changed
    to include raw booking/client fields by mistake. Organisation identifiers,
    organisation names, aggregate counts, periods and suppression metadata remain allowed.
    """
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump()

    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key).lower() in _HR_FORBIDDEN_RESPONSE_KEYS:
                logging.error("HR privacy boundary blocked forbidden response field: %s", key)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="HR privacy boundary prevented an unsafe response."
                )
            _assert_hr_aggregate_only(value)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            _assert_hr_aggregate_only(item)


def _assert_hr_csv_aggregate_only(csv_content: str) -> None:
    """Ensure HR CSV exports retain the approved aggregate-only schema."""
    expected_header = "Period,Total Sessions,Completed,Cancelled,No Show"
    header = (csv_content.splitlines() or [""])[0].strip()
    if header != expected_header:
        logging.error("HR privacy boundary blocked unexpected CSV schema")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="HR privacy boundary prevented an unsafe export."
        )


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
    # /me contains only the authenticated HR user's own identity plus organisation identity.
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
    _assert_hr_aggregate_only(dashboard_data)

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
    _assert_hr_aggregate_only(contract_data)

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
    _assert_hr_aggregate_only(trends)

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
    data = await HRReportingService.get_session_types_breakdown(db, org_id)
    _assert_hr_aggregate_only(data)
    return data


@hr_router.get("/session-modes")
async def get_hr_session_modes(
    request: Request,
    user: Dict = Depends(get_current_hr_user),
    org_id: str = Depends(require_hr_scoped_org)
):
    db = get_db(request)
    data = await HRReportingService.get_session_modes_breakdown(db, org_id)
    _assert_hr_aggregate_only(data)
    return data


@hr_router.get("/export/csv")
async def export_safe_hr_csv(
    request: Request,
    user: Dict = Depends(get_current_hr_user),
    org_id: str = Depends(require_hr_scoped_org)
):
    db = get_db(request)
    csv_content = await HRReportingService.generate_safe_aggregate_csv(db, org_id)
    _assert_hr_csv_aggregate_only(csv_content)

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
