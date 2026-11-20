/**
 * PyClean Pro Mobile Companion - Service Worker (100% Offline PWA)
 * Cache-First strategy for core application shell and offline assets
 */

const CACHE_NAME = 'pyclean-vault-mobile-v1';
const PRECACHE_ASSETS = [
  './',
  './index.html',
  './mobile.css',
  './mobile.js',
  './crypto.js',
  './scanner.js',
  './storage.js',
  './jsqr.min.js',
  './manifest.webmanifest'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS).catch((err) => {
        console.warn('Pre-cache parcial durante install SW:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            return caches.delete(name);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  // Solo interceptar peticiones GET (no interceptar POST a /api/sync)
  if (event.request.method !== 'GET') {
    return;
  }

  const url = new URL(event.request.url);

  // No interceptar peticiones de API dinámicas
  if (url.pathname.includes('/api/')) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request).then((networkResponse) => {
        if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
          return networkResponse;
        }
        const responseToCache = networkResponse.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseToCache);
        });
        return networkResponse;
      }).catch(() => {
        // En caso de caída de red, devolver index.html si es navegación
        if (event.request.mode === 'navigate') {
          return caches.match('./index.html');
        }
      });
    })
  );
});
