const CACHE_NAME = "malazan-tree-v20";
const PORTRAIT_CACHE = "malazan-portraits-v1";
const ASSETS = [
  "./",
  "./index.html",
  "./style.css",
  "./data.js",
  "./app.js",
  "./manifest.json",
  "./icon.svg",
  "./icon-192.png",
  "./icon-512.png"
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  const keep = new Set([CACHE_NAME, PORTRAIT_CACHE]);
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => !keep.has(k)).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Portraits : Cache-First avec mise en cache persistante ;
// Application & données : Réseau d'abord (clé normalisée sans ?v= / ?t=), cache en secours hors-ligne.
self.addEventListener("fetch", e => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin || url.pathname.includes("/api/")) return;

  const isPortrait = url.pathname.includes("/portraits/") || /\.(?:webp|png|jpg|jpeg|svg)$/i.test(url.pathname);
  if (isPortrait) {
    const cleanReq = new Request(url.origin + url.pathname);
    e.respondWith(
      caches.match(cleanReq, { ignoreSearch: true }).then(cached => {
        if (cached) return cached;
        return fetch(req).then(res => {
          if (res && res.ok) {
            const clone = res.clone();
            caches.open(PORTRAIT_CACHE).then(c => c.put(cleanReq, clone));
          }
          return res;
        });
      })
    );
    return;
  }

  const key = new Request(url.origin + url.pathname);
  const isPage = req.mode === "navigate" || url.pathname.endsWith("/") || url.pathname.endsWith("/index.html");
  const isAppAsset = isPage || /\.(?:css|js|json)$/i.test(url.pathname);
  const network = isAppAsset ? fetch(url.href, { cache: "no-cache" }) : fetch(req);

  e.respondWith(
    network
      .then(res => {
        if (res && res.ok) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(c => c.put(key, clone));
        }
        return res;
      })
      .catch(() =>
        caches.match(key, { ignoreSearch: true }).then(r => r || caches.match("./index.html", { ignoreSearch: true }))
      )
  );
});
