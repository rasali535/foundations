from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import time
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
from routers.crm_router import crm_router
from routers.booking_router import booking_router
from routers.therapist_router import therapist_router
from routers.admin_router import admin_router
from routers.hr_router import hr_router
from routers.invoice_router import invoice_router

# ----------------- Environment & Configuration -----------------
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
db = client[os.environ.get('DB_NAME', 'foundations_db')]

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', 'dummy_key')

# ----------------- In-Memory Rate Limiting Engine -----------------
RATE_LIMIT_STORE: Dict[str, List[float]] = {}
def check_rate_limit(request: Request, limit: int = 15, window_seconds: int = 60):
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    if client_ip not in RATE_LIMIT_STORE:
        RATE_LIMIT_STORE[client_ip] = []
    
    RATE_LIMIT_STORE[client_ip] = [t for t in RATE_LIMIT_STORE[client_ip] if now - t < window_seconds]
    
    if len(RATE_LIMIT_STORE[client_ip]) >= limit:
        retry_after = int(window_seconds - (now - RATE_LIMIT_STORE[client_ip][0]))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please retry shortly.",
            headers={"Retry-After": str(max(retry_after, 1))}
        )
    
    RATE_LIMIT_STORE[client_ip].append(now)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Create indexes for high performance & query optimization
        await db.crm_clients.create_index([("email", 1)])
        await db.crm_clients.create_index([("phone", 1)])
        await db.crm_clients.create_index([("client_number", 1)], unique=True)
        await db.crm_clients.create_index([("created_at", -1)])
        
        await db.bookings.create_index([("client_id", 1)])
        await db.bookings.create_index([("therapist_id", 1)])
        await db.bookings.create_index([("starts_at", 1)])
        await db.bookings.create_index([("status", 1)])
        
        await db.crm_notes.create_index([("client_id", 1), ("is_pinned", -1), ("created_at", -1)])
        await db.crm_intake_submissions.create_index([("client_id", 1)])
        await db.crm_activity_log.create_index([("client_id", 1)])
        await db.crm_activity_log.create_index([("booking_id", 1)])
        await db.notification_log.create_index([("client_id", 1)])
        
        # Seed default therapists if missing
        await TherapistService.seed_defaults_if_empty(db)
        logging.info("MongoDB indexes verified and therapists seeded.")
    except Exception as e:
        logging.warning(f"Database startup indexing note: {e}")
    yield

# ----------------- App & Middleware Initialization -----------------
app = FastAPI(title="Foundations Counselling Academy API & CRM", version="2.1.0", lifespan=lifespan)
app.state.db = db

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
# Always include localhost for local development if not already present
for _local in ['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:8000', 'http://127.0.0.1:8000']:
    if _local not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(_local)

# Enable Secure cookie flag only when serving over HTTPS in production.
# HTTPS_ONLY env var is explicitly set to "true" in production (Render).
# Local dev and test environments leave it unset (defaults to False).
# We also infer production mode if CORS_ORIGINS contains only https:// origins
# (no localhost), which is the case in the Render production environment.
_cors_has_localhost = any('localhost' in o or '127.0.0.1' in o for o in ALLOWED_ORIGINS)
_IS_HTTPS = (
    os.environ.get('HTTPS_ONLY', '').lower() == 'true'
    or (not _cors_has_localhost and any(o.startswith('https://') for o in ALLOWED_ORIGINS))
)

# The production frontend and API are on different sites
# (academyfoundations.com -> onrender.com). Cross-site XHR session cookies
# therefore require SameSite=None together with Secure. Local HTTP dev/test
# keeps SameSite=Lax so cookies continue to work without HTTPS.
_SESSION_SAME_SITE = 'none' if _IS_HTTPS else 'lax'

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

# ----------------- User Management & RBAC -----------------
# Production user store starts empty and is populated strictly via explicit environment bootstrap or database.
USERS_DB: Dict[str, Dict[str, Any]] = {}

def bootstrap_super_admin():
    """
    Initializes the super_admin user ONLY if explicit environment credentials
    (FCA_BOOTSTRAP_ADMIN_EMAIL / FCA_BOOTSTRAP_ADMIN_PASSWORD or ADMIN_USER / ADMIN_PASSWORD)
    are configured.
    No hardcoded, default, fallback, or domain-derived passwords are ever accepted.
    """
    admin_email = os.environ.get("FCA_BOOTSTRAP_ADMIN_EMAIL") or os.environ.get("ADMIN_USER")
    admin_password = os.environ.get("FCA_BOOTSTRAP_ADMIN_PASSWORD") or os.environ.get("ADMIN_PASSWORD")

    if admin_email and admin_password and len(admin_password.strip()) >= 8:
        email_clean = admin_email.strip().lower()
        admin_data = {
            "password_hash": bcrypt.hashpw(admin_password.strip().encode(), bcrypt.gensalt()).decode(),
            "role": "super_admin",
            "name": "FCA System Administrator",
            "therapist_id": None
        }
        USERS_DB[email_clean] = admin_data
        if "@" in email_clean:
            prefix = email_clean.split("@")[0]
            USERS_DB[prefix] = admin_data
        logging.info(f"Initialized super_admin account for {email_clean}")
    else:
        logging.info("No bootstrap admin credentials provided in environment. User store initialized empty.")

# Initialize on module load
bootstrap_super_admin()

def get_current_user_session(request: Request) -> Dict:
    user_id = request.session.get('user_id')
    if not user_id or user_id not in USERS_DB:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user_info = USERS_DB[user_id].copy()
    user_info['user_id'] = user_id
    return user_info

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

    target_db = request.app.state.db if hasattr(request.app.state, 'db') and request.app.state.db is not None else db
    if not user_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    if user_key not in USERS_DB and target_db is not None:
        try:
            db_user = await target_db.organisation_users.find_one({"user_id": user_key})
            if db_user and db_user.get("password_hash"):
                USERS_DB[user_key] = {
                    "password_hash": db_user["password_hash"],
                    "role": db_user.get("role", "hr_admin"),
                    "name": db_user.get("name", user_key),
                    "organisation_id": db_user.get("organisation_id"),
                    "therapist_id": None
                }
        except Exception:
            pass

    if user_key not in USERS_DB:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    
    user = USERS_DB[user_key]
    if not bcrypt.checkpw(user_pass.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    
    # Establish server-side session
    request.session['user_id'] = user_key
    request.session['role'] = user["role"]
    request.session['name'] = user["name"]
    request.session['therapist_id'] = user.get("therapist_id")
    request.session['organisation_id'] = user.get("organisation_id")
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
    submission = ContactSubmission(**payload.model_dump())
    try:
        await db.contact_submissions.insert_one(submission.model_dump())
    except Exception as e:
        logging.warning(f"MongoDB offline/timeout in /contact: {e}")
    return submission

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
    lead = ChatLead(**payload.model_dump())
    try:
        await db.chatbot_leads.insert_one({
            **lead.model_dump()
        })
    except Exception as e:
        logging.warning(f"MongoDB offline/timeout in /chat/lead: {e}")
    return lead

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
    
    reply = aliana.generate_response(payload.message)
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
    result = await IntakeService.process_intake_submission(
        target_db, payload.model_dump(), source="website_intake"
    )
    return result

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

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
