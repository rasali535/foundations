const CACHE_NAME = 'foundations-static-v4';
const SAFE_STATIC = [
  '/manifest.json',
  '/admin-manifest.json',
  '/hr-manifest.json',
  '/fca-app-icon.svg'
];

const offlineResponse = () =>
  new Response(
    '<!doctype html><html><head><meta charset="utf-8"><title>Foundations Offline</title></head><body><main style="font-family:system-ui;padding:2rem"><h1>Foundations is offline</h1><p>Reconnect to the internet and reopen the portal.</p></main></body></html>',
    {
      status: 503,
      statusText: 'Offline',
      headers: { 'Content-Type': 'text/html; charset=utf-8' }
    }
  );

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      for (const asset of SAFE_STATIC) {
        try {
          await cache.add(asset);
        } catch (error) {
          // Optional static asset failures must not block worker installation.
        }
      }
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.map((key) => {
      if (key !== CACHE_NAME) return caches.delete(key);
      return Promise.resolve(false);
    })))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== 'GET') return;

  // Authenticated/API traffic is never intercepted or cached.
  if (url.pathname.startsWith('/api/') || url.hostname === 'api.academyfoundations.com') {
    return;
  }

  // HTML/navigation is always network-only. Never fall back to a cached '/'
  // document, because stale app shells can break login and portal boot.
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => offlineResponse()));
    return;
  }

  // Same-origin static assets remain network-first with safe cache fallback.
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok && url.origin === self.location.origin) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(async () => {
        const cached = await caches.match(request);
        return cached || Response.error();
      })
  );
});
