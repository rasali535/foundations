from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import uuid4
from pydantic import BaseModel, Field, EmailStr

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ==================== User & Auth Models ====================

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    email: EmailStr
    password_hash: str
    name: Optional[str] = None
    role: str = "staff"  # staff, admin, super_admin, therapist, clinical_admin
    therapist_id: Optional[str] = None  # Linked therapist ID if role is therapist
    active: bool = True
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
    last_login_at: Optional[str] = None

class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    role: str
    expires_at: str = Field(default_factory=lambda: (datetime.now(timezone.utc) + __import__('datetime').timedelta(hours=24)).isoformat())
    csrf_token: str = Field(default_factory=lambda: str(uuid4()))

# ==================== CRM Client Models ====================

class CRMClient(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    client_number: str  # e.g. "FCA-000001"
    first_name: str
    last_name: str
    email: str
    phone: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    preferred_contact_method: str = "Phone call"
    emergency_contact_name: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    organisation_id: Optional[str] = None  # Nullable for future corporate client support
    organisation_name: Optional[str] = None
    status: str = "active"  # active, inactive, archived, flagged_review
    tags: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class CRMClientCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    preferred_contact_method: str = "Phone call"
    emergency_contact_name: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    organisation_id: Optional[str] = None
    organisation_name: Optional[str] = None
    status: str = "active"
    tags: List[str] = Field(default_factory=list)

class CRMClientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    preferred_contact_method: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    organisation_id: Optional[str] = None
    organisation_name: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

# ==================== Intake Submission Models ====================

class CRMIntakeSubmission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    client_id: str
    client_number: Optional[str] = None
    submission_data: Dict[str, Any]
    triage_level: str = "ROUTINE_COUNSELLING"
    is_high_risk: bool = False
    source: str = "website_intake"  # website_intake, admin_manual, partner_referral
    version: str = "1.0"
    submitted_at: str = Field(default_factory=now_iso)
    created_at: str = Field(default_factory=now_iso)

# ==================== CRM Administrative Notes ====================
# STRICT REQUIREMENT: Administrative CRM notes are for logistics, scheduling, and admin follow-ups.
# Never for clinical notes or medical evaluations.

class CRMNote(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    client_id: str
    author_user_id: str
    author_name: str
    content: str
    is_pinned: bool = False
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class CRMNoteCreate(BaseModel):
    content: str
    is_pinned: bool = False

class CRMNoteUpdate(BaseModel):
    content: Optional[str] = None
    is_pinned: Optional[bool] = None

# ==================== Therapist Models ====================

class Therapist(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    email: EmailStr
    phone: Optional[str] = None
    active: bool = True
    supports_in_person: bool = True
    supports_virtual: bool = True
    specializations: List[str] = Field(default_factory=list)
    working_days: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])  # 0=Mon, 4=Fri
    working_hours_start: str = "08:00"
    working_hours_end: str = "17:00"
    slot_duration_minutes: int = 60
    default_location: Optional[str] = None
    virtual_meeting_link_template: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class TherapistCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    active: bool = True
    supports_in_person: bool = True
    supports_virtual: bool = True
    specializations: List[str] = Field(default_factory=list)
    working_days: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    working_hours_start: str = "08:00"
    working_hours_end: str = "17:00"
    slot_duration_minutes: int = 60
    default_location: Optional[str] = None
    virtual_meeting_link_template: Optional[str] = None

class TherapistUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    active: Optional[bool] = None
    supports_in_person: Optional[bool] = None
    supports_virtual: Optional[bool] = None
    specializations: Optional[List[str]] = None
    working_days: Optional[List[int]] = None
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None
    slot_duration_minutes: Optional[int] = None
    default_location: Optional[str] = None
    virtual_meeting_link_template: Optional[str] = None

class TherapistBlock(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    therapist_id: str
    type: str = "leave"  # leave, blocked_slot, manual_admin_block, public_holiday
    starts_at: str  # ISO string UTC
    ends_at: str    # ISO string UTC
    reason: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)

class TherapistBlockCreate(BaseModel):
    therapist_id: str
    type: str = "leave"
    starts_at: str
    ends_at: str
    reason: Optional[str] = None

# ==================== Booking Models ====================

class BookingParticipant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    booking_id: Optional[str] = None
    client_id: Optional[str] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    participant_role: str = "primary_client"  # primary_client, partner, parent, child, other
    created_at: str = Field(default_factory=now_iso)

class BookingBatch(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    client_id: str
    client_number: Optional[str] = None
    source: str = "admin"  # website, admin, whatsapp
    created_by: Optional[str] = None
    total_slots: int = 1
    notes: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)

class Booking(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    booking_batch_id: Optional[str] = None
    client_id: str
    client_number: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    therapist_id: str
    therapist_name: Optional[str] = None
    session_type: str  # individual, couple, family
    session_mode: str  # in_person, virtual
    starts_at: str  # UTC ISO timestamp
    ends_at: str    # UTC ISO timestamp
    status: str = "confirmed"  # pending, confirmed, completed, cancelled, late_cancelled_billable, rescheduled, no_show
    location: Optional[str] = None
    virtual_meeting_link: Optional[str] = None
    cancellation_reason: Optional[str] = None
    cancelled_at: Optional[str] = None
    cancelled_by: Optional[str] = None
    hours_before_session: Optional[float] = None
    cancellation_billing_status: Optional[str] = None  # billable, non_billable
    rescheduled_from_id: Optional[str] = None
    participants: List[BookingParticipant] = Field(default_factory=list)
    notes: Optional[str] = None
    active_invoice_id: Optional[str] = None  # Reference to linked active invoice (draft, issued, paid)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class SingleBookingSlot(BaseModel):
    starts_at: str  # ISO string
    ends_at: Optional[str] = None  # Defaults to starts_at + 60 min if omitted
    notes: Optional[str] = None

class BookingCreateRequest(BaseModel):
    client_id: Optional[str] = None  # If existing
    client_first_name: Optional[str] = None
    client_last_name: Optional[str] = None
    client_email: Optional[EmailStr] = None
    client_phone: Optional[str] = None
    therapist_id: Optional[str] = None  # If not provided, auto-routes based on session_mode
    session_type: str  # individual, couple, family
    session_mode: str  # in_person, virtual
    starts_at: str
    ends_at: Optional[str] = None
    location: Optional[str] = None
    virtual_meeting_link: Optional[str] = None
    participants: List[Dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = None
    send_notifications: bool = True
    source: str = "admin"  # website, admin, whatsapp

class MultiBookingCreateRequest(BaseModel):
    client_id: Optional[str] = None
    client_first_name: Optional[str] = None
    client_last_name: Optional[str] = None
    client_email: Optional[EmailStr] = None
    client_phone: Optional[str] = None
    therapist_id: Optional[str] = None
    session_type: str  # individual, couple, family
    session_mode: str  # in_person, virtual
    slots: List[SingleBookingSlot]  # E.g. 4 monthly appointment slots
    location: Optional[str] = None
    virtual_meeting_link: Optional[str] = None
    participants: List[Dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = None
    send_notifications: bool = True
    source: str = "admin"

class BookingRescheduleRequest(BaseModel):
    new_starts_at: str
    new_ends_at: Optional[str] = None
    therapist_id: Optional[str] = None
    reason: Optional[str] = None
    send_notifications: bool = True

class BookingStatusUpdateRequest(BaseModel):
    status: str  # completed, cancelled, late_cancelled_billable, no_show, confirmed
    cancellation_reason: Optional[str] = None
    cancellation_billing_status: Optional[str] = None
    # NOTE: cancellation_timestamp is intentionally NOT accepted from clients.
    # The server always uses its own UTC clock for billing classification.
    notes: Optional[str] = None
    send_notifications: bool = True

# ==================== Notification Models ====================

class NotificationLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    client_id: str
    booking_id: Optional[str] = None
    booking_batch_id: Optional[str] = None
    channel: str  # email, whatsapp
    recipient: str
    template: str
    status: str = "pending"  # pending, sent, failed
    subject: Optional[str] = None
    content_summary: Optional[str] = None
    provider_reference: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)

# ==================== Activity & Audit Log Models ====================

class CRMActivityLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    actor_user_id: Optional[str] = None
    actor_name: Optional[str] = None
    client_id: Optional[str] = None
    booking_id: Optional[str] = None
    booking_batch_id: Optional[str] = None
    action: str  # client_created, intake_received, client_updated, note_created, note_updated, note_deleted, booking_created, booking_rescheduled, booking_cancelled, booking_completed, booking_no_show, email_sent, email_failed, whatsapp_sent, whatsapp_failed
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)

# ==================== Corporate Organisation & HR Models ====================

HR_MIN_REPORTING_COUNT = 5  # Privacy threshold: buckets with fewer records are suppressed

class Organisation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    code: str  # Unique code e.g. "CORP-LETS"
    status: str = "active"  # active, inactive, suspended
    contract_start: Optional[str] = None  # YYYY-MM-DD
    contract_end: Optional[str] = None    # YYYY-MM-DD
    allocated_sessions: Optional[int] = None  # Contract session pool
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class OrganisationCreate(BaseModel):
    name: str
    code: str
    status: str = "active"
    contract_start: Optional[str] = None
    contract_end: Optional[str] = None
    allocated_sessions: Optional[int] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None

class OrganisationUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    status: Optional[str] = None
    contract_start: Optional[str] = None
    contract_end: Optional[str] = None
    allocated_sessions: Optional[int] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None

class OrganisationUser(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    organisation_id: str
    user_id: str  # Maps to USERS_DB username/sub
    email: str
    name: str
    role: str = "hr_admin"  # hr_admin, hr_viewer
    password_hash: Optional[str] = None
    active: bool = True
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class OrganisationUserCreate(BaseModel):
    username: str
    password: str
    email: str
    name: str
    role: str = "hr_admin"  # hr_admin, hr_viewer

class AggregateMetric(BaseModel):
    count: Optional[int] = None
    display: str  # e.g. "42", "<5", "0"
    percentage: Optional[float] = None
    suppressed: bool = False

class HRContractStatus(BaseModel):
    organisation_id: str
    organisation_name: str
    contract_status: str
    contract_start: Optional[str] = None
    contract_end: Optional[str] = None
    allocated_sessions: Optional[int] = None
    sessions_used: int
    sessions_remaining: Optional[int] = None
    utilisation_percentage: Optional[float] = None
    is_configured: bool = False

class HRDashboardResponse(BaseModel):
    organisation_id: str
    organisation_name: str
    period: str
    total_sessions: AggregateMetric
    completed: AggregateMetric
    cancelled: AggregateMetric
    no_show: AggregateMetric
    session_types: Dict[str, AggregateMetric]
    session_modes: Dict[str, AggregateMetric]
    contract: HRContractStatus
    detailed_breakdown_available: bool = True
    privacy_notice: str = "All counts below the privacy threshold (5) are masked to safeguard employee anonymity."

# ==================== Corporate Billing & Invoice Models ====================

from decimal import Decimal

SESSION_RATES: Dict[str, Decimal] = {
    "individual": Decimal("350.00"),
    "couple": Decimal("600.00"),
    "family": Decimal("600.00")
}
DEFAULT_CURRENCY: str = "BWP"

SESSION_TYPE_DESCRIPTIONS: Dict[str, str] = {
    "individual": "Individual Counselling",
    "couple": "Couple Counselling",
    "family": "Family Counselling"
}

class InvoiceItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    invoice_id: str
    session_type: str  # individual, couple, family
    description: str
    quantity: int
    unit_price: float
    line_total: float
    created_at: str = Field(default_factory=now_iso)

class InvoiceBookingLink(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    invoice_id: str
    booking_id: str
    session_type: str
    starts_at: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)

class Invoice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    invoice_number: str  # e.g. "FCA-INV-2026-0001"
    organisation_id: str
    organisation_name: str
    billing_period_start: str  # YYYY-MM-DD
    billing_period_end: str    # YYYY-MM-DD
    currency: str = "BWP"
    subtotal: float
    total: float
    total_sessions: int
    status: str = "draft"  # draft, issued, paid, cancelled
    issued_at: Optional[str] = None
    due_date: Optional[str] = None
    paid_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    cancellation_reason: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class InvoicePreviewItem(BaseModel):
    session_type: str
    description: str
    quantity: int
    unit_price: float
    line_total: float

class InvoicePreviewResponse(BaseModel):
    organisation_id: str
    organisation_name: str
    billing_period_start: str
    billing_period_end: str
    currency: str = "BWP"
    items: List[InvoicePreviewItem]
    total_sessions: int
    subtotal: float
    total: float

class InvoiceCreateRequest(BaseModel):
    organisation_id: str
    billing_period_start: str  # YYYY-MM-DD
    billing_period_end: str    # YYYY-MM-DD
    due_date: Optional[str] = None

class InvoiceCancelRequest(BaseModel):
    reason: Optional[str] = "Cancelled by admin"
