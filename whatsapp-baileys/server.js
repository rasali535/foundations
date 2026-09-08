import fs from 'node:fs/promises';
import path from 'node:path';
import express from 'express';
import pino from 'pino';
import makeWASocket, {
  Browsers,
  DisconnectReason,
  useMultiFileAuthState,
} from '@whiskeysockets/baileys';

const PORT = Number(process.env.PORT || 3001);
const API_TOKEN = process.env.BAILEYS_API_TOKEN;
const AUTH_DIR = process.env.BAILEYS_AUTH_DIR || '/data/baileys-auth';

if (!API_TOKEN) {
  throw new Error('BAILEYS_API_TOKEN is required');
}

await fs.mkdir(AUTH_DIR, { recursive: true });

const logger = pino({ level: process.env.LOG_LEVEL || 'info' });
const app = express();
app.use(express.json({ limit: '64kb' }));

let socket = null;
let currentQr = null;
let connectionState = 'starting';
let reconnectTimer = null;
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

async function connectWhatsApp() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  connectionState = 'connecting';
  currentQr = null;

  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const sock = makeWASocket({
    auth: state,
    browser: Browsers.ubuntu('FCA Notifications'),
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
      logger.info('Baileys WhatsApp session connected');
    }

    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const loggedOut = statusCode === DisconnectReason.loggedOut;
      socket = null;
      currentQr = null;
      connectionState = loggedOut ? 'logged_out' : 'disconnected';

      if (loggedOut) {
        logger.warn('Baileys session logged out; manual re-pairing is required');
      } else {
        logger.warn({ statusCode }, 'Baileys connection closed; scheduling reconnect');
        reconnectTimer = setTimeout(() => {
          connectWhatsApp().catch((err) => logger.error({ err: err?.message }, 'Baileys reconnect failed'));
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
  res.json({ qr: currentQr, status: connectionState });
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

connectWhatsApp().catch((err) => {
  connectionState = 'error';
  logger.error({ error: err?.name }, 'Initial Baileys connection failed');
});

app.listen(PORT, () => {
  logger.info({ port: PORT, authDir: path.resolve(AUTH_DIR) }, 'FCA Baileys adapter listening');
});
