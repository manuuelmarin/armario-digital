const root = self.registration.scope;
const prefix = "armario-digital:" + new URL(root).pathname + ":",
  cacheKey = prefix + "__REVISION__";
const assets = ["__ASSETS__"].map((path) => new URL(path, root).href);
self.addEventListener("install", (event) =>
  event.waitUntil(caches.open(cacheKey).then((cache) => cache.addAll(assets))),
);
self.addEventListener("activate", (event) =>
  event.waitUntil(
    (async () => {
      for (const key of await caches.keys())
        if (key.startsWith(prefix) && key !== cacheKey)
          await caches.delete(key);
      await self.clients.claim();
    })(),
  ),
);
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  url.search = "";
  url.hash = "";
  const target =
    url.href === root ? new URL("index.html", root).href : url.href;
  if (assets.includes(target))
    event.respondWith(
      caches
        .open(cacheKey)
        .then(
          async (cache) => (await cache.match(target)) || fetch(event.request),
        ),
    );
});
self.addEventListener("message", (event) => {
  if (event.data?.type !== "check-update") return;
  event.waitUntil(
    (async () => {
      const tabs = (
        await self.clients.matchAll({
          includeUncontrolled: true,
          type: "window",
        })
      ).filter((tab) => tab.url.startsWith(root));
      const permits = await Promise.all(
        tabs.map(
          (tab) =>
            new Promise((resolve) => {
              const ch = new MessageChannel();
              const timer = setTimeout(() => {
                ch.port1.close();
                resolve(false);
              }, 3500);
              ch.port1.onmessage = (e) => {
                clearTimeout(timer);
                ch.port1.close();
                resolve(e.data?.ok === true);
              };
              tab.postMessage({ type: "can-update" }, [ch.port2]);
            }),
        ),
      );
      if (permits.every(Boolean)) await self.skipWaiting();
      else {
        for (const tab of tabs) tab.postMessage({ type: "cancel-update" });
        event.source?.postMessage({ type: "busy" });
      }
    })(),
  );
});
