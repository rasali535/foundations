# Super Admin WhatsApp booking assignment

Foundations supports therapist assignment from WhatsApp without logging into the Admin portal.

## One-time setup

In **Admin > Settings & Audit > Platform Staff & Admin Accounts**, a Super Admin can:

- enter their WhatsApp number in international format
- enable **Allow booking assignment by WhatsApp**
- save the binding

Only active `super_admin` accounts with an enabled, matching WhatsApp number can use the assignment commands.

## WhatsApp flow

From the configured Super Admin WhatsApp number:

1. Send `ASSIGN`
2. Foundations lists pending booking requests that are awaiting assignment or reassignment
3. Reply with the booking number
4. Foundations lists eligible therapists for that requested time
5. Reply with the therapist number
6. The normal `BookingService.assign_therapist()` workflow runs
7. The therapist receives their assignment notification with Accept / Decline
8. The therapist decision continues through the existing acceptance workflow

Useful commands:

- `ADMIN` — show the WhatsApp admin command help
- `ASSIGN` — list booking requests awaiting therapist assignment
- `CANCEL` — exit the current WhatsApp assignment flow

## Security

- WhatsApp admin access is restricted to explicitly enabled Super Admin accounts
- sender identity is matched using normalized international phone numbers
- Admin and non-admin numbers cannot use the Super Admin assignment flow
- the existing booking service remains authoritative for therapist compatibility, conflict protection, live scheduling checks, audit logging, and therapist notification
- no clinical intake content is included in the WhatsApp assignment list
