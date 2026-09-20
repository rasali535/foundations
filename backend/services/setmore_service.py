import asyncio
import os
import time
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
        if mapping and mapping.get("service_key"):
            return str(mapping["service_key"])

        wanted = [
            f"{session_type} {session_mode}".replace("_", " "),
            session_type.replace("_", " "),
        ]
        rows = await cls.services()
        matches = []
        for row in rows:
            title = str(row.get("service_name") or row.get("name") or row.get("title") or "").strip().lower()
            if any(value == title for value in wanted):
                matches.append(row)
        if not matches and len(rows) == 1:
            matches = rows
        if len(matches) != 1 or not cls._key(matches[0]):
            raise SetmoreError(
                f"Setmore service mapping missing for {session_type}/{session_mode}"
            )
        key = cls._key(matches[0])
        await db.scheduling_service_mappings.update_one(
            {"provider": "setmore", "session_type": session_type, "session_mode": session_mode},
            {"$set": {"service_key": key, "updated_at": datetime.utcnow().isoformat()}},
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
        return output
