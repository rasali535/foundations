import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from models import (
    Organisation, OrganisationCreate, OrganisationUpdate,
    OrganisationUser, OrganisationUserCreate,
    AggregateMetric, HRContractStatus, HRDashboardResponse,
    HR_MIN_REPORTING_COUNT, now_iso
)

def mask_metric(count: int, threshold: int = HR_MIN_REPORTING_COUNT) -> AggregateMetric:
    """
    Applies privacy-preserving threshold suppression.
    If 0 < count < threshold, the exact count is masked with '<{threshold}'.
    Zero counts and counts >= threshold are safe to display.
    """
    if count == 0:
        return AggregateMetric(count=0, display="0", suppressed=False)
    if 0 < count < threshold:
        return AggregateMetric(count=None, display=f"<{threshold}", suppressed=True)
    return AggregateMetric(count=count, display=str(count), suppressed=False)


class HRReportingService:
    # ==================== Organisation Management ====================
    @staticmethod
    async def create_organisation(db: AsyncIOMotorDatabase, payload: OrganisationCreate) -> Organisation:
        org = Organisation(**payload.model_dump())
        await db.organisations.insert_one(org.model_dump())
        return org

    @staticmethod
    async def get_organisation(db: AsyncIOMotorDatabase, org_id: str) -> Optional[Organisation]:
        doc = await db.organisations.find_one({"id": org_id}, {"_id": 0})
        return Organisation(**doc) if doc else None

    @staticmethod
    async def list_organisations(db: AsyncIOMotorDatabase) -> List[Organisation]:
        docs = await db.organisations.find({}, {"_id": 0}).sort("name", 1).to_list(100)
        return [Organisation(**d) for d in docs]

    @staticmethod
    async def update_organisation(db: AsyncIOMotorDatabase, org_id: str, payload: OrganisationUpdate) -> Optional[Organisation]:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            return await HRReportingService.get_organisation(db, org_id)
        updates["updated_at"] = now_iso()
        await db.organisations.update_one({"id": org_id}, {"$set": updates})
        return await HRReportingService.get_organisation(db, org_id)

    @staticmethod
    async def create_organisation_user(db: AsyncIOMotorDatabase, org_id: str, payload: OrganisationUserCreate) -> OrganisationUser:
        org_user = OrganisationUser(
            organisation_id=org_id,
            user_id=payload.username.strip().lower(),
            email=payload.email.strip().lower(),
            name=payload.name.strip(),
            role=payload.role,
            active=True
        )
        await db.organisation_users.insert_one(org_user.model_dump())
        return org_user

    @staticmethod
    async def list_organisation_users(db: AsyncIOMotorDatabase, org_id: str) -> List[OrganisationUser]:
        docs = await db.organisation_users.find({"organisation_id": org_id}, {"_id": 0}).to_list(100)
        return [OrganisationUser(**d) for d in docs]

    # ==================== Safe Aggregate Query Helpers ====================
    @staticmethod
    async def _get_org_client_ids(db: AsyncIOMotorDatabase, org_id: str) -> List[str]:
        """Resolves internal CRM client IDs associated with this corporate organisation."""
        client_ids = await db.crm_clients.distinct("id", {"organisation_id": org_id})
        return client_ids

    @staticmethod
    def _resolve_period_dates(period: str, custom_start: Optional[str] = None, custom_end: Optional[str] = None) -> Tuple[Optional[str], Optional[str], str]:
        now = datetime.now(timezone.utc)
        if period == "current_month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
            # end of month
            next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = next_month.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
            return start, end, now.strftime("%B %Y")
        elif period == "previous_month":
            first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_prev_month = first_this_month - timedelta(days=1)
            start = last_prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
            end = last_prev_month.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
            return start, end, last_prev_month.strftime("%B %Y")
        elif period == "quarter":
            quarter = (now.month - 1) // 3 + 1
            start_month = (quarter - 1) * 3 + 1
            start = now.replace(month=start_month, day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
            end = now.isoformat()
            return start, end, f"Q{quarter} {now.year}"
        elif period == "year":
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
            end = now.replace(month=12, day=31, hour=23, minute=59, second=59).isoformat()
            return start, end, f"Year {now.year}"
        elif period == "custom" and custom_start and custom_end:
            return custom_start, custom_end, f"{custom_start[:10]} to {custom_end[:10]}"
        return None, None, "All Time"

    # ==================== Aggregate Dashboard ====================
    @staticmethod
    async def get_dashboard(
        db: AsyncIOMotorDatabase,
        org_id: str,
        period: str = "current_month",
        threshold: int = HR_MIN_REPORTING_COUNT
    ) -> HRDashboardResponse:
        org = await HRReportingService.get_organisation(db, org_id)
        org_name = org.name if org else "Corporate Client"

        start_dt, end_dt, period_label = HRReportingService._resolve_period_dates(period)
        client_ids = await HRReportingService._get_org_client_ids(db, org_id)

        # Build booking query
        query: Dict[str, Any] = {"client_id": {"$in": client_ids}}
        if start_dt and end_dt:
            query["starts_at"] = {"$gte": start_dt, "$lte": end_dt}

        bookings = await db.bookings.find(query, {"_id": 0}).to_list(10000)

        # Aggregation counters
        total_sessions = len(bookings)
        completed = sum(1 for b in bookings if b.get("status") == "completed")
        cancelled = sum(1 for b in bookings if b.get("status") == "cancelled")
        no_show = sum(1 for b in bookings if b.get("status") == "no_show")

        # Session type distribution
        individual_count = sum(1 for b in bookings if b.get("session_type") == "individual")
        couple_count = sum(1 for b in bookings if b.get("session_type") == "couple")
        family_count = sum(1 for b in bookings if b.get("session_type") == "family")

        # Session mode distribution
        in_person_count = sum(1 for b in bookings if b.get("session_mode") == "in_person")
        virtual_count = sum(1 for b in bookings if b.get("session_mode") == "virtual")

        # Contract overview
        contract = await HRReportingService.get_contract_status(db, org_id)

        return HRDashboardResponse(
            organisation_id=org_id,
            organisation_name=org_name,
            period=period_label,
            total_sessions=mask_metric(total_sessions, threshold),
            completed=mask_metric(completed, threshold),
            cancelled=mask_metric(cancelled, threshold),
            no_show=mask_metric(no_show, threshold),
            session_types={
                "individual": mask_metric(individual_count, threshold),
                "couple": mask_metric(couple_count, threshold),
                "family": mask_metric(family_count, threshold),
            },
            session_modes={
                "in_person": mask_metric(in_person_count, threshold),
                "virtual": mask_metric(virtual_count, threshold),
            },
            contract=contract,
            privacy_notice=f"All counts below the privacy threshold ({threshold}) are masked to safeguard employee anonymity."
        )

    # ==================== Contract Overview ====================
    @staticmethod
    async def get_contract_status(db: AsyncIOMotorDatabase, org_id: str) -> HRContractStatus:
        org = await HRReportingService.get_organisation(db, org_id)
        if not org:
            return HRContractStatus(
                organisation_id=org_id,
                organisation_name="Unknown Organisation",
                contract_status="inactive",
                sessions_used=0,
                is_configured=False
            )

        client_ids = await HRReportingService._get_org_client_ids(db, org_id)
        # Contract session utilisation counts completed or confirmed sessions
        query: Dict[str, Any] = {
            "client_id": {"$in": client_ids},
            "status": {"$in": ["completed", "confirmed"]}
        }
        if org.contract_start and org.contract_end:
            query["starts_at"] = {"$gte": f"{org.contract_start}T00:00:00Z", "$lte": f"{org.contract_end}T23:59:59Z"}

        sessions_used = await db.bookings.count_documents(query)
        allocated = org.allocated_sessions
        remaining = max(0, allocated - sessions_used) if allocated is not None else None
        utilisation_pct = round((sessions_used / allocated) * 100, 1) if allocated and allocated > 0 else None

        return HRContractStatus(
            organisation_id=org.id,
            organisation_name=org.name,
            contract_status=org.status,
            contract_start=org.contract_start,
            contract_end=org.contract_end,
            allocated_sessions=allocated,
            sessions_used=sessions_used,
            sessions_remaining=remaining,
            utilisation_percentage=utilisation_pct,
            is_configured=allocated is not None
        )

    # ==================== Utilisation Reporting & Trends ====================
    @staticmethod
    async def get_utilisation_trends(
        db: AsyncIOMotorDatabase,
        org_id: str,
        granularity: str = "monthly",
        threshold: int = HR_MIN_REPORTING_COUNT
    ) -> Dict[str, Any]:
        client_ids = await HRReportingService._get_org_client_ids(db, org_id)
        org = await HRReportingService.get_organisation(db, org_id)

        bookings = await db.bookings.find({"client_id": {"$in": client_ids}}, {"_id": 0}).sort("starts_at", 1).to_list(10000)

        # Aggregate by period key (e.g. YYYY-MM)
        trend_buckets: Dict[str, Dict[str, int]] = {}
        for b in bookings:
            dt_str = b.get("starts_at", "")
            if len(dt_str) >= 7:
                period_key = dt_str[:7]  # "2026-09"
            else:
                period_key = "Other"
            
            if period_key not in trend_buckets:
                trend_buckets[period_key] = {"total": 0, "completed": 0, "cancelled": 0, "no_show": 0}
            
            trend_buckets[period_key]["total"] += 1
            st = b.get("status")
            if st in ["completed", "cancelled", "no_show"]:
                trend_buckets[period_key][st] += 1

        points = []
        for period_key in sorted(trend_buckets.keys()):
            data = trend_buckets[period_key]
            points.append({
                "period": period_key,
                "total_sessions": mask_metric(data["total"], threshold).model_dump(),
                "completed": mask_metric(data["completed"], threshold).model_dump(),
                "cancelled": mask_metric(data["cancelled"], threshold).model_dump(),
                "no_show": mask_metric(data["no_show"], threshold).model_dump()
            })

        return {
            "organisation_id": org_id,
            "organisation_name": org.name if org else "Corporate Client",
            "granularity": granularity,
            "trends": points,
            "privacy_notice": f"Individual monthly buckets with fewer than {threshold} sessions are masked for privacy."
        }

    # ==================== Session Type & Mode Aggregates ====================
    @staticmethod
    async def get_session_types_breakdown(
        db: AsyncIOMotorDatabase,
        org_id: str,
        threshold: int = HR_MIN_REPORTING_COUNT
    ) -> Dict[str, Any]:
        client_ids = await HRReportingService._get_org_client_ids(db, org_id)
        bookings = await db.bookings.find({"client_id": {"$in": client_ids}}, {"_id": 0}).to_list(10000)

        total = len(bookings)
        ind_count = sum(1 for b in bookings if b.get("session_type") == "individual")
        cpl_count = sum(1 for b in bookings if b.get("session_type") == "couple")
        fam_count = sum(1 for b in bookings if b.get("session_type") == "family")

        ind_metric = mask_metric(ind_count, threshold)
        cpl_metric = mask_metric(cpl_count, threshold)
        fam_metric = mask_metric(fam_count, threshold)

        return {
            "organisation_id": org_id,
            "total_sessions": mask_metric(total, threshold).model_dump(),
            "types": {
                "individual": {
                    "metric": ind_metric.model_dump(),
                    "percentage": round((ind_count / total) * 100, 1) if total > 0 and not ind_metric.suppressed else None
                },
                "couple": {
                    "metric": cpl_metric.model_dump(),
                    "percentage": round((cpl_count / total) * 100, 1) if total > 0 and not cpl_metric.suppressed else None
                },
                "family": {
                    "metric": fam_metric.model_dump(),
                    "percentage": round((fam_count / total) * 100, 1) if total > 0 and not fam_metric.suppressed else None
                }
            }
        }

    @staticmethod
    async def get_session_modes_breakdown(
        db: AsyncIOMotorDatabase,
        org_id: str,
        threshold: int = HR_MIN_REPORTING_COUNT
    ) -> Dict[str, Any]:
        client_ids = await HRReportingService._get_org_client_ids(db, org_id)
        bookings = await db.bookings.find({"client_id": {"$in": client_ids}}, {"_id": 0}).to_list(10000)

        total = len(bookings)
        in_person_count = sum(1 for b in bookings if b.get("session_mode") == "in_person")
        virtual_count = sum(1 for b in bookings if b.get("session_mode") == "virtual")

        ip_metric = mask_metric(in_person_count, threshold)
        v_metric = mask_metric(virtual_count, threshold)

        return {
            "organisation_id": org_id,
            "total_sessions": mask_metric(total, threshold).model_dump(),
            "modes": {
                "in_person": {
                    "metric": ip_metric.model_dump(),
                    "percentage": round((in_person_count / total) * 100, 1) if total > 0 and not ip_metric.suppressed else None
                },
                "virtual": {
                    "metric": v_metric.model_dump(),
                    "percentage": round((virtual_count / total) * 100, 1) if total > 0 and not v_metric.suppressed else None
                }
            }
        }

    # ==================== Safe Aggregate CSV Export ====================
    @staticmethod
    async def generate_safe_aggregate_csv(
        db: AsyncIOMotorDatabase,
        org_id: str,
        threshold: int = HR_MIN_REPORTING_COUNT
    ) -> str:
        """
        Generates aggregate-only CSV export.
        NEVER contains client names, emails, phones, or individual appointments.
        """
        trends_data = await HRReportingService.get_utilisation_trends(db, org_id, threshold=threshold)
        lines = ["Period,Total Sessions,Completed,Cancelled,No Show"]
        for pt in trends_data.get("trends", []):
            lines.append(f"{pt['period']},{pt['total_sessions']['display']},{pt['completed']['display']},{pt['cancelled']['display']},{pt['no_show']['display']}")
        return "\n".join(lines)
