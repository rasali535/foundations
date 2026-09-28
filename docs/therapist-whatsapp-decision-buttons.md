# Therapist WhatsApp booking decision buttons

The Meta WhatsApp template `fca_therapist_booking_notification` must include **two Quick Reply buttons** in this order:

1. **Accept**
2. **Decline**

Do not use URL or phone-number buttons. The backend supplies opaque payloads for the approved quick-reply buttons:

- Accept -> `FCA_BOOKING_ACCEPT:<booking_id>`
- Decline -> `FCA_BOOKING_DECLINE:<booking_id>`

The button titles are static Meta template content; the booking ID is supplied only in the quick-reply payload.

When the therapist taps a button, Meta posts the reply to the existing WhatsApp webhook. Foundations then:

- verifies the sender against the therapist's configured WhatsApp number
- validates that the booking is assigned to that therapist and is still awaiting acceptance
- on **Accept**, confirms the booking, creates the Setmore appointment when enabled, and sends the client confirmation
- on **Decline**, returns the booking to the Super Admin queue for reassignment
- sends a short WhatsApp acknowledgement back to the therapist

If the Meta template does not contain these two Quick Reply buttons, Meta cannot render them even though the backend supports the payloads.
