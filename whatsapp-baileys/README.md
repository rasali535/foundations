# FCA WhatsApp Baileys Adapter

Optional WhatsApp booking-confirmation adapter for Foundations Counselling & Advisory.

## Important

Baileys is an unofficial WhatsApp Web client and is not affiliated with WhatsApp/Meta. FCA's default production integration remains the official WhatsApp Cloud API. Use this adapter only for legitimate client communications and in accordance with WhatsApp's terms and client consent requirements.

## Runtime

- Node.js 20 or later
- Persistent private filesystem for linked-device credentials
- HTTPS endpoint reachable only by the FCA API

Do **not** deploy the Baileys auth directory to an ephemeral filesystem. A service restart would lose the linked-device session and require a new QR pairing. The auth directory contains sensitive Signal/session key material and must never be committed to Git.

## Environment

```text
BAILEYS_API_TOKEN=<strong random service-to-service token>
BAILEYS_AUTH_DIR=/persistent/private/baileys-auth
PORT=3001
LOG_LEVEL=info
```

## Pairing

1. Start the service.
2. Call `GET /pairing/qr` with `Authorization: Bearer <BAILEYS_API_TOKEN>`.
3. Render the returned QR value using an internal/admin-only QR viewer and scan it from the FCA WhatsApp account's Linked Devices screen.
4. Confirm `GET /health` reports `connected: true`.

Never expose the pairing endpoint publicly without the bearer token.

## FastAPI configuration

To explicitly use Baileys instead of Meta Cloud API:

```text
WHATSAPP_PROVIDER=baileys
BAILEYS_SERVICE_URL=https://<private-baileys-service-host>
BAILEYS_SERVICE_TOKEN=<same value as BAILEYS_API_TOKEN>
```

The FastAPI notification service calls `POST /send` with an E.164 recipient, logistical booking-confirmation text and an idempotency key. The adapter does not ingest client replies or clinical content.

## Production recommendation

Prefer the official Meta Cloud API for production business messaging. If Baileys is enabled, run it as a separate service with persistent encrypted storage, restricted network access and monitoring for disconnect/logged-out state.
