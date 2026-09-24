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
from services.corporate_entitlement_service import CorporateEntitlementService, ENTITLEMENT_STATUSES

class HRPrivacyService:
    """
    Aggregate reporting helper.

    The HR portal still exposes aggregate-only organisation reporting, but exact
    aggregate counts are returned at every volume. Employee identity, clinical
    details, intake answers, therapist identity and cross-tenant data remain
    outside the HR reporting boundary.
    """

    @staticmethod
    def mask_single_metric(
        count: int,
        threshold: int = HR_MIN_REPORTING_COUNT,
        total: Optional[int] = None
    ) -> AggregateMetric:
        pct = round((count / total) * 100, 1) if (total and total > 0) else (0.0 if count == 0 and total else None)
        return AggregateMetric(
            count=count,
            display=str(count),
            percentage=pct,
            suppressed=False,
        )

    @staticmethod
    def apply_breakdown_suppression(
        raw_counts: Dict[str, int],
        total: int,
        threshold: int = HR_MIN_REPORTING_COUNT,
        category_type: str = "general"
    ) -> Tuple[Dict[str, AggregateMetric], bool]:
        result: Dict[str, AggregateMetric] = {}
        for key, value in raw_counts.items():
            pct = round((value / total) * 100, 1) if total > 0 else None
            result[key] = AggregateMetric(
                count=value,
                display=str(value),
                percentage=pct,
                suppressed=False,
            )
        return result, True


# Backwards compatibility alias
mask_metric = HRPrivacyService.mask_single_metric


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
        if not doc:
            return None
        pool = await CorporateEntitlementService.organisation_pool_summary(db, org_id)
        doc["allocated_sessions"] = pool["allocated_sessions"]
        return Organisation(**doc)

    @staticmethod
    async def list_organisations(db: AsyncIOMotorDatabase) -> List[Organisation]:
        docs = await db.organisations.find({}, {"_id": 0}).sort("name", 1).to_list(100)
        result: List[Organisation] = []
        for doc in docs:
            pool = await CorporateEntitlementService.organisation_pool_summary(db, doc["id"])
            doc["allocated_sessions"] = pool["allocated_sessions"]
            result.append(Organisation(**doc))
        return result

    @staticmethod
    async def update_organisation(db: AsyncIOMotorDatabase, org_id: str, payload: OrganisationUpdate) -> Optional[Organisation]:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            return await HRReportingService.get_organisation(db, org_id)
        updates["updated_at"] = now_iso()
        await db.organisations.update_one({"id": org_id}, {"$set": updates})
        return await HRReportingService.get_organisation(db, org_id)

    @staticmethod
    async def create_organisation_user(
        db: AsyncIOMotorDatabase,
        org_id: str,
        payload: OrganisationUserCreate,
        password_hash: Optional[str] = None
    ) -> OrganisationUser:
        org_user = OrganisationUser(
            organisation_id=org_id,
            user_id=payload.username.strip().lower(),
            email=payload.email.strip().lower(),
            name=payload.name.strip(),
            role=payload.role,
            password_hash=password_hash,
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

        # Apply Centralized Privacy Engine
        total_sessions_metric = HRPrivacyService.mask_single_metric(total_sessions, threshold)

        attendance_metrics, att_avail = HRPrivacyService.apply_breakdown_suppression(
            {"completed": completed, "cancelled": cancelled, "no_show": no_show},
            total=total_sessions,
            threshold=threshold,
            category_type="attendance"
        )

        type_metrics, types_avail = HRPrivacyService.apply_breakdown_suppression(
            {"individual": individual_count, "couple": couple_count, "family": family_count},
            total=total_sessions,
            threshold=threshold,
            category_type="types"
        )

        mode_metrics, modes_avail = HRPrivacyService.apply_breakdown_suppression(
            {"in_person": in_person_count, "virtual": virtual_count},
            total=total_sessions,
            threshold=threshold,
            category_type="modes"
        )

        # Contract overview
        contract = await HRReportingService.get_contract_status(db, org_id)

        detailed_avail = att_avail or types_avail or modes_avail

        return HRDashboardResponse(
            organisation_id=org_id,
            organisation_name=org_name,
            period=period_label,
            total_sessions=total_sessions_metric,
            completed=attendance_metrics["completed"],
            cancelled=attendance_metrics["cancelled"],
            no_show=attendance_metrics["no_show"],
            session_types=type_metrics,
            session_modes=mode_metrics,
            contract=contract,
            detailed_breakdown_available=detailed_avail,
            privacy_notice="Exact aggregate utilisation counts are shown. Individual employee records, counselling reasons, intake answers, therapist identities, and clinical information remain confidential."
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
        query: Dict[str, Any] = {
            "client_id": {"$in": client_ids},
            "status": {"$in": ENTITLEMENT_STATUSES}
        }
        if org.contract_start and org.contract_end:
            query["starts_at"] = {
                "$gte": f"{org.contract_start}T00:00:00",
                "$lte": f"{org.contract_end}T23:59:59"
            }

        sessions_used = await db.bookings.count_documents(query)
        pool = await CorporateEntitlementService.organisation_pool_summary(db, org_id)
        allocated = pool["allocated_sessions"]
        remaining = max(0, allocated - sessions_used)
        utilisation_pct = round((sessions_used / allocated) * 100, 1) if allocated > 0 else None

        return HRContractStatus(
            organisation_id=org.id,
            organisation_name=org.name,
            contract_status=org.status,
            contract_start=org.contract_start,
            contract_end=org.contract_end,
            allocated_sessions=allocated,
            member_count=pool["member_count"],
            base_sessions_per_member=4,
            approved_extra_sessions=pool["approved_extra_sessions"],
            sessions_used=sessions_used,
            sessions_remaining=remaining,
            utilisation_percentage=utilisation_pct,
            is_configured=pool["member_count"] > 0
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
                period_key = dt_str[:7]
            else:
                period_key = "Other"
            
            if period_key not in trend_buckets:
                trend_buckets[period_key] = {"total": 0, "completed": 0, "cancelled": 0, "no_show": 0}
            
            trend_buckets[period_key]["total"] += 1
            st = b.get("status")
            if st in ["completed", "cancelled", "no_show"]:
                trend_buckets[period_key][st] += 1

        sorted_periods = sorted(trend_buckets.keys())
        period_totals = {p: trend_buckets[p]["total"] for p in sorted_periods}
        overall_total = sum(period_totals.values())

        period_metrics = {
            period_key: HRPrivacyService.mask_single_metric(period_total, threshold)
            for period_key, period_total in period_totals.items()
        }

        points = []
        for period_key in sorted_periods:
            data = trend_buckets[period_key]
            p_total = data["total"]
            p_total_metric = period_metrics.get(period_key) or HRPrivacyService.mask_single_metric(p_total, threshold)
            att_metrics, _ = HRPrivacyService.apply_breakdown_suppression(
                {
                    "completed": data["completed"],
                    "cancelled": data["cancelled"],
                    "no_show": data["no_show"],
                },
                total=p_total,
                threshold=threshold,
                category_type="attendance",
            )

            points.append({
                "period": period_key,
                "total_sessions": p_total_metric.model_dump(),
                "completed": att_metrics["completed"].model_dump(),
                "cancelled": att_metrics["cancelled"].model_dump(),
                "no_show": att_metrics["no_show"].model_dump()
            })

        return {
            "organisation_id": org_id,
            "organisation_name": org.name if org else "Corporate Client",
            "granularity": granularity,
            "trends": points,
            "privacy_notice": "Exact aggregate monthly utilisation counts are shown. Individual employee and clinical records remain confidential."
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

        type_metrics, breakdown_avail = HRPrivacyService.apply_breakdown_suppression(
            {"individual": ind_count, "couple": cpl_count, "family": fam_count},
            total=total,
            threshold=threshold,
            category_type="types"
        )

        return {
            "organisation_id": org_id,
            "total_sessions": HRPrivacyService.mask_single_metric(total, threshold).model_dump(),
            "detailed_breakdown_available": breakdown_avail,
            "types": {
                k: {
                    "metric": m.model_dump(),
                    "percentage": m.percentage
                }
                for k, m in type_metrics.items()
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

        mode_metrics, breakdown_avail = HRPrivacyService.apply_breakdown_suppression(
            {"in_person": in_person_count, "virtual": virtual_count},
            total=total,
            threshold=threshold,
            category_type="modes"
        )

        return {
            "organisation_id": org_id,
            "total_sessions": HRPrivacyService.mask_single_metric(total, threshold).model_dump(),
            "detailed_breakdown_available": breakdown_avail,
            "modes": {
                k: {
                    "metric": m.model_dump(),
                    "percentage": m.percentage
                }
                for k, m in mode_metrics.items()
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
        Generates aggregate-only CSV export with exact aggregate counts.
        Individual employee and clinical records are never included.
        """
        trends_data = await HRReportingService.get_utilisation_trends(db, org_id, threshold=threshold)
        lines = ["Period,Total Sessions,Completed,Cancelled,No Show"]
        for pt in trends_data.get("trends", []):
            lines.append(f"{pt['period']},{pt['total_sessions']['display']},{pt['completed']['display']},{pt['cancelled']['display']},{pt['no_show']['display']}")
        return "\n".join(lines)
