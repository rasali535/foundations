# FCA WhatsApp Baileys Adapter

Optional WhatsApp booking-confirmation adapter for Foundations Counselling & Advisory.

## Important

Baileys is an unofficial WhatsApp Web client and is not affiliated with WhatsApp/Meta. FCA's default production integration remains the official WhatsApp Cloud API. Use this adapter only for legitimate client communications and in accordance with WhatsApp's terms and client consent requirements.

## Runtime

- Node.js 20 or later
- MongoDB-backed auth state for production
- HTTPS endpoint reachable only by the FCA API

Baileys authentication contains long-lived Signal/private key material. Use a dedicated MongoDB user/database for this adapter wherever possible and never commit auth state or credentials to Git.

## Production environment

```text
BAILEYS_API_TOKEN=<strong random service-to-service token>
BAILEYS_AUTH_BACKEND=mongo
MONGO_URL=<dedicated MongoDB connection string>
BAILEYS_DB_NAME=foundations_baileys
BAILEYS_SESSION_ID=fca-primary
PORT=3001
LOG_LEVEL=info
```

The Mongo auth store persists Baileys credentials and Signal keys across service restarts. The built-in file mode is retained only for local/pilot use because Baileys recommends a SQL/NoSQL-backed authentication state for production systems.

## Local / pilot file mode

```text
BAILEYS_AUTH_BACKEND=file
BAILEYS_AUTH_DIR=./auth
```

The auth directory is ignored by Git and must still be treated as sensitive key material.

## Pairing

1. Start the service.
2. Call `GET /pairing/qr` with `Authorization: Bearer <BAILEYS_API_TOKEN>`.
3. Render the returned QR value using an internal/admin-only QR viewer and scan it from the FCA WhatsApp account's **Linked Devices** screen.
4. Confirm `GET /health` reports `connected: true`.

Never expose the pairing endpoint without the bearer token.

## FastAPI configuration

To explicitly use Baileys instead of Meta Cloud API:

```text
WHATSAPP_PROVIDER=baileys
BAILEYS_SERVICE_URL=https://<private-baileys-service-host>
BAILEYS_SERVICE_TOKEN=<same value as BAILEYS_API_TOKEN>
```

The FastAPI notification service calls `POST /send` with an international recipient, logistical booking-confirmation text and an idempotency key. The adapter does not ingest client replies, intake content or clinical notes.

## Production recommendation

Prefer the official Meta Cloud API for production business messaging. If Baileys is enabled, keep it as a separate service with Mongo-backed auth state, restricted API access and monitoring for disconnected/logged-out state.
