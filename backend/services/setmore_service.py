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

    @staticmethod
    def _key(row: Dict[str, Any]) -> Optional[str]:
        value = row.get("key") or row.get("staff_key") or row.get("service_key")
        return str(value) if value else None

    @classmethod
    async def resolve_staff_key(cls, db: AsyncIOMotorDatabase, therapist_id: str) -> str:
        therapist = await db.therapists.find_one({"id": therapist_id}, {"_id": 0})
        if not therapist:
            raise SetmoreError("FCA therapist was not found")
        explicit = therapist.get("setmore_staff_key")
        if explicit:
            return str(explicit)
        email = str(therapist.get("email") or "").strip().lower()
        name = str(therapist.get("name") or "").strip().lower()
        rows = await cls.staffs()
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
            "individual": {"individual", "individual counselling", "individual counseling", "counselling", "counseling"},
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
        for row in rows:
            title = norm(row.get("service_name") or row.get("name") or row.get("title"))
            if not title or not cls._key(row):
                continue
            safe_titles.append(title[:80])
            type_score = max((3 if title == alias else 2 if alias in title else 0) for alias in wanted_types)
            mode_score = max((2 if alias in title else 0) for alias in wanted_modes)
            # A type match is required. Mode is a useful discriminator when the
            # Setmore account exposes separate virtual/in-person services.
            if type_score:
                scored.append((type_score + mode_score, mode_score, row))

        mapped_row = next((row for row in rows if cls._key(row) == mapped_key), None) if mapped_key else None

        if scored:
            scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
            best_score = scored[0][0]
            best = [item[2] for item in scored if item[0] == best_score]
            if len(best) == 1:
                matches = best
            elif mapped_row in best:
                matches = [mapped_row]
            else:
                matches = []
        elif mapped_row is not None:
            # Keep an existing valid mapping only when no better FCA-specific
            # service exists. This lets accounts move off bootstrap generic
            # services without manually clearing Mongo mappings.
            matches = [mapped_row]
        else:
            # Fresh Setmore accounts commonly start with generic duration services.
            # FCA counselling appointments are currently 60 minutes, so a single
            # unambiguous one-hour service is the safe bootstrap mapping until the
            # account is renamed/configured with FCA-specific service names.
            hour_aliases = {"1 hour meeting", "60 minute meeting", "60 minutes meeting", "1 hour"}
            hour_matches = [
                row for row in rows
                if norm(row.get("service_name") or row.get("name") or row.get("title")) in hour_aliases
                and cls._key(row)
            ]
            if len(hour_matches) == 1:
                matches = hour_matches
            elif len(rows) == 1 and cls._key(rows[0]):
                matches = rows
            else:
                matches = []

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
            slots_map = ((payload.get("data") or {}).get("slots") or {})
            times = slots_map.get(day.isoformat(), []) if isinstance(slots_map, dict) else []
            if not isinstance(times, list):
                times = []
            logging.warning("SETMORE_TRACE stage=day therapist_id=%s date=%s slot_count=%s returned_dates=%s", therapist_id, day.isoformat(), len(times), list(slots_map.keys())[:10] if isinstance(slots_map, dict) else [])
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
        logging.warning("SETMORE_TRACE stage=complete therapist_id=%s usable_slots=%s", therapist_id, len(output))
        return output
