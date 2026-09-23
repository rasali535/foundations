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


@hr_router.get("/booking-ledger")
async def get_hr_booking_ledger(
    request: Request,
    period: str = Query("current_month", description="current_month, previous_month, quarter, year, all_time"),
    user: Dict = Depends(get_current_hr_user),
    org_id: str = Depends(require_hr_scoped_org)
):
    """
    Accounts-only booking ledger.

    Returns one row per organisation booking with financial/reconciliation metadata only.
    It intentionally excludes employee identity, contact data, therapist identity,
    clinical reasons, intake data and notes.
    """
    if user.get("role") not in ["hr_admin", "super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accounts booking ledger requires HR Admin access."
        )

    db = get_db(request)
    client_docs = await db.crm_clients.find(
        {"organisation_id": org_id},
        {"_id": 0, "id": 1}
    ).to_list(50000)
    client_ids = [row.get("id") for row in client_docs if row.get("id")]

    if not client_ids:
        return {
            "organisation_id": org_id,
            "period": period,
            "currency": "BWP",
            "total_bookings": 0,
            "billable_bookings": 0,
            "invoiced_bookings": 0,
            "estimated_total": 0.0,
            "bookings": [],
        }

    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    if period == "current_month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == "previous_month":
        this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = this_month - timedelta(seconds=1)
        start = end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "quarter":
        quarter_start_month = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    else:
        start = None
        end = None

    query: Dict[str, Any] = {"client_id": {"$in": client_ids}}
    if start is not None and end is not None:
        query["starts_at"] = {"$gte": start.isoformat(), "$lte": end.isoformat()}

    bookings = await db.bookings.find(
        query,
        {
            "_id": 0,
            "id": 1,
            "session_type": 1,
            "session_mode": 1,
            "starts_at": 1,
            "status": 1,
            "cancellation_billing_status": 1,
            "active_invoice_id": 1,
        }
    ).sort("starts_at", -1).to_list(50000)

    org = await db.organisations.find_one({"id": org_id}, {"_id": 0}) or {}
    rates = {
        "individual": float(org.get("rate_individual") if org.get("rate_individual") is not None else 400),
        "couple": float(org.get("rate_couple") if org.get("rate_couple") is not None else 500),
        "family": float(org.get("rate_family") if org.get("rate_family") is not None else 600),
    }
    currency = str(org.get("billing_currency") or "BWP").upper()

    invoice_ids = list({b.get("active_invoice_id") for b in bookings if b.get("active_invoice_id")})
    invoice_map = {}
    if invoice_ids:
        invoice_docs = await db.invoices.find(
            {"id": {"$in": invoice_ids}, "organisation_id": org_id},
            {"_id": 0, "id": 1, "invoice_number": 1, "status": 1}
        ).to_list(50000)
        invoice_map = {row.get("id"): row for row in invoice_docs if row.get("id")}

    service_mapping_docs = await db.scheduling_service_mappings.find(
        {"provider": "setmore", "funding_scope": "organisation"},
        {"_id": 0, "session_type": 1, "session_mode": 1, "service_name": 1}
    ).to_list(100)
    service_name_map = {
        (str(row.get("session_type") or ""), str(row.get("session_mode") or "")): str(row.get("service_name") or "")
        for row in service_mapping_docs
        if row.get("session_type") and row.get("session_mode") and row.get("service_name")
    }
    eap_service_fallbacks = {
        ("individual", "virtual"): "EAP- Virtual Counselling",
        ("individual", "in_person"): "EAP- One-on-one in person counselling",
        ("couple", "virtual"): "EAP- Counselling for Couples",
        ("couple", "in_person"): "EAP- Counselling for Couples",
        ("family", "virtual"): "EAP- Family Counselling",
        ("family", "in_person"): "EAP- Family Counselling",
    }

    safe_rows = []
    billable_count = 0
    invoiced_count = 0
    estimated_total = 0.0
    for booking in bookings:
        booking_id = str(booking.get("id") or "")
        session_type = str(booking.get("session_type") or "individual")
        booking_status = str(booking.get("status") or "")
        billable = (
            booking_status in ["completed", "late_cancelled_billable"]
            or booking.get("cancellation_billing_status") == "billable"
        )
        unit_rate = rates.get(session_type, 0.0) if billable else 0.0
        invoice = invoice_map.get(booking.get("active_invoice_id"))

        if billable:
            billable_count += 1
            estimated_total += unit_rate
        if invoice:
            invoiced_count += 1

        starts_at = str(booking.get("starts_at") or "")
        session_mode = str(booking.get("session_mode") or "")
        service_name = (
            service_name_map.get((session_type, session_mode))
            or eap_service_fallbacks.get((session_type, session_mode))
            or f"EAP- {session_type.replace('_', ' ').title()} Counselling"
        )
        safe_rows.append({
            "booking_reference": f"FCA-{booking_id[-8:].upper()}" if booking_id else "FCA-UNKNOWN",
            "booking_date": starts_at[:10] if len(starts_at) >= 10 else None,
            "service_name": service_name,
            "session_type": session_type,
            "session_mode": session_mode,
            "status": booking_status,
            "billable": billable,
            "unit_rate": unit_rate,
            "currency": currency,
            "invoice_number": invoice.get("invoice_number") if invoice else None,
            "invoice_status": invoice.get("status") if invoice else "not_invoiced",
        })

    await AuditService.log_activity(
        db,
        action="hr_booking_ledger_viewed",
        actor_user_id=user["user_id"],
        actor_name=user["name"],
        metadata={"organisation_id": org_id, "period": period, "rows": len(safe_rows)}
    )

    return {
        "organisation_id": org_id,
        "period": period,
        "currency": currency,
        "total_bookings": len(safe_rows),
        "billable_bookings": billable_count,
        "invoiced_bookings": invoiced_count,
        "estimated_total": round(estimated_total, 2),
        "bookings": safe_rows,
        "privacy_notice": (
            "Accounts-only reconciliation view. Employee identities, therapist identities, "
            "clinical reasons, intake information and notes are never included."
        ),
    }
