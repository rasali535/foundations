const CACHE_NAME = 'foundations-shell-v2';
const SAFE_SHELL = [
  '/',
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
      for (const asset of SAFE_SHELL) {
        try {
          await cache.add(asset);
        } catch (error) {
          // One unavailable optional shell asset must not prevent worker install.
        }
      }
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== 'GET') return;

  // Never intercept or cache authenticated API responses.
  if (url.pathname.startsWith('/api/') || url.hostname === 'api.academyfoundations.com') {
    return;
  }

  // Portal navigation is network-first. If genuinely offline, return a valid
  // cached app shell or a real 503 Response instead of undefined.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(async () => {
        const shell = await caches.match('/');
        return shell || offlineResponse();
      })
    );
    return;
  }

  // Static assets are network-first with a cache fallback. Never return
  // undefined to respondWith().
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
