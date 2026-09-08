import makeWASocket, {
  Browsers,
  BufferJSON,
  DisconnectReason,
  initAuthCreds,
  makeCacheableSignalKeyStore,
  proto,
  useMultiFileAuthState,
} from '@whiskeysockets/baileys';

const required = {
  makeWASocket,
  Browsers,
  BufferJSON,
  DisconnectReason,
  initAuthCreds,
  makeCacheableSignalKeyStore,
  proto,
  useMultiFileAuthState,
};

for (const [name, value] of Object.entries(required)) {
  if (value === undefined || value === null) {
    throw new Error(`Missing Baileys export: ${name}`);
  }
}

if (typeof makeWASocket !== 'function') throw new Error('makeWASocket is not a function');
if (typeof Browsers.ubuntu !== 'function') throw new Error('Browsers.ubuntu is not available');
if (typeof initAuthCreds !== 'function') throw new Error('initAuthCreds is not a function');
if (typeof makeCacheableSignalKeyStore !== 'function') throw new Error('makeCacheableSignalKeyStore is not a function');
if (typeof useMultiFileAuthState !== 'function') throw new Error('useMultiFileAuthState is not a function');
if (!proto?.Message?.AppStateSyncKeyData?.fromObject) throw new Error('AppStateSyncKeyData.fromObject is unavailable');
if (!BufferJSON?.replacer || !BufferJSON?.reviver) throw new Error('BufferJSON serializer helpers are unavailable');

const creds = initAuthCreds();
if (!creds || typeof creds !== 'object') throw new Error('initAuthCreds did not return credentials');

const browser = Browsers.ubuntu('FCA Verification');
if (!Array.isArray(browser) || browser.length < 3) throw new Error('Unexpected Browsers.ubuntu result');

console.log('Baileys compatibility verification passed.');
console.log('DisconnectReason.loggedOut:', DisconnectReason.loggedOut);
