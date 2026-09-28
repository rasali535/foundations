# Foundations Resend Form Migration

## Goal

Move public website form delivery away from third-party form forwarding and make the Foundations platform the source of truth.

The production flow is:

```
Public form
  -> Foundations API
  -> MongoDB/Admin Portal
  -> Resend notification
  -> Optional acknowledgement to sender
```

Email delivery is never the source of record. A temporary Resend outage must not lose a website enquiry.

## Migrated flows

### Contact form

Endpoint: `POST /api/contact`

1. Validate and rate-limit the submission.
2. Persist the complete enquiry in `contact_submissions`.
3. Send a Resend notification to `CONTACT_NOTIFICATION_TO`.
4. Set the visitor's email as `reply_to` on the FCA notification.
5. Send a branded acknowledgement to the visitor.
6. Persist Resend acceptance status/reference back onto the enquiry record.
7. Display the enquiry and delivery state under **Admin -> Enquiries**.

### Chatbot lead capture

Endpoint: `POST /api/chat/lead`

1. Persist the lead in `chatbot_leads`.
2. Send a Resend notification to FCA.
3. Persist the Resend acceptance status/reference.
4. Display it under **Admin -> Enquiries -> Chat leads**.

### Booking confirmations

Booking email already uses `NotificationService`. The form migration centralises the shared email transport so booking confirmations and website form notifications use the same Resend implementation.

## Clinical intake

Clinical intake remains in the secure CRM/intake workflow.

Clinical answers, safety-screen responses, therapy reasons and other sensitive intake content are not copied into marketing notification emails. Staff review those records in the authenticated Foundations Admin/CRM portal.

## Production environment

Required:

- `EMAIL_PROVIDER=resend`
- `RESEND_API_KEY=<Render secret>`
- `EMAIL_FROM=Foundations Counselling Academy <notifications@academyfoundations.com>`
- `CONTACT_NOTIFICATION_TO=info@academyfoundations.com`
- `CONTACT_REPLY_TO=info@academyfoundations.com`

The sending domain `academyfoundations.com` must be verified in Resend before production delivery.

## Formspree removal

The current Foundations frontend already posts the Contact form directly to the Foundations API. No Formspree endpoint remains in the active frontend path.

Once this migration is deployed and a production test enquiry has been received in both Admin -> Enquiries and the FCA mailbox, any remaining Formspree account/form configuration can be retired.

## Failure policy

- Database write fails -> return an error to the visitor; do not claim the enquiry was received.
- Database write succeeds but Resend fails -> return success to the visitor because the enquiry is safely stored, mark email delivery as failed, and keep the record visible in Admin -> Enquiries.
- Resend errors are logged without exposing API keys or provider secrets.
