from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import time
import asyncio
import re
import json
import hmac
import hashlib
import base64
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
import bcrypt
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone

from models import (
    User, CRMClient, CRMIntakeSubmission, CRMNote,
    Therapist, Booking, BookingBatch, NotificationLog, CRMActivityLog, now_iso
)
from services.therapist_service import TherapistService
from services.intake_service import IntakeService
from services.whatsapp_reminder_dispatcher import WhatsAppReminderDispatcher
from routers.crm_router import crm_router
from routers.booking_router import booking_router
from routers.therapist_router import therapist_router
from routers.admin_router import admin_router
from routers.hr_router import hr_router
from routers.invoice_router import invoice_router
from routers.meta_whatsapp_router import meta_whatsapp_router
from routers.meta_messenger_router import meta_messenger_router
from services.aliana_conversation_service import AlianaConversationService
from services.scheduling_service import SchedulingService
from services.setmore_service import SetmoreService
from services.notification_service import NotificationService

# ----------------- Environment & Configuration -----------------
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
db = client[os.environ.get('DB_NAME', 'foundations_db')]

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', 'dummy_key')
RESEND_WEBHOOK_SECRET = (os.environ.get('RESEND_WEBHOOK_SECRET') or '').strip()
RESEND_INBOUND_DOMAIN = (os.environ.get('RESEND_INBOUND_DOMAIN') or 'forms.academyfoundations.com').strip().lower()

# ----------------- In-Memory Rate Limiting Engine -----------------
RATE_LIMIT_STORE: Dict[str, List[float]] = {}
def check_rate_limit(
    request: Request,
    limit: int = 15,
    window_seconds: int = 60,
    bucket: Optional[str] = None,
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    store_key = f"{client_ip}:{bucket}" if bucket else client_ip
    now = time.time()
    if store_key not in RATE_LIMIT_STORE:
        RATE_LIMIT_STORE[store_key] = []

    RATE_LIMIT_STORE[store_key] = [t for t in RATE_LIMIT_STORE[store_key] if now - t < window_seconds]

    if len(RATE_LIMIT_STORE[store_key]) >= limit:
        retry_after = int(window_seconds - (now - RATE_LIMIT_STORE[store_key][0]))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please retry shortly.",
            headers={"Retry-After": str(max(retry_after, 1))}
        )

    RATE_LIMIT_STORE[store_key].append(now)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Create indexes for high performance & query optimization
        await db.crm_clients.create_index([("email", 1)])
        await db.crm_clients.create_index([("phone", 1)])
        await db.crm_clients.create_index([("client_number", 1)], unique=True)
        await db.crm_clients.create_index([("created_at", -1)])
        await db.crm_clients.create_index([("organisation_id", 1)])
        
        await db.bookings.create_index([("client_id", 1)])
        await db.bookings.create_index([("therapist_id", 1)])
        await db.bookings.create_index([("starts_at", 1)])
        await db.bookings.create_index([("status", 1)])
        
        await db.crm_notes.create_index([("client_id", 1), ("is_pinned", -1), ("created_at", -1)])
        await db.crm_intake_submissions.create_index([("client_id", 1)])
        await db.crm_intake_submissions.create_index([("organisation_id", 1), ("created_at", -1)])
        await db.organisations.create_index([("code", 1)], unique=True)
        await db.staff_users.create_index([("user_id", 1)], unique=True)
        await db.organisation_contacts.create_index(
            [("organisation_id", 1), ("email_normalized", 1)],
            unique=True,
            sparse=True
        )
        await db.organisation_contacts.create_index([("organisation_id", 1), ("active", 1)])
        await db.crm_activity_log.create_index([("client_id", 1)])
        await db.crm_activity_log.create_index([("booking_id", 1)])
        await db.notification_log.create_index([("client_id", 1)])
        await db.resend_webhook_events.create_index([("event_id", 1)], unique=True)
        await db.resend_inbound_messages.create_index([("email_id", 1)], unique=True, sparse=True)
        await db.whatsapp_dispatch_claims.create_index([("event_key", 1)], unique=True)
        
        # Seed default therapists if missing
        await TherapistService.seed_defaults_if_empty(db)

        # Persist the Render-provisioned bootstrap administrator. These credentials
        # are the production recovery path and must survive process restarts instead
        # of existing only in the in-memory USERS_DB cache.
        bootstrap_email = (os.environ.get("FCA_BOOTSTRAP_ADMIN_EMAIL") or "").strip().lower()
        bootstrap_password = (os.environ.get("FCA_BOOTSTRAP_ADMIN_PASSWORD") or "").strip()
        if bootstrap_email and bootstrap_password:
            bootstrap_hash = bcrypt.hashpw(
                bootstrap_password.encode("utf-8"), bcrypt.gensalt()
            ).decode()
            await db.staff_users.update_one(
                {"user_id": {"$regex": f"^{re.escape(bootstrap_email)}$", "$options": "i"}},
                {
                    "$set": {
                        "user_id": bootstrap_email,
                        "password_hash": bootstrap_hash,
                        "role": "super_admin",
                        "name": "System Administrator",
                        "active": True,
                        "organisation_id": None,
                        "therapist_id": None,
                        "updated_at": now_iso(),
                    },
                    "$setOnInsert": {"created_at": now_iso()},
                },
                upsert=True,
            )
            USERS_DB.pop(bootstrap_email, None)
            logging.warning("AUTH_BOOTSTRAP status=ready role=super_admin")
        elif bootstrap_email or bootstrap_password:
            logging.error("AUTH_BOOTSTRAP status=incomplete")

        logging.info("MongoDB indexes verified, therapists seeded, and auth bootstrap checked.")

        scheduling_provider = SchedulingService.provider()
        setmore_configured = SetmoreService.configured()
        logging.warning(
            "SETMORE_HEALTH stage=startup_config provider=%s configured=%s",
            scheduling_provider,
            setmore_configured,
        )
        if scheduling_provider == "setmore" and setmore_configured:
            try:
                setmore_staff = await SetmoreService.staffs()
                logging.warning(
                    "SETMORE_HEALTH stage=startup_connectivity status=ok staff_count=%s timezone=%s",
                    len(setmore_staff),
                    SetmoreService.timezone(),
                )
            except Exception as exc:
                logging.error(
                    "SETMORE_HEALTH stage=startup_connectivity status=failed error=%s",
                    exc.__class__.__name__,
                )
            synced = await SetmoreService.reconcile_pending_bookings(db)
            if synced:
                logging.warning("SETMORE_SYNC stage=startup_backfill synced=%s", synced)
    except Exception as e:
        logging.warning(f"Database startup indexing note: {e}")
    reminder_task = asyncio.create_task(WhatsAppReminderDispatcher.run_forever(db))
    try:
        yield
    finally:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass

# ----------------- App & Middleware Initialization -----------------
app = FastAPI(title="Foundations Counselling Academy API & CRM", version="2.1.0", lifespan=lifespan)
app.state.db = db


@app.get("/health", include_in_schema=False)
async def health():
    return {
        "status": "ok",
        "service": "foundations-api",
        "version": app.version,
    }


@app.get("/ready", include_in_schema=False)
async def ready(request: Request):
    target_db = request.app.state.db
    try:
        await asyncio.wait_for(target_db.command("ping"), timeout=2.0)
    except Exception as exc:
        logging.error("READINESS_CHECK status=failed error=%s", exc.__class__.__name__)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "service": "foundations-api",
                "database": "unavailable",
            },
        )

    return {
        "status": "ready",
        "service": "foundations-api",
        "database": "ok",
    }


# Strict Production Session Middleware
# Reads SESSION_SECRET (Render env var name) with SESSION_SECRET_KEY as alias.
_SESSION_SECRET_RAW = (
    os.environ.get('SESSION_SECRET')
    or os.environ.get('SESSION_SECRET_KEY')
    or 'fca-local-dev-session-key-change-in-production'
)
if _SESSION_SECRET_RAW == 'fca-local-dev-session-key-change-in-production':
    logging.warning(
        "SESSION_SECRET is not set in the environment. "
        "Using insecure local fallback — NOT suitable for production."
    )

# CORS allow-list: read from env at runtime so Render env vars override the defaults.
_CORS_ENV = os.environ.get(
    'CORS_ORIGINS',
    'https://academyfoundations.com,https://www.academyfoundations.com,http://localhost:3000,http://127.0.0.1:3000'
)
ALLOWED_ORIGINS = [o.strip() for o in _CORS_ENV.split(',') if o.strip()]

# Production web origins are mandatory even if a stale Render CORS_ORIGINS value
# is present. Environment configuration may add origins, but must not accidentally
# remove the canonical FCA sites and break public booking/intake requests.
for _required_origin in [
    'https://academyfoundations.com',
    'https://www.academyfoundations.com',
]:
    if _required_origin not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(_required_origin)

# Production HTTPS must be explicit. Render sets HTTPS_ONLY=true via render.yaml.
_IS_HTTPS = os.environ.get('HTTPS_ONLY', '').lower() == 'true'

# Only add localhost origins for local development. Production CORS remains
# limited to the configured/canonical FCA web origins.
if not _IS_HTTPS:
    for _local in ['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:8000', 'http://127.0.0.1:8000']:
        if _local not in ALLOWED_ORIGINS:
            ALLOWED_ORIGINS.append(_local)

# academyfoundations.com and api.academyfoundations.com are same-site HTTPS
# origins, so SameSite=Lax preserves the credentialed API session while
# providing stronger CSRF protection than SameSite=None.
_SESSION_SAME_SITE = 'lax'

app.add_middleware(
    SessionMiddleware,
    secret_key=_SESSION_SECRET_RAW,
    session_cookie='fca_session_id',
    max_age=86400,  # 24 hours
    same_site=_SESSION_SAME_SITE,
    https_only=_IS_HTTPS,  # True in production HTTPS, False in local dev
)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    origin = request.headers.get("origin")
    if (
        request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and origin
        and origin not in ALLOWED_ORIGINS
    ):
        return JSONResponse(status_code=403, content={"detail": "Origin not allowed"})

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "DENY")
    if _IS_HTTPS:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response

# ----------------- User Management & RBAC -----------------
# Production user store starts empty and is populated strictly via explicit environment bootstrap or database.
USERS_DB: Dict[str, Dict[str, Any]] = {}

# No separate bootstrap super-admin account is created. Privileged access is
# assigned explicitly to persistent staff users in MongoDB.
async def _load_persistent_user(target_db, user_key: str) -> Optional[Dict[str, Any]]:
    """Load a staff or organisation user from MongoDB and refresh the process cache."""
    normalized = str(user_key or "").strip().lower()
    if not normalized or target_db is None:
        return None

    exact_ci = {"$regex": f"^{re.escape(normalized)}$", "$options": "i"}
    try:
        db_user = await target_db.staff_users.find_one(
            {"user_id": exact_ci, "active": {"$ne": False}}
        )
        if db_user and db_user.get("password_hash"):
            cached = {
                "password_hash": db_user["password_hash"],
                "role": db_user.get("role", "staff"),
                "name": db_user.get("name", normalized),
                "organisation_id": db_user.get("organisation_id"),
                "therapist_id": db_user.get("therapist_id"),
            }
            USERS_DB[normalized] = cached
            return cached

        db_user = await target_db.organisation_users.find_one(
            {"user_id": exact_ci, "active": {"$ne": False}}
        )
        if db_user and db_user.get("password_hash"):
            cached = {
                "password_hash": db_user["password_hash"],
                "role": db_user.get("role", "hr_admin"),
                "name": db_user.get("name", normalized),
                "organisation_id": db_user.get("organisation_id"),
                "therapist_id": db_user.get("therapist_id"),
                "auth_version": int(db_user.get("auth_version") or 1),
            }
            USERS_DB[normalized] = cached
            return cached
    except Exception as exc:
        logging.exception(
            "AUTH_REHYDRATE_FAILED user=%s error=%s",
            normalized,
            exc.__class__.__name__,
        )
    return None


async def get_current_user_session(request: Request) -> Dict:
    raw_user_id = request.session.get('user_id')
    if not raw_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user_id = str(raw_user_id).strip().lower()
    user_info = USERS_DB.get(user_id)
    if not user_info:
        target_db = request.app.state.db if hasattr(request.app.state, 'db') else db
        user_info = await _load_persistent_user(target_db, user_id)

    if not user_info:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    hydrated = user_info.copy()
    hydrated['user_id'] = user_id
    return hydrated

def require_role(allowed_roles: List[str]):
    def role_checker(user: Dict = Depends(get_current_user_session)):
        if user['role'] not in allowed_roles and user['role'] != 'super_admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}"
            )
        return user
    return role_checker

# ----------------- Domain 1: Marketing / Contact Models -----------------
class ContactSubmissionCreate(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    phone: Optional[str] = None
    inquiry_type: Optional[str] = None
    message: str

class ContactSubmission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    domain: str = "marketing_crm"
    name: str
    email: str
    company: Optional[str] = None
    phone: Optional[str] = None
    inquiry_type: Optional[str] = None
    message: str
    admin_notification_status: Optional[str] = None
    admin_notification_reference: Optional[str] = None
    acknowledgement_status: Optional[str] = None
    acknowledgement_reference: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)

class ChatLeadCreate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    inquiry_type: Optional[str] = None
    session_id: str
    notes: Optional[str] = None

class ChatLead(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    domain: str = "marketing_crm"
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    inquiry_type: Optional[str] = None
    session_id: str
    notes: Optional[str] = None
    notification_status: Optional[str] = None
    notification_reference: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)

# ----------------- Domain 2: Clinical Intake & Triage Models -----------------
class ClinicalSafetyScreen(BaseModel):
    self_harm: str = "No"
    harm_others: str = "No"
    unsafe_environment: str = "No"
    abuse_experienced: str = "No"
    risk_explanation: Optional[str] = None

class ClinicalIntakeCreate(BaseModel):
    full_name: str
    dob: str
    age: Optional[str] = None
    gender: Optional[str] = None
    phone: str
    email: EmailStr
    location: Optional[str] = None
    preferred_contact_method: str = "Phone call"
    emergency_contact_name: str
    emergency_contact_relationship: str
    emergency_contact_phone: str
    reason_for_seeking_therapy: str
    support_needed: List[str] = []
    support_other: Optional[str] = None
    wellbeing_symptoms: List[str] = []
    safety_screen: ClinicalSafetyScreen
    previous_mental_health_support: str = "No"
    previous_support_details: Optional[str] = None
    current_medication: str = "No"
    consent_acknowledged: bool
    typed_signature: str
    consent_date: str
    organisation_code: Optional[str] = None

class ClinicalIntakeRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    domain: str = "clinical_confidential"
    full_name: str
    dob: str
    age: Optional[str] = None
    gender: Optional[str] = None
    phone: str
    email: str
    location: Optional[str] = None
    preferred_contact_method: str
    emergency_contact_name: str
    emergency_contact_relationship: str
    emergency_contact_phone: str
    reason_for_seeking_therapy: str
    support_needed: List[str]
    wellbeing_symptoms: List[str]
    safety_screen: ClinicalSafetyScreen
    triage_level: str
    escalation_required: bool
    disclaimer_accepted: bool
    created_at: str = Field(default_factory=now_iso)

# ----------------- Domain 3: AI Assistant (Aliana) -----------------
class ChatMessageCreate(BaseModel):
    session_id: str
    message: str

class ChatMessageResponse(BaseModel):
    session_id: str
    reply: str
    ai_provider: str = "FCA-Aliana-Isolated"

SYSTEM_PROMPT = """You are Aliana, the friendly and professional AI assistant for Foundations Counselling Academy (FCA)."""

class AlianaEngine:
    def __init__(self, api_key: str, system_prompt: str):
        self.api_key = api_key
        self.system_prompt = system_prompt

    def generate_response(self, user_text: str) -> str:
        lower = user_text.lower()
        if any(w in lower for w in ["ignore previous", "system prompt", "api key", "patient record", "database record", "leak", "secret"]):
            return "Foundations Counselling Academy maintains strict confidentiality and privacy standards. How may I assist you with our counselling or corporate training services?"
        if any(w in lower for w in ["kill myself", "suicide", "end my life", "hurt myself", "emergency"]):
            return "If you are experiencing an immediate crisis or feeling unsafe, please reach out right away to emergency services (Dial 999 in Botswana) or contact our 24/7 crisis response line."
        if "eap" in lower or "counselling" in lower or "counseling" in lower or "therapy" in lower:
            return "Foundations Counselling Academy provides confidential 1-on-1, couples, and family counselling, as well as comprehensive Employee Assistance Programmes (EAP)."
        return "Thank you for reaching out to Foundations Counselling Academy. We specialise in clinical counselling, corporate wellness, and accredited training. How may I assist you?"

aliana = AlianaEngine(api_key=EMERGENT_LLM_KEY, system_prompt=SYSTEM_PROMPT)

# ----------------- API Router & Endpoints -----------------
api_router = APIRouter(prefix="/api")


def _verify_resend_webhook(raw_body: bytes, request: Request) -> bool:
    """Verify Resend/Svix webhook signatures against the untouched request body."""
    if not RESEND_WEBHOOK_SECRET:
        return False

    event_id = request.headers.get("svix-id")
    timestamp = request.headers.get("svix-timestamp")
    signature_header = request.headers.get("svix-signature")
    if not event_id or not timestamp or not signature_header:
        return False

    try:
        timestamp_int = int(timestamp)
    except (TypeError, ValueError):
        return False

    # Svix/Resend recommends rejecting stale signatures to reduce replay risk.
    if abs(int(time.time()) - timestamp_int) > 300:
        return False

    secret = RESEND_WEBHOOK_SECRET
    if secret.startswith("whsec_"):
        secret = secret[len("whsec_"):]

    try:
        key = base64.b64decode(secret)
    except Exception:
        return False

    signed_payload = f"{event_id}.{timestamp}.".encode("utf-8") + raw_body
    expected = base64.b64encode(
        hmac.new(key, signed_payload, hashlib.sha256).digest()
    ).decode("ascii")

    signatures = []
    for item in signature_header.split():
        if item.startswith("v1,"):
            signatures.append(item.split(",", 1)[1])

    return any(hmac.compare_digest(expected, candidate) for candidate in signatures)


@api_router.post("/webhooks/resend", include_in_schema=False)
async def resend_webhook(request: Request):
    if not RESEND_WEBHOOK_SECRET:
        logging.error("RESEND_WEBHOOK status=misconfigured reason=missing_secret")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook verification is not configured."
        )

    raw_body = await request.body()
    if not _verify_resend_webhook(raw_body, request):
        logging.warning("RESEND_WEBHOOK status=rejected reason=invalid_signature")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature.")

    try:
        event = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload.")

    event_id = request.headers.get("svix-id")
    event_type = str(event.get("type") or "")
    event_data = event.get("data") if isinstance(event.get("data"), dict) else {}
    target_db = request.app.state.db if hasattr(request.app.state, "db") and request.app.state.db is not None else db

    # Idempotency: Resend retries events, so processing the same Svix event twice
    # must be harmless.
    existing = await target_db.resend_webhook_events.find_one(
        {"event_id": event_id},
        {"_id": 0, "event_id": 1},
    )
    if existing:
        return {"status": "duplicate_ignored"}

    await target_db.resend_webhook_events.insert_one({
        "event_id": event_id,
        "event_type": event_type,
        "created_at": event.get("created_at") or now_iso(),
        "received_at": now_iso(),
    })

    if event_type == "email.received":
        recipients = [
            str(value).strip().lower()
            for value in (event_data.get("to") or [])
            if value
        ]
        accepted_recipients = [
            address
            for address in recipients
            if address.endswith(f"@{RESEND_INBOUND_DOMAIN}")
        ]

        if not accepted_recipients:
            logging.warning(
                "RESEND_WEBHOOK status=ignored reason=unexpected_recipient event_id=%s",
                event_id,
            )
            return {"status": "ignored"}

        email_id = event_data.get("email_id")
        await target_db.resend_inbound_messages.update_one(
            {"email_id": email_id},
            {"$setOnInsert": {
                "email_id": email_id,
                "message_id": event_data.get("message_id"),
                "from": event_data.get("from"),
                "to": accepted_recipients,
                "subject": event_data.get("subject"),
                "attachments": event_data.get("attachments") or [],
                "provider_created_at": event_data.get("created_at"),
                "received_at": now_iso(),
                "status": "received",
                "source": "resend_inbound",
            }},
            upsert=True,
        )

        logging.info(
            "RESEND_WEBHOOK status=accepted type=email.received event_id=%s email_id=%s",
            event_id,
            email_id,
        )

    return {"status": "accepted"}


@api_router.get("/")
async def root():
    return {
        "service": "Foundations Counselling Academy API & CRM Platform",
        "version": "2.1.0",
        "status": "operational",
        "security_mode": "RBAC + Session-Cookie + CRM & Centralized Booking Engine"
    }

# --- Authentication Endpoints ---
class LoginRequest(BaseModel):
    username: str
    password: str

@api_router.post("/login")
async def login(request: Request, payload: Optional[LoginRequest] = None, username: str = "", password: str = ""):
    raw_key = payload.username if payload else username
    user_key = raw_key.strip().lower() if raw_key else ""
    user_pass = payload.password if payload else password

    # Slow credential-stuffing/brute-force attempts without locking out a whole
    # corporate NAT after a few normal logins.
    check_rate_limit(request, limit=60, window_seconds=300, bucket="login-ip")
    if user_key:
        check_rate_limit(request, limit=10, window_seconds=300, bucket=f"login-user:{user_key}")

    target_db = request.app.state.db if hasattr(request.app.state, 'db') and request.app.state.db is not None else db
    if not user_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    user = USERS_DB.get(user_key)
    if not user:
        user = await _load_persistent_user(target_db, user_key)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not bcrypt.checkpw(user_pass.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    # HR sessions backed by organisation_users get persistent auth-version
    # enforcement. Legacy/in-memory fixtures without a persistent account keep
    # the historical behavior used by the test suite.
    persistent_hr_account = False
    if user.get("role") in ["hr_admin", "hr_viewer"]:
        exact_ci = {"$regex": f"^{re.escape(user_key)}$", "$options": "i"}
        persisted_hr = await target_db.organisation_users.find_one(
            {"user_id": exact_ci, "active": {"$ne": False}},
            {"_id": 0, "auth_version": 1, "organisation_id": 1, "role": 1, "name": 1},
        )
        if persisted_hr:
            persistent_hr_account = True
            user["auth_version"] = int(persisted_hr.get("auth_version") or 1)
            user["organisation_id"] = persisted_hr.get("organisation_id")
            user["role"] = persisted_hr.get("role", user.get("role"))
            user["name"] = persisted_hr.get("name", user.get("name"))
            USERS_DB[user_key] = user
    
    # Establish server-side session
    request.session['user_id'] = user_key
    request.session['role'] = user["role"]
    request.session['name'] = user["name"]
    request.session['therapist_id'] = user.get("therapist_id")
    request.session['organisation_id'] = user.get("organisation_id")
    request.session['auth_version'] = int(user.get("auth_version") or 1)
    request.session['persistent_hr_account'] = persistent_hr_account
    request.session['login_time'] = now_iso()
    
    return {
        "status": "authenticated",
        "user": user_key,
        "name": user["name"],
        "role": user["role"],
        "therapist_id": user.get("therapist_id"),
        "organisation_id": user.get("organisation_id")
    }

@api_router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"status": "logged_out", "detail": "Session terminated"}

@api_router.get("/me")
async def get_me(user: Dict = Depends(get_current_user_session)):
    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "role": user["role"],
        "therapist_id": user.get("therapist_id"),
        "organisation_id": user.get("organisation_id")
    }

# --- Marketing / Contact Endpoints ---
@api_router.post("/contact", response_model=ContactSubmission)
async def submit_contact(payload: ContactSubmissionCreate, request: Request):
    check_rate_limit(request, limit=10, window_seconds=60)
    target_db = request.app.state.db if hasattr(request.app.state, "db") and request.app.state.db is not None else db
    submission = ContactSubmission(**payload.model_dump())
    submission_doc = submission.model_dump()

    # The database is the source of truth. Email is a notification layer only.
    try:
        await target_db.contact_submissions.insert_one(submission_doc)
    except Exception as exc:
        logging.error("CONTACT_SUBMISSION persist_failed error=%s", exc.__class__.__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Your enquiry could not be safely stored. Please try again."
        )

    delivery = await NotificationService.send_contact_notifications(submission_doc)
    public_delivery = {
        "admin_notification_status": delivery.get("admin_notification_status"),
        "admin_notification_reference": delivery.get("admin_notification_reference"),
        "acknowledgement_status": delivery.get("acknowledgement_status"),
        "acknowledgement_reference": delivery.get("acknowledgement_reference"),
    }
    await target_db.contact_submissions.update_one(
        {"id": submission.id},
        {"$set": {
            **public_delivery,
            "notification_updated_at": now_iso(),
        }}
    )

    if delivery.get("admin_notification_status") != "sent":
        logging.warning(
            "CONTACT_SUBMISSION resend_admin_notification_failed id=%s error=%s",
            submission.id,
            delivery.get("admin_notification_error"),
        )
    if delivery.get("acknowledgement_status") != "sent":
        logging.warning(
            "CONTACT_SUBMISSION resend_acknowledgement_failed id=%s error=%s",
            submission.id,
            delivery.get("acknowledgement_error"),
        )

    return ContactSubmission(**{**submission_doc, **public_delivery})

@api_router.get("/contact", response_model=List[ContactSubmission])
async def list_contacts(user: Dict = Depends(require_role(["staff", "admin", "super_admin"]))):
    try:
        docs = await db.contact_submissions.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
        return docs
    except Exception:
        return []

@api_router.post("/chat/lead", response_model=ChatLead)
async def capture_chat_lead(payload: ChatLeadCreate, request: Request):
    check_rate_limit(request, limit=10, window_seconds=60)
    target_db = request.app.state.db if hasattr(request.app.state, "db") and request.app.state.db is not None else db
    lead = ChatLead(**payload.model_dump())
    lead_doc = lead.model_dump()
    try:
        await target_db.chatbot_leads.insert_one(lead_doc)
    except Exception as exc:
        logging.error("CHAT_LEAD persist_failed error=%s", exc.__class__.__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Your details could not be safely stored. Please try again."
        )

    delivery = await NotificationService.send_chat_lead_notification(lead_doc)
    await target_db.chatbot_leads.update_one(
        {"id": lead.id},
        {"$set": {
            "notification_status": delivery.get("notification_status"),
            "notification_reference": delivery.get("notification_reference"),
            "notification_updated_at": now_iso(),
        }}
    )
    if delivery.get("notification_status") != "sent":
        logging.warning(
            "CHAT_LEAD resend_notification_failed id=%s error=%s",
            lead.id,
            delivery.get("notification_error"),
        )
    return ChatLead(**{
        **lead_doc,
        "notification_status": delivery.get("notification_status"),
        "notification_reference": delivery.get("notification_reference"),
    })

@api_router.get("/chat/leads", response_model=List[ChatLead])
async def list_chat_leads(user: Dict = Depends(require_role(["staff", "admin", "super_admin"]))):
    try:
        docs = await db.chatbot_leads.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
        return docs
    except Exception:
        return []

@api_router.post("/chat/message", response_model=ChatMessageResponse)
async def chat_message(payload: ChatMessageCreate, request: Request):
    check_rate_limit(request, limit=20, window_seconds=60)
    try:
        await db.chat_messages.insert_one({
            "session_id": payload.session_id,
            "role": "user",
            "content": payload.message,
            "created_at": now_iso()
        })
    except Exception:
        pass
    
    reply = await AlianaConversationService.respond(
        db, "website", payload.session_id, payload.message, session_id=payload.session_id
    )
    try:
        await db.chat_messages.insert_one({
            "session_id": payload.session_id,
            "role": "assistant",
            "content": reply,
            "created_at": now_iso()
        })
    except Exception:
        pass
    return ChatMessageResponse(session_id=payload.session_id, reply=reply)

# --- Intake Endpoint (Enhanced with CRM Linking) ---
@api_router.post("/clinical/intake", response_model=Dict)
async def submit_clinical_intake(payload: ClinicalIntakeCreate, request: Request):
    check_rate_limit(request, limit=5, window_seconds=60)
    target_db = request.app.state.db if hasattr(request.app.state, 'db') and request.app.state.db is not None else db
    # Process through CRM Intake Service (Atomically links to CRM Profile)
    try:
        result = await IntakeService.process_intake_submission(
            target_db, payload.model_dump(), source="website_intake"
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@api_router.get("/clinical/records", response_model=List[Dict])
async def list_clinical_records(request: Request, user: Dict = Depends(require_role(["clinical_admin", "super_admin"]))):
    target_db = request.app.state.db if hasattr(request.app.state, 'db') and request.app.state.db is not None else db
    try:
        docs = await target_db.crm_intake_submissions.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
        return docs
    except Exception:
        return []

# Mount New Modular Domain Routers
api_router.include_router(crm_router)
api_router.include_router(booking_router)
api_router.include_router(therapist_router)
api_router.include_router(admin_router)
api_router.include_router(hr_router)
api_router.include_router(invoice_router)
api_router.include_router(meta_whatsapp_router)
api_router.include_router(meta_messenger_router)

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
