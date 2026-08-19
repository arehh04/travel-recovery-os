/** TR-OS Service Worker — cache app shell, serve offline fallback (Phase 10). */

const CACHE_NAME = 'tros-v3';
const SHELL_FILES = [
  '/',
  '/index.html',
  '/manifest.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_FILES))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  // Clean up stale caches from previous versions
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== CACHE_NAME)
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // API requests: network-first, respect Cache-Control: no-store
  if (request.url.includes('/api/')) {
    event.respondWith(
      fetch(request).then((response) => {
        // Don't cache responses with no-store
        if (response.headers.get('Cache-Control')?.includes('no-store')) {
          return response;
        }
        // Cache successful API responses for offline fallback (Phase 10 fix)
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      }).catch(() => caches.match(request))
    );
    return;
  }

  // Static assets: stale-while-revalidate (Phase 10)
  event.respondWith(
    caches.match(request).then((cached) => {
      // Stale-while-revalidate: return cached immediately, update in background
      const fetchPromise = fetch(request).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      });
      return cached || fetchPromise;
    })
  );
});
