from pathlib import Path

from models import Booking, CRMClient
from services.notification_service import NotificationService
from services.whatsapp_booking_bot_service import WhatsAppBookingBotService


def test_whatsapp_slot_list_hides_therapist_identity():
    message = WhatsAppBookingBotService._render_slots([
        {
            "starts_at": "2026-10-06T09:00:00+00:00",
            "therapist_id": "therapist-private",
            "therapist_name": "Private Therapist Name",
        }
    ])

    assert "Private Therapist Name" not in message
    assert "Therapist:" not in message
    assert "Available appointments:" in message


def test_booking_email_uses_assignment_message_not_therapist_name():
    client = CRMClient(
        id="client-privacy",
        client_number="FCA-PRIVACY",
        first_name="Privacy",
        last_name="Test",
        email="privacy@example.com",
        phone="+26770000000",
    )
    booking = Booking(
        id="booking-privacy",
        client_id=client.id,
        client_number=client.client_number,
        therapist_id="therapist-private",
        therapist_name="Private Therapist Name",
        session_type="individual",
        session_mode="in_person",
        starts_at="2026-10-06T09:00:00+00:00",
        ends_at="2026-10-06T10:00:00+00:00",
        location="FCA Clinic",
    )

    _, html_body = NotificationService.build_booking_email_content(client, [booking])

    assert "Private Therapist Name" not in html_body
    assert "Therapist: <strong>" not in html_body
    assert "A suitable therapist will be assigned based on availability and your counselling needs." in html_body


def test_public_booking_sources_do_not_render_therapist_name():
    repo_root = Path(__file__).resolve().parents[2]
    intake_source = (repo_root / "frontend" / "src" / "pages" / "IntakeForm.js").read_text(encoding="utf-8")
    router_source = (repo_root / "backend" / "routers" / "booking_router.py").read_text(encoding="utf-8")

    assert "slot.therapist_name" not in intake_source
    assert "bookingSuccess.therapist_name" not in intake_source
    assert '"therapist_name": therapist.name' not in router_source
    assert 'response_model=PublicBookingConfirmation' in router_source


def test_whatsapp_client_copy_does_not_expose_therapist_label():
    repo_root = Path(__file__).resolve().parents[2]
    service_source = (
        repo_root / "backend" / "services" / "whatsapp_booking_bot_service.py"
    ).read_text(encoding="utf-8")
    day_flow_source = (
        repo_root / "backend" / "services" / "whatsapp_booking_bot_day_flow.py"
    ).read_text(encoding="utf-8")

    assert 'f"Therapist:' not in service_source
    assert 'f"Therapist:' not in day_flow_source
    assert "A suitable therapist will be assigned based on availability and your counselling needs." in service_source
    assert "A suitable therapist will be assigned based on availability and your counselling needs." in day_flow_source
