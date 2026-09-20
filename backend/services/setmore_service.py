import asyncio
import os
import time
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import requests
from motor.motor_asyncio import AsyncIOMotorDatabase


TOKEN_URL = "https://developer.setmore.com/api/v1/o/oauth2/token"
API_BASE = "https://developer.setmore.com/api/v1/bookingapi"
_TOKEN: Dict[str, Any] = {"value": None, "expires_at": 0.0}
_TOKEN_LOCK = asyncio.Lock()


class SetmoreError(RuntimeError):
    pass


class SetmoreService:
    @staticmethod
    def configured() -> bool:
        return bool((os.environ.get("SETMORE_REFRESH_TOKEN") or "").strip())

    @staticmethod
    def timezone() -> str:
        return (os.environ.get("SETMORE_TIMEZONE") or "Africa/Gaborone").strip()

    @staticmethod
    async def _json_request(method: str, url: str, **kwargs) -> Dict[str, Any]:
        def run():
            response = requests.request(method, url, timeout=20, **kwargs)
            response.raise_for_status()
            return response.json()
        try:
            payload = await asyncio.to_thread(run)
        except Exception as exc:
            raise SetmoreError(f"Setmore request failed: {exc.__class__.__name__}") from exc
        if not isinstance(payload, dict) or payload.get("response") is False:
            raise SetmoreError("Setmore returned an unsuccessful response")
        return payload

    @classmethod
    async def access_token(cls) -> str:
        if _TOKEN["value"] and time.time() < float(_TOKEN["expires_at"] or 0):
            return str(_TOKEN["value"])
        async with _TOKEN_LOCK:
            if _TOKEN["value"] and time.time() < float(_TOKEN["expires_at"] or 0):
                return str(_TOKEN["value"])
            refresh = (os.environ.get("SETMORE_REFRESH_TOKEN") or "").strip()
            if not refresh:
                raise SetmoreError("SETMORE_REFRESH_TOKEN is not configured")
            payload = await cls._json_request("GET", TOKEN_URL, params={"refreshToken": refresh})
            token = (((payload.get("data") or {}).get("token")) or {})
            value = token.get("access_token")
            if not value:
                raise SetmoreError("Setmore token exchange returned no access token")
            expires_in = max(int(token.get("expires_in") or 3600), 120)
            _TOKEN.update(value=value, expires_at=time.time() + expires_in - 60)
            return str(value)

    @classmethod
    async def _api(cls, method: str, path: str, **kwargs) -> Dict[str, Any]:
        token = await cls.access_token()
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["Authorization"] = f"Bearer {token}"
        headers.setdefault("Content-Type", "application/json")
        return await cls._json_request(method, f"{API_BASE}{path}", headers=headers, **kwargs)

    @classmethod
    async def staffs(cls) -> List[Dict[str, Any]]:
        payload = await cls._api("GET", "/staffs")
        data = payload.get("data") or {}
        rows = data.get("staffs") or data.get("staff") or []
        return rows if isinstance(rows, list) else []

    @classmethod
    async def services(cls) -> List[Dict[str, Any]]:
        payload = await cls._api("GET", "/services")
        data = payload.get("data") or {}
        rows = data.get("services") or data.get("service") or []
        return rows if isinstance(rows, list) else []

    @classmethod
    async def service_categories(cls) -> List[Dict[str, Any]]:
        payload = await cls._api("GET", "/services/categories")
        data = payload.get("data") or {}
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []
        for key in (
            "categories",
            "category",
            "service_categories",
            "service_category",
            "category_list",
            "categoryList",
        ):
            rows = data.get(key)
            if isinstance(rows, list):
                return rows
            if isinstance(rows, dict):
                return [rows]
        # Be tolerant of Setmore response-shape drift: if data contains exactly
        # one list of objects, treat that list as the category collection.
        object_lists = [
            value for value in data.values()
            if isinstance(value, list) and all(isinstance(item, dict) for item in value)
        ]
        return object_lists[0] if len(object_lists) == 1 else []

    @classmethod
    async def services_for_category(cls, category_key: str) -> List[Dict[str, Any]]:
        payload = await cls._api("GET", f"/services/categories/{category_key}")
        data = payload.get("data") or {}
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []
        for key in ("services", "service", "service_list", "serviceList"):
            rows = data.get(key)
            if isinstance(rows, list):
                return rows
            if isinstance(rows, dict):
                return [rows]
        object_lists = [
            value for value in data.values()
            if isinstance(value, list) and all(isinstance(item, dict) for item in value)
        ]
        return object_lists[0] if len(object_lists) == 1 else []

    @staticmethod
    def _key(row: Dict[str, Any]) -> Optional[str]:
        value = (
            row.get("key")
            or row.get("staff_key")
            or row.get("service_key")
            or row.get("category_key")
            or row.get("categoryKey")
        )
        return str(value) if value else None

    @classmethod
    async def resolve_staff_key(cls, db: AsyncIOMotorDatabase, therapist_id: str) -> str:
        therapist = await db.therapists.find_one({"id": therapist_id}, {"_id": 0})
        if not therapist:
            raise SetmoreError("FCA therapist was not found")
        explicit = therapist.get("setmore_staff_key")
        email = str(therapist.get("email") or "").strip().lower()
        name = str(therapist.get("name") or "").strip().lower()
        rows = await cls.staffs()

        # Revalidate persisted staff mappings against Setmore instead of trusting
        # them forever. A stale staff key can otherwise yield a valid 200 response
        # with no slots and look indistinguishable from "fully booked".
        if explicit:
            explicit_key = str(explicit)
            if any(cls._key(row) == explicit_key for row in rows):
                logging.warning(
                    "SETMORE_TRACE stage=staff_selected source=stored staff_count=%s",
                    len(rows),
                )
                return explicit_key
            logging.warning(
                "SETMORE_TRACE stage=staff_stale staff_count=%s",
                len(rows),
            )

        matches = []
        for row in rows:
            row_email = str(row.get("email") or row.get("email_id") or "").strip().lower()
            row_name = " ".join(str(row.get(k) or "").strip() for k in ("first_name", "last_name")).strip().lower()
            if (email and row_email == email) or (name and row_name == name):
                matches.append(row)
        if not matches and len(rows) == 1:
            matches = rows
        if len(matches) != 1 or not cls._key(matches[0]):
            raise SetmoreError("Setmore staff mapping is missing or ambiguous")
        key = cls._key(matches[0])
        await db.therapists.update_one({"id": therapist_id}, {"$set": {"setmore_staff_key": key}})
        logging.warning(
            "SETMORE_TRACE stage=staff_selected source=resolved staff_count=%s",
            len(rows),
        )
        return str(key)

    @classmethod
    async def resolve_service_key(cls, db: AsyncIOMotorDatabase, session_type: str, session_mode: str) -> str:
        mapping = await db.scheduling_service_mappings.find_one(
            {"provider": "setmore", "session_type": session_type, "session_mode": session_mode},
            {"_id": 0},
        )
        mapped_key = str(mapping.get("service_key")) if mapping and mapping.get("service_key") else None

        rows = await cls.services()
        if not rows:
            raise SetmoreError("Setmore returned no active services")

        def norm(value: Any) -> str:
            return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

        type_aliases = {
            # Keep these aliases specific to the session type. Generic values such
            # as "counselling" make Individual/Couples/Family categories all match
            # at once and cause an ambiguous Setmore service resolution.
            "individual": {"individual", "individual counselling", "individual counseling"},
            "couple": {"couple", "couples", "couple counselling", "couples counselling", "couple counseling", "couples counseling"},
            "family": {"family", "family counselling", "family counseling"},
        }
        mode_aliases = {
            "in_person": {"in person", "inperson", "face to face", "physical", "office"},
            "virtual": {"virtual", "online", "remote", "video"},
        }
        wanted_types = {norm(v) for v in type_aliases.get(session_type, {session_type})}
        wanted_modes = {norm(v) for v in mode_aliases.get(session_mode, {session_mode})}

        scored = []
        safe_titles = []

        # Setmore accounts can model FCA's session type as a service category
        # (Individual/Couples/Family) and the mode as the service name
        # (In Person/Virtual). Build a category lookup so both layouts work.
        try:
            category_rows = await cls.service_categories()
        except Exception:
            category_rows = []
        category_names: Dict[str, str] = {}
        for category in category_rows:
            category_key = cls._key(category)
            category_name = norm(
                category.get("category_name")
                or category.get("categoryName")
                or category.get("name")
                or category.get("title")
                or category.get("label")
            )
            if category_key and category_name:
                category_names[str(category_key)] = category_name

        def service_title(row: Dict[str, Any]) -> str:
            return norm(
                row.get("service_name")
                or row.get("name")
                or row.get("title")
                or row.get("label")
                or row.get("display_name")
            )

        def service_category(row: Dict[str, Any]) -> str:
            direct = norm(
                row.get("category_name")
                or row.get("categoryName")
                or row.get("category")
                or row.get("category_title")
                or row.get("categoryTitle")
            )
            if direct:
                return direct
            category_key = row.get("category_key") or row.get("categoryKey")
            return category_names.get(str(category_key), "") if category_key else ""

        for row in rows:
            title = service_title(row)
            category = service_category(row)
            if not title or not cls._key(row):
                continue
            descriptor = " ".join(part for part in (category, title) if part)
            safe_titles.append(descriptor[:100])
            type_score = max(
                (4 if category == alias else 3 if alias in category else 2 if alias in descriptor else 0)
                for alias in wanted_types
            )
            mode_score = max(
                (3 if title == alias else 2 if alias in title else 1 if alias in descriptor else 0)
                for alias in wanted_modes
            )
            if type_score:
                scored.append((type_score + mode_score, mode_score, row))

        mapped_row = next((row for row in rows if cls._key(row) == mapped_key), None) if mapped_key else None

        if scored:
            scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
            best_score = scored[0][0]
            best_mode_score = scored[0][1]
            best = [item[2] for item in scored if item[0] == best_score and item[1] == best_mode_score]
            if len(best) == 1:
                matches = best
            elif mapped_row in best:
                matches = [mapped_row]
            else:
                matches = []
        else:
            # If the flat service list exposes only mode names, resolve through
            # Setmore's service-category endpoints.
            matching_categories = []
            scored_categories = []
            for category in category_rows:
                category_name = norm(
                    category.get("category_name")
                    or category.get("categoryName")
                    or category.get("name")
                    or category.get("title")
                    or category.get("label")
                )
                if not category_name:
                    continue
                category_score = max(
                    (3 if category_name == alias else 2 if category_name.startswith(alias + " ") else 1 if alias in category_name else 0)
                    for alias in wanted_types
                )
                category_key = cls._key(category)
                if category_key and category_score:
                    scored_categories.append((category_score, str(category_key), category_name))

            if scored_categories:
                best_category_score = max(item[0] for item in scored_categories)
                matching_categories = [
                    (category_key, category_name)
                    for score, category_key, category_name in scored_categories
                    if score == best_category_score
                ]

            category_matches = []
            for category_key, category_name in matching_categories:
                try:
                    category_services = await cls.services_for_category(category_key)
                except Exception:
                    category_services = []
                for row in category_services:
                    title = service_title(row)
                    if not title or not cls._key(row):
                        continue
                    mode_score = max(
                        (3 if title == alias else 2 if alias in title else 0)
                        for alias in wanted_modes
                    )
                    if mode_score:
                        safe_titles.append(f"{category_name} {title}"[:100])
                        category_matches.append((mode_score, row))

            if category_matches:
                category_matches.sort(key=lambda item: item[0], reverse=True)
                best_mode = category_matches[0][0]
                best = [row for score, row in category_matches if score == best_mode]
                matches = best if len(best) == 1 else []
            elif mapped_row is not None:
                # Keep an existing valid mapping only when no better FCA-specific
                # service exists.
                matches = [mapped_row]
            else:
                # Fresh Setmore accounts commonly start with generic duration services.
                hour_aliases = {"1 hour meeting", "60 minute meeting", "60 minutes meeting", "1 hour"}
                hour_matches = [
                    row for row in rows
                    if service_title(row) in hour_aliases and cls._key(row)
                ]
                if len(hour_matches) == 1:
                    matches = hour_matches
                elif len(rows) == 1 and cls._key(rows[0]):
                    matches = rows
                else:
                    matches = []

        logging.warning(
            "SETMORE_TRACE stage=service_catalog type=%s mode=%s categories=%s services=%s",
            session_type,
            session_mode,
            list(category_names.values())[:10],
            safe_titles[:20],
        )

        if len(matches) != 1:
            logging.error(
                "Setmore service auto-mapping failed session_type=%s session_mode=%s available_services=%s",
                session_type, session_mode, safe_titles
            )
            raise SetmoreError(
                f"Setmore service mapping missing for {session_type}/{session_mode}"
            )
        selected = matches[0]
        key = cls._key(selected)
        selected_name = str(selected.get("service_name") or selected.get("name") or selected.get("title") or "").strip()
        selected_duration = selected.get("duration") or selected.get("duration_minutes") or selected.get("service_duration")
        logging.warning(
            "SETMORE_TRACE stage=service_shape fields=%s key_field=%s service_key_field=%s category_key_field=%s category_name=%s",
            sorted(selected.keys()),
            bool(selected.get("key")),
            bool(selected.get("service_key")),
            bool(selected.get("category_key") or selected.get("categoryKey")),
            str(selected.get("category_name") or selected.get("categoryName") or selected.get("category") or "")[:80],
        )
        if mapped_key and mapped_key != key:
            logging.warning(
                "SETMORE_TRACE stage=service_remap type=%s mode=%s old_key=%s new_key=%s new_name=%s",
                session_type, session_mode, mapped_key, key, selected_name[:80]
            )
        else:
            logging.warning(
                "SETMORE_TRACE stage=service_selected type=%s mode=%s key=%s name=%s",
                session_type, session_mode, key, selected_name[:80]
            )
        await db.scheduling_service_mappings.update_one(
            {"provider": "setmore", "session_type": session_type, "session_mode": session_mode},
            {"$set": {
                "service_key": key,
                "service_name": selected_name,
                "service_duration": selected_duration,
                "updated_at": datetime.utcnow().isoformat(),
            }},
            upsert=True,
        )
        return str(key)

    @classmethod
    async def available_slots(
        cls,
        db: AsyncIOMotorDatabase,
        therapist_id: str,
        start_date: str,
        days_ahead: int,
        session_type: str,
        session_mode: str,
    ) -> List[Dict[str, Any]]:
        staff_key, service_key = await asyncio.gather(
            cls.resolve_staff_key(db, therapist_id),
            cls.resolve_service_key(db, session_type, session_mode),
        )
        tz = ZoneInfo(cls.timezone())
        first = datetime.strptime(start_date, "%Y-%m-%d").date()
        output: List[Dict[str, Any]] = []
        logging.warning("SETMORE_TRACE stage=query therapist_id=%s service_key=%s type=%s mode=%s start_date=%s days=%s timezone=%s", therapist_id, service_key, session_type, session_mode, start_date, days_ahead, cls.timezone())
        for offset in range(days_ahead):
            day = first + timedelta(days=offset)
            payload = await cls._api(
                "POST",
                "/slots",
                json={
                    "staff_key": staff_key,
                    "service_key": service_key,
                    "selected_date": day.strftime("%d/%m/%Y"),
                    "off_hours": False,
                    "double_booking": False,
                    "slot_limit": 30,
                    "timezone": cls.timezone(),
                },
            )
            data = payload.get("data") or {}
            slots_present = isinstance(data, dict) and "slots" in data
            slots_map = data.get("slots") if isinstance(data, dict) else None

            # Setmore documents HTTP 200 as a union of a successful slots payload
            # and a validation payload. Do not silently turn a validation response
            # into "zero availability"; surface safe metadata so the real cause can
            # be diagnosed.
            if not slots_present:
                safe_msg = (
                    payload.get("msg")
                    or payload.get("message")
                    or (data.get("msg") if isinstance(data, dict) else None)
                    or (data.get("message") if isinstance(data, dict) else None)
                    or "validation response"
                )
                safe_code = (
                    payload.get("code")
                    or payload.get("status")
                    or (data.get("code") if isinstance(data, dict) else None)
                    or (data.get("status") if isinstance(data, dict) else None)
                )
                logging.warning(
                    "SETMORE_TRACE stage=slots_validation date=%s response=%s code=%s msg=%s top_keys=%s data_keys=%s",
                    day.isoformat(),
                    payload.get("response"),
                    safe_code,
                    str(safe_msg)[:160],
                    sorted(payload.keys()),
                    sorted(data.keys()) if isinstance(data, dict) else [],
                )
                raise SetmoreError(f"Setmore slots validation response: {str(safe_msg)[:120]}")

            if isinstance(slots_map, dict):
                times = slots_map.get(day.isoformat(), [])
                returned_dates = list(slots_map.keys())[:10]
            elif isinstance(slots_map, list):
                times = slots_map
                returned_dates = []
            else:
                times = []
                returned_dates = []

            if not isinstance(times, list):
                times = []
            logging.warning(
                "SETMORE_TRACE stage=day therapist_id=%s date=%s slot_count=%s returned_dates=%s slots_shape=%s",
                therapist_id, day.isoformat(), len(times), returned_dates, type(slots_map).__name__
            )
            for display in times:
                try:
                    local_start = datetime.strptime(
                        f"{day.isoformat()} {display}", "%Y-%m-%d %I:%M %p"
                    ).replace(tzinfo=tz)
                except ValueError:
                    continue
                # FCA currently models counselling slots as 60 minutes. Appointment
                # creation will use the Setmore service duration when wired next.
                local_end = local_start + timedelta(minutes=60)
                output.append({
                    "date": day.isoformat(),
                    "starts_at": local_start.isoformat(),
                    "ends_at": local_end.isoformat(),
                    "time_display": str(display),
                    "is_available": True,
                    "provider": "setmore",
                    "setmore_staff_key": staff_key,
                    "setmore_service_key": service_key,
                })
        if not output:
            # Diagnostic-only probes: never return these times to clients. They
            # isolate timezone/lead-time/window/configuration causes without
            # weakening normal booking rules.
            probe_day = next(
                (first + timedelta(days=offset) for offset in range(1, days_ahead) if (first + timedelta(days=offset)).weekday() < 5),
                first,
            )

            async def probe(day_value, off_hours: bool, double_booking: bool, include_timezone: bool) -> int:
                body = {
                    "staff_key": staff_key,
                    "service_key": service_key,
                    "selected_date": day_value.strftime("%d/%m/%Y"),
                    "off_hours": off_hours,
                    "double_booking": double_booking,
                    "slot_limit": 30,
                }
                if include_timezone:
                    body["timezone"] = cls.timezone()
                payload = await cls._api("POST", "/slots", json=body)
                data = payload.get("data") or {}
                slots_value = data.get("slots") if isinstance(data, dict) else None
                if isinstance(slots_value, dict):
                    values = slots_value.get(day_value.isoformat(), [])
                    return len(values) if isinstance(values, list) else 0
                if isinstance(slots_value, list):
                    return len(slots_value)
                return 0

            try:
                probes = {}
                probes["weekday_standard_no_tz"] = await probe(probe_day, False, False, False)
                probes["weekday_offhours_double_no_tz"] = await probe(probe_day, True, True, False)
                for days_out in (14, 30):
                    future_day = first + timedelta(days=days_out)
                    probes[f"future_{days_out}d"] = await probe(future_day, False, False, False)
                logging.warning(
                    "SETMORE_TRACE stage=empty_diagnostic date=%s results=%s",
                    probe_day.isoformat(),
                    probes,
                )
            except Exception as exc:
                logging.warning(
                    "SETMORE_TRACE stage=empty_diagnostic_failed error=%s",
                    exc.__class__.__name__,
                )

        logging.warning("SETMORE_TRACE stage=complete therapist_id=%s usable_slots=%s", therapist_id, len(output))
        return output
