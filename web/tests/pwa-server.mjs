import http from "node:http";
import { readFile } from "node:fs/promises";
import { extname, resolve, sep } from "node:path";
let release = "a";
const mime = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "text/javascript",
    ".wasm": "application/wasm",
    ".woff2": "font/woff2",
    ".webmanifest": "application/manifest+json",
    ".png": "image/png",
    ".svg": "image/svg+xml",
};
http.createServer(async (req, res) => {
    if (req.method === "POST" && ["/choose-a", "/choose-b"].includes(req.url)) {
        release = req.url.at(-1);
        res.end("OK");
        return;
    }
    const prefix = "/armario-digital/",
        url = new URL(req.url, "http://localhost");
    if (url.pathname === "/finances/") {
        res.writeHead(200, { "Content-Type": "text/html" });
        res.end(
            "<!doctype html><title>Prueba de coexistencia</title><h1>Finanzas de prueba</h1>",
        );
        return;
    }
    if (url.pathname === "/finances/sw.js") {
        res.writeHead(200, { "Content-Type": "text/javascript" });
        res.end(`
            self.addEventListener("install", event => event.waitUntil(caches.open("finances-ensayo").then(cache=>cache.add("./"))));
            self.addEventListener("activate", event=>event.waitUntil(clients.claim()));
            self.addEventListener("fetch", event => event.respondWith(caches.match(event.request).then(hit=>hit||fetch(event.request))));
        `);
        return;
    }
    if (!url.pathname.startsWith(prefix)) {
        console.warn("Recurso de prueba ausente", url.pathname);
        res.writeHead(404);
        res.end();
        return;
    }
    const root = resolve(release === "a" ? ".fixtures/build-a" : "dist"),
        path = resolve(root, url.pathname.slice(prefix.length) || "index.html");
    if (!path.startsWith(root + sep)) {
        console.warn("Recurso de prueba ausente", url.pathname);
        res.writeHead(404);
        res.end();
        return;
    }
    try {
        const data = await readFile(path);
        res.writeHead(200, {
            "Content-Type": mime[extname(path)] || "application/octet-stream",
            "Cache-Control": "no-store",
        });
        res.end(data);
    } catch {
        console.warn("Recurso de prueba ausente", url.pathname);
        res.writeHead(404);
        res.end();
    }
}).listen(4175, "127.0.0.1");
