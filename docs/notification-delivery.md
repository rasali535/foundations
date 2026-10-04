# Intake, allocation and session notifications

After deployment, new intakes and booking requests create a durable alert for each
active configured administrator. Intake alerts, awaiting-allocation alerts and
therapist-declined alerts also appear in the portal bell. Acknowledgement is tracked
separately for each admin. The optional sound requires clicking the sound toggle
and applies while the portal is open; this is not background browser push.

Admin WhatsApp recipients use the existing `whatsapp_phone` and
`whatsapp_admin_enabled` settings. Both current super-admin accounts qualify.
No clinical answers or client names appear in admin template parameters. The
existing `ASSIGN` flow and therapist Accept/Decline buttons remain available.
Concurrent admins cannot overwrite a booking that has already been allocated.

## Meta templates required before production delivery

Create utility templates in the WhatsApp account connected to the sending number.
Use **named** body parameters with these exact names, and configure the matching
approved language. Do not assume submission means approval.

| Template | Named parameters | Suggested body |
|---|---|---|
| `fca_admin_intake_received` | `reference`, `submitted_at` | Foundations Counselling Academy: a new intake was received at {{submitted_at}}. Reference: {{reference}}. Review securely in the Admin portal. |
| `fca_admin_booking_pending` | `reference`, `submitted_at` | Foundations Counselling Academy: a booking requires therapist allocation. Reference: {{reference}}. Received: {{submitted_at}}. Reply ASSIGN to continue. |
| `fca_admin_booking_declined` | `reference`, `submitted_at` | Foundations Counselling Academy: a therapist declined a booking and reassignment is needed. Reference: {{reference}}. Updated: {{submitted_at}}. Reply ASSIGN to continue. |
| `fca_booking_reminder_6h` | `client_name`, `appointment_date`, `appointment_time` | Hello {{client_name}}, your Foundations Counselling Academy session is in approximately 6 hours, on {{appointment_date}} at {{appointment_time}}. Contact FCA if you need assistance. |

Use a static URL button linking to `https://academyfoundations.com/admin/bookings`
for allocation templates, and `/admin/dashboard` for the intake template. Do not
put clinical details in template samples.

Admin templates use `WHATSAPP_ADMIN_TEMPLATE_LANGUAGE` (otherwise the general
`WHATSAPP_TEMPLATE_LANGUAGE`). Reminders use `WHATSAPP_TEMPLATE_LANGUAGE`.
Template names may be overridden with `WHATSAPP_ADMIN_INTAKE_TEMPLATE`,
`WHATSAPP_ADMIN_BOOKING_TEMPLATE`, `WHATSAPP_ADMIN_DECLINED_TEMPLATE`, and
`WHATSAPP_REMINDER_6H_TEMPLATE`. Copy any overrides to both API and cron.

Existing templates are retained: `fca_booking_reminder_24h`,
`fca_booking_reminder_2h`, and `fca_virtual_access_link` at 3 hours. The last only
applies to confirmed virtual sessions with a meeting URL. No general 3-hour
reminder is introduced.

## Independent scheduling on Render

The API polls the queue while awake. Reliable dispatch during API sleep requires
the separate cron service in `render-notifications.yaml`, every five minutes.
It connects directly to MongoDB; it does not wake or depend on the web API.

Create/apply this cron after the code is merged. Copy `MONGO_URL`, `DB_NAME`,
WhatsApp credentials, approved template locales, Graph API version, and the email
provider settings from the API into the cron's secrets. Never commit credentials.
Render cron has a billing minimum; review its charge when enabling the service.
A Blueprint file alone does not create the live service.

Bookings with legacy timezone offsets are parsed to UTC before selection. The
queue uses UTC timestamps and displays appointment times in Africa/Gaborone.
The default catch-up window is 60 minutes (`WHATSAPP_REMINDER_GRACE_MINUTES`).
Nothing is sent after a session has started. Rescheduled/cancelled bookings are
rechecked immediately before sending. Existing successful legacy claims are
honoured for the same reminder time.

## Failures and retries

Delivery states are pending, processing, retrying, provider-accepted (`sent`),
delivered, read, failed, expired, cancelled, or delivery_unknown. Meta callbacks
update both the transmission log and queue. Temporary provider rejections retry
up to five attempts with exponential delays. Invalid phone/template errors stop
and are visible in Settings; after correction an admin may click Retry.

A send interrupted by a crash or response timeout has an uncertain result. It is
marked delivery_unknown and is not automatically resent, avoiding blind duplicate
sends. Verify delivery externally before any manual recovery of such a record.
Durable deduplication covers each logical alert/recipient and booking/start/event;
it does not promise exactly-once delivery across a third-party network.

Intake accepts explicit international numbers only. The country selector is a
user choice, not automatic inference. Existing invalid client numbers are not
bulk-modified: correct them in CRM from verified client information. A new intake
with an explicit valid number can repair an invalid number matched by email.
