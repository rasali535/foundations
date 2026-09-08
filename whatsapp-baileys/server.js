import fs from 'node:fs/promises';
import express from 'express';
import pino from 'pino';
import makeWASocket, {
  Browsers,
  DisconnectReason,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
  useMultiFileAuthState,
} from '@whiskeysockets/baileys';
import { useMongoAuthState } from './mongoAuthState.js';

const PORT = Number(process.env.PORT || 3001);
const API_TOKEN = process.env.BAILEYS_API_TOKEN;
const AUTH_BACKEND = (process.env.BAILEYS_AUTH_BACKEND || 'mongo').toLowerCase();
const AUTH_DIR = process.env.BAILEYS_AUTH_DIR || './auth';
const MONGO_URL = process.env.MONGO_URL;
const MONGO_DB_NAME = process.env.BAILEYS_DB_NAME || 'foundations_baileys';
const SESSION_ID = process.env.BAILEYS_SESSION_ID || 'fca-primary';

if (!API_TOKEN) {
  throw new Error('BAILEYS_API_TOKEN is required');
}
if (!['mongo', 'file'].includes(AUTH_BACKEND)) {
  throw new Error("BAILEYS_AUTH_BACKEND must be 'mongo' or 'file'");
}
if (AUTH_BACKEND === 'mongo' && !MONGO_URL) {
  throw new Error('MONGO_URL is required when BAILEYS_AUTH_BACKEND=mongo');
}
if (AUTH_BACKEND === 'file') {
  await fs.mkdir(AUTH_DIR, { recursive: true });
}

const logger = pino({ level: process.env.LOG_LEVEL || 'info' });
const app = express();
app.use(express.json({ limit: '64kb' }));

let socket = null;
let currentQr = null;
let connectionState = 'starting';
let reconnectTimer = null;
let authClose = null;
let shuttingDown = false;
let currentWaVersion = null;
let lastDisconnectInfo = null;
const recentIdempotencyKeys = new Map();

function redactPhone(value) {
  const digits = String(value || '').replace(/\D/g, '');
  if (digits.length < 7) return '***';
  return `${digits.slice(0, 3)}****${digits.slice(-2)}`;
}

function normalizeInternationalPhone(value) {
  const raw = String(value || '').trim();
  const digits = raw.replace(/\D/g, '');
  if (digits.length < 8 || digits.length > 15) return null;
  return digits;
}

function disconnectReasonName(statusCode) {
  if (statusCode === null || typeof statusCode === 'undefined') return null;
  const match = Object.entries(DisconnectReason).find(
    ([key, value]) => typeof value === 'number' && value === statusCode && Number.isNaN(Number(key)),
  );
  return match?.[0] || null;
}

function requireToken(req, res, next) {
  if (req.headers.authorization !== `Bearer ${API_TOKEN}`) {
    return res.status(401).json({ detail: 'Unauthorized' });
  }
  next();
}

function rememberIdempotency(key, messageId) {
  if (!key) return;
  recentIdempotencyKeys.set(key, { messageId, createdAt: Date.now() });
  if (recentIdempotencyKeys.size > 1000) {
    const oldest = [...recentIdempotencyKeys.entries()]
      .sort((a, b) => a[1].createdAt - b[1].createdAt)
      .slice(0, 100);
    for (const [oldKey] of oldest) recentIdempotencyKeys.delete(oldKey);
  }
}

async function loadAuthState() {
  if (authClose) {
    await authClose().catch(() => {});
    authClose = null;
  }

  if (AUTH_BACKEND === 'mongo') {
    const store = await useMongoAuthState({
      mongoUrl: MONGO_URL,
      dbName: MONGO_DB_NAME,
      sessionId: SESSION_ID,
    });
    authClose = store.close;
    return store;
  }

  // File auth is kept only for local/pilot use. Baileys recommends a DB-backed
  // AuthenticationState for production-grade systems.
  return useMultiFileAuthState(AUTH_DIR);
}

async function connectWhatsApp() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (shuttingDown) return;

  connectionState = 'connecting';
  currentQr = null;

  const { state, saveCreds } = await loadAuthState();
  const { version, isLatest } = await fetchLatestBaileysVersion();
  currentWaVersion = version;
  logger.info({ version: version.join('.'), isLatest }, 'Using WhatsApp Web version');

  const sock = makeWASocket({
    version,
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, logger),
    },
    browser: Browsers.ubuntu('Chrome'),
    printQRInTerminal: false,
    markOnlineOnConnect: false,
    syncFullHistory: false,
    generateHighQualityLinkPreview: false,
    logger,
  });

  socket = sock;
  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      currentQr = qr;
      connectionState = 'pairing_required';
      logger.info('Baileys pairing QR refreshed');
    }

    if (connection === 'open') {
      currentQr = null;
      connectionState = 'connected';
      lastDisconnectInfo = null;
      logger.info({ authBackend: AUTH_BACKEND }, 'Baileys WhatsApp session connected');
    }

    if (connection === 'close') {
      const statusCode =
        lastDisconnect?.error?.output?.statusCode ??
        lastDisconnect?.error?.statusCode ??
        null;
      const reason = disconnectReasonName(statusCode);
      const loggedOut = statusCode === DisconnectReason.loggedOut;

      lastDisconnectInfo = {
        status_code: statusCode,
        reason,
        error_name: lastDisconnect?.error?.name || null,
      };

      socket = null;
      currentQr = null;
      connectionState = loggedOut ? 'logged_out' : 'disconnected';

      if (shuttingDown) return;

      if (loggedOut) {
        logger.warn({ statusCode, reason }, 'Baileys session logged out; manual re-pairing is required');
      } else {
        logger.warn({ statusCode, reason }, 'Baileys connection closed; scheduling reconnect');
        reconnectTimer = setTimeout(() => {
          connectWhatsApp().catch((err) => {
            connectionState = 'error';
            logger.error({ error: err?.name }, 'Baileys reconnect failed');
          });
        }, 5000);
      }
    }
  });
}

app.get('/health', (req, res) => {
  res.json({
    service: 'fca-whatsapp-baileys-adapter',
    status: connectionState,
    connected: connectionState === 'connected',
    auth_backend: AUTH_BACKEND,
    wa_version: currentWaVersion ? currentWaVersion.join('.') : null,
    last_disconnect: lastDisconnectInfo,
  });
});

app.get('/pairing/qr', requireToken, (req, res) => {
  if (!currentQr) {
    return res.status(409).json({
      detail: connectionState === 'connected'
        ? 'WhatsApp is already connected'
        : 'No pairing QR is currently available',
      status: connectionState,
    });
  }
  return res.json({ qr: currentQr, status: connectionState });
});

app.post('/pairing/code', requireToken, async (req, res) => {
  const digits = normalizeInternationalPhone(req.body?.phone);
  if (!digits) {
    return res.status(400).json({ detail: 'Phone must include country code and contain 8-15 digits' });
  }
  if (!socket) {
    return res.status(503).json({ detail: 'WhatsApp socket is not ready', status: connectionState });
  }
  if (socket.authState?.creds?.registered) {
    return res.status(409).json({ detail: 'WhatsApp session is already paired', status: connectionState });
  }

  try {
    const code = await socket.requestPairingCode(digits);
    logger.info({ recipient: redactPhone(digits) }, 'Baileys pairing code generated');
    return res.json({ code, status: connectionState });
  } catch (err) {
    logger.error({ error: err?.name }, 'Baileys pairing code generation failed');
    return res.status(502).json({ detail: 'Could not generate WhatsApp pairing code' });
  }
});

app.post('/send', requireToken, async (req, res) => {
  const { to, text, idempotency_key: idempotencyKey } = req.body || {};
  const digits = normalizeInternationalPhone(to);

  if (!digits) {
    return res.status(400).json({ detail: 'Recipient must be an international phone number' });
  }
  if (!text || typeof text !== 'string' || text.length > 4096) {
    return res.status(400).json({ detail: 'Text is required and must be 4096 characters or fewer' });
  }
  if (!socket || connectionState !== 'connected') {
    return res.status(503).json({ detail: 'WhatsApp session is not connected', status: connectionState });
  }

  if (idempotencyKey && recentIdempotencyKeys.has(idempotencyKey)) {
    const existing = recentIdempotencyKeys.get(idempotencyKey);
    return res.status(200).json({
      message_id: existing.messageId,
      duplicate: true,
    });
  }

  try {
    const jid = `${digits}@s.whatsapp.net`;
    const lookup = await socket.onWhatsApp(jid);
    if (!lookup?.[0]?.exists) {
      return res.status(400).json({ detail: 'Recipient is not available on WhatsApp' });
    }

    const sent = await socket.sendMessage(jid, { text });
    const messageId = sent?.key?.id || null;
    rememberIdempotency(idempotencyKey, messageId);
    logger.info({ recipient: redactPhone(digits) }, 'WhatsApp confirmation accepted by Baileys');

    return res.status(202).json({ message_id: messageId, duplicate: false });
  } catch (err) {
    logger.error({ recipient: redactPhone(digits), error: err?.name }, 'Baileys send failed');
    return res.status(502).json({ detail: 'WhatsApp send failed' });
  }
});

app.use((err, req, res, next) => {
  logger.error({ error: err?.name }, 'Unhandled Baileys service error');
  res.status(500).json({ detail: 'Internal service error' });
});

async function shutdown() {
  shuttingDown = true;
  connectionState = 'shutting_down';
  if (reconnectTimer) clearTimeout(reconnectTimer);
  try {
    socket?.end(new Error('Service shutting down'));
  } catch (_) {}
  if (authClose) await authClose().catch(() => {});
  process.exit(0);
}

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);

connectWhatsApp().catch((err) => {
  connectionState = 'error';
  logger.error({ error: err?.name }, 'Initial Baileys connection failed');
});

app.listen(PORT, () => {
  logger.info({ port: PORT, authBackend: AUTH_BACKEND }, 'FCA Baileys adapter listening');
});
