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
    if (!url.pathname.startsWith(prefix)) {
        res.writeHead(404);
        res.end();
        return;
    }
    const root = resolve(release === "a" ? ".fixtures/build-a" : "dist"),
        path = resolve(root, url.pathname.slice(prefix.length) || "index.html");
    if (!path.startsWith(root + sep)) {
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
        res.writeHead(404);
        res.end();
    }
}).listen(4175, "127.0.0.1");
