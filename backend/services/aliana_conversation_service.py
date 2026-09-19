from typing import Any, Optional

from models import now_iso
from services.whatsapp_booking_bot_service import WhatsAppBookingBotService


class AlianaConversationService:
    """Shared FCA conversation brain for website, WhatsApp and Messenger."""

    BOOKING_WORDS = ("book", "appointment", "availability", "available", "schedule", "session")
    CRISIS_WORDS = ("kill myself", "suicide", "end my life", "hurt myself", "not safe", "emergency")

    @staticmethod
    def _faq_reply(text: str) -> Optional[str]:
        lower = text.lower()

        if any(term in lower for term in AlianaConversationService.CRISIS_WORDS):
            return (
                "If you are in immediate danger or feel unable to stay safe, please contact Botswana "
                "emergency services on 999 or go to the nearest emergency facility. Aliana can help "
                "with FCA service and booking information, but cannot provide emergency clinical care."
            )
        if any(term in lower for term in ("where are you", "location", "address", "located")):
            return (
                "Foundations Counselling Academy is based at Plot 18680 Khuhurutse St, Phase 2, "
                "Gaborone. FCA also offers virtual counselling appointments."
            )
        if any(term in lower for term in ("couple", "family", "individual", "counselling", "counseling", "therapy")):
            return (
                "FCA offers confidential counselling for individuals, couples and families, with "
                "in-person sessions in Gaborone and virtual appointments. Sessions are generally "
                "50–60 minutes. If you'd like, I can also help you start a booking."
            )
        if "eap" in lower or "employee assistance" in lower or "corporate wellness" in lower:
            return (
                "FCA provides Employee Assistance and workplace wellness support, including "
                "confidential employee counselling and organisational psychosocial-wellness services. "
                "Corporate clients can use their organisation-specific FCA intake pathway."
            )
        if any(term in lower for term in ("price", "pricing", "cost", "rate", "how much")):
            return (
                "Counselling rates are discussed with FCA coordinators during the initial enquiry. "
                "I won't invent a price that FCA hasn't published. I can help you continue with an "
                "enquiry or booking."
            )
        if any(term in lower for term in ("virtual", "online", "remote")):
            return (
                "Yes. FCA offers confidential virtual counselling as well as in-person appointments "
                "in Gaborone. I can help you start a booking and check the available appointment options."
            )
        if any(term in lower for term in ("training", "team building", "workshop")):
            return (
                "FCA provides corporate training and team-development services alongside counselling "
                "and workplace wellness. Tell me what your team or organisation needs and I can point "
                "you to the appropriate FCA pathway."
            )
        if any(term in lower for term in ("hello", "hi", "hey", "good morning", "good afternoon", "good evening")):
            return (
                "Hello, I'm Aliana, Foundations Counselling Academy's assistant. You can ask me about "
                "FCA services, counselling, EAP, virtual or in-person sessions, or tell me you'd like "
                "to book an appointment."
            )
        return None

    @staticmethod
    async def respond(
        db: Any,
        channel: str,
        sender_id: str,
        text: str,
        session_id: Optional[str] = None,
    ) -> str:
        raw = str(text or "").strip()
        if not raw:
            return "How can I help you today?"

        faq = AlianaConversationService._faq_reply(raw)
        lower = raw.lower()
        wants_booking = any(word in lower for word in AlianaConversationService.BOOKING_WORDS)

        # Preserve the existing verified WhatsApp booking state machine. Numbered
        # replies and active booking states must continue through it, while ordinary
        # language at the menu can be handled as an FAQ/conversation.
        if channel == "whatsapp":
            upper = raw.upper()
            booking_commands = {
                "1", "2", "3", "4", "5", "6", "MENU", "START", "HELP", "BOT",
                "BOOK", "BOOK APPOINTMENT", "MY BOOKINGS", "MY APPOINTMENTS",
                "APPOINTMENTS", "RESCHEDULE", "CANCEL", "BALANCE",
                "SESSION BALANCE", "AGENT", "HUMAN", "FCA",
            }
            session = await WhatsAppBookingBotService._get_session(db, sender_id)
            active_booking_state = session.get("state", "menu") != "menu" or session.get("handoff_active")
            token_command = upper.startswith("BOOK ") and len(raw.split()) == 2

            if active_booking_state or upper in booking_commands or token_command or wants_booking:
                booking_text = "BOOK" if wants_booking and not active_booking_state else raw
                booking_reply = await WhatsAppBookingBotService.handle_inbound(db, sender_id, booking_text)
                if booking_reply:
                    return booking_reply

        if faq:
            return faq

        if wants_booking:
            if channel == "messenger":
                return (
                    "I can help with booking. For privacy, Messenger booking needs to be linked to an "
                    "FCA client record first. Please complete the secure FCA intake form; after that "
                    "we can continue the appointment process without discussing clinical details here."
                )
            return (
                "I can help you book an FCA appointment. If you've already completed intake, use your "
                "FCA booking invitation or ask me to book. If not, please complete the secure intake first."
            )

        return (
            "I can help with FCA counselling and services, EAP and corporate wellness, virtual or "
            "in-person appointments, location, and booking. Tell me what you'd like to know in your own words."
        )

    @staticmethod
    async def log_turn(db: Any, channel: str, session_id: str, role: str, content: str) -> None:
        await db.aliana_messages.insert_one({
            "channel": channel,
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": now_iso(),
        })
