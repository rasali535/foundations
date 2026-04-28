from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

app = FastAPI(title="Foundations Counselling Academy API")
api_router = APIRouter(prefix="/api")


# ---------- Models ----------
class ContactSubmissionCreate(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    phone: Optional[str] = None
    inquiry_type: Optional[str] = None
    message: str


class ContactSubmission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    company: Optional[str] = None
    phone: Optional[str] = None
    inquiry_type: Optional[str] = None
    message: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


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
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    inquiry_type: Optional[str] = None
    session_id: str
    notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChatMessageCreate(BaseModel):
    session_id: str
    message: str


class ChatMessageResponse(BaseModel):
    session_id: str
    reply: str


# ---------- System prompt ----------
SYSTEM_PROMPT = """You are Aria, the friendly assistant for Foundations Counselling Academy — a Pameltex Group company in Botswana specialising in workplace mental health and organisational development.

Your role:
- Help HR managers, executives and procurement teams understand our services.
- Recommend the right service based on their challenge.
- Capture lead details when they show interest (name, company, email, phone, inquiry type) and confirm we'll follow up within 1 business day.
- Be warm, calm, professional, concise (2-4 sentences typical).

Our services:
1) EAP & Counselling — confidential employee counselling, crisis support, wellbeing programmes.
2) Corporate Training — mental health literacy, leader resilience, psychological safety workshops.
3) Psychosocial Risk Management — ISO 45003 aligned assessments and mitigation plans.
4) Organisational Development — culture, change management, team effectiveness.

Our Four Pillars Framework: Assessment → Intervention → Reinforcement → Reporting.

Industries served: Financial Services, Healthcare, Education, Government, Manufacturing.

If asked something outside scope, politely redirect to our services or suggest they use the Contact page. Always invite them to share contact details for tailored guidance."""


# ---------- Routes ----------
@api_router.get("/")
async def root():
    return {"service": "Foundations Counselling Academy API", "status": "ok"}


@api_router.post("/contact", response_model=ContactSubmission)
async def submit_contact(payload: ContactSubmissionCreate):
    submission = ContactSubmission(**payload.model_dump())
    await db.contact_submissions.insert_one(submission.model_dump())
    return submission


@api_router.get("/contact", response_model=List[ContactSubmission])
async def list_contacts():
    docs = await db.contact_submissions.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return docs


@api_router.post("/chat/lead", response_model=ChatLead)
async def capture_chat_lead(payload: ChatLeadCreate):
    lead = ChatLead(**payload.model_dump())
    await db.chatbot_leads.insert_one(lead.model_dump())
    return lead


@api_router.get("/chat/leads", response_model=List[ChatLead])
async def list_chat_leads():
    docs = await db.chatbot_leads.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return docs


@api_router.post("/chat/message", response_model=ChatMessageResponse)
async def chat_message(payload: ChatMessageCreate):
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="LLM key not configured")

    # Persist user message
    await db.chat_messages.insert_one({
        "session_id": payload.session_id,
        "role": "user",
        "content": payload.message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=payload.session_id,
        system_message=SYSTEM_PROMPT,
    ).with_model("openai", "gpt-5.2")

    try:
        reply = await chat.send_message(UserMessage(text=payload.message))
    except Exception as e:
        logging.exception("LLM error")
        raise HTTPException(status_code=502, detail=f"Chat service error: {str(e)}")

    await db.chat_messages.insert_one({
        "session_id": payload.session_id,
        "role": "assistant",
        "content": reply,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return ChatMessageResponse(session_id=payload.session_id, reply=reply)


@api_router.get("/chat/history/{session_id}")
async def chat_history(session_id: str):
    docs = await db.chat_messages.find(
        {"session_id": session_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(500)
    return {"session_id": session_id, "messages": docs}


# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
