# WhatsApp client booking copy

## Intake acknowledgement template

Meta template name: `fca_intake_received`

The intake acknowledgement must remain privacy-safe. It may use the existing client-name variable, but it must not include clinical intake answers, safety-screen responses, therapy reasons, emergency-contact details, or therapist identity.

Approved client-facing intent:

> Hello {{client_name}}, your intake form has been received successfully. Our clinical team will review your information. When you're ready to book your counselling session, reply **MENU** and choose the booking option.

The **MENU** instruction is static template copy. Do not add it as a new template variable unless the Meta template itself is changed and re-approved with that parameter.

## Therapist assignment

Public and WhatsApp self-service booking flows do not show therapist names before or after booking.

The scheduling engine continues to:
- query eligible therapists internally
- retain the selected `therapist_id`
- create the real booking and Setmore mapping against that therapist
- expose therapist identity to authorised Admin/CRM workflows

Client-facing confirmation wording:

> A suitable therapist will be assigned based on availability and your counselling needs.

This is presentation privacy only; it does not remove or defer the internal therapist assignment required to reserve a real slot.
