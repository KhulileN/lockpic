/**
 * Service Worker for Digital Literacy Bridge
 * Provides offline capability for core assets.
 */

const CACHE_NAME = "dlb-v1";
const ASSETS_TO_CACHE = [
  "/",
  "/index.html",
  "/static/css/main.css",
  "/static/js/api.js",
  "/static/js/app.js",
  // Add other static assets as needed
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("Service Worker: Caching core assets");
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            console.log("Service Worker: Deleting old cache:", name);
            return caches.delete(name);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  // For same-origin requests, try cache first, then network
  if (request.mode === "navigate" || request.destination === "document") {
    event.respondWith(
      caches.match(request).then((cached) => {
        return cached || fetch(request).catch(() => caches.match("/index.html"));
      })
    );
  } else if (request.destination === "script" || request.destination === "style") {
    event.respondWith(
      caches.match(request).then((cached) => {
        return cached || fetch(request).then((response) => {
          // Optionally cache new assets on the fly
          return response;
        });
      })
    );
  }
  // For API calls, go to network and don't cache by default
});
