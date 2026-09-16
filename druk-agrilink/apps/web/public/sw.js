/* DrukAgriLink service worker: app-shell + reference-data caching.
   Never caches authenticated financial data or tokens. */
const SHELL_CACHE = "druk-shell-v1";
const REF_CACHE = "druk-reference-v1";
const SHELL_URLS = ["/", "/dashboard", "/manifest.json", "/icon.svg"];
const REF_PATTERNS = ["/api/v1/products", "/api/v1/locations"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_URLS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => ![SHELL_CACHE, REF_CACHE].includes(key))
          .map((key) => caches.delete(key)),
      ),
    ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET") return;

  // reference data: network-first, fall back to cache offline
  if (REF_PATTERNS.some((pattern) => url.pathname.startsWith(pattern))) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(REF_CACHE).then((cache) => cache.put(event.request, copy));
          return response;
        })
        .catch(() => caches.match(event.request).then((hit) => hit ?? Response.error())),
    );
    return;
  }
  // never cache other API calls (financial/personal data)
  if (url.pathname.startsWith("/api/")) return;

  // app shell: cache-first
  event.respondWith(
    caches.match(event.request).then((hit) => hit ?? fetch(event.request)),
  );
});
