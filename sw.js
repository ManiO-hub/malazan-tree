const CACHE_NAME = "malazan-tree-v18";
const ASSETS = ["./", "./index.html", "./manifest.json", "./icon.svg", "./icon-192.png", "./icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Réseau d'abord (toujours la dernière version du code à chaque démarrage), cache en secours hors-ligne.
// Les pages sont mises en cache SANS leur paramètre ?v=… pour ne pas faire grossir le cache à chaque démarrage.
self.addEventListener("fetch", e => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin || url.pathname.includes("/api/")) return;

  const isPage = req.mode === "navigate" || url.pathname.endsWith("/") || url.pathname.endsWith("/index.html");
  const key = isPage ? new Request(url.origin + url.pathname) : req;
  const network = isPage ? fetch(url.href, { cache: "no-cache" }) : fetch(req);

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
