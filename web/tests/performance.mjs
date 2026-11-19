// Run from web/. Only synthetic files in the temporary Chromium profile are used.
import { chromium } from "playwright";
import { createServer } from "vite";
import { tmpdir, cpus, platform, release } from "node:os";
import { mkdtemp, rm, readFile, readdir } from "node:fs/promises";
import { join } from "node:path";
const profile = await mkdtemp(join(tmpdir(), "armario-perf-"));
const server = await createServer({
    server: { host: "127.0.0.1", port: 4183, strictPort: true },
});
await server.listen();
let ctx;
async function openPage() {
    ctx = await chromium.launchPersistentContext(profile, {
        executablePath: process.env.BROWSER_EXECUTABLE || undefined,
        args: ["--disable-dev-shm-usage"],
        headless: true,
    });
    const page = await ctx.newPage();
    await page.goto("http://127.0.0.1:4183/armario-digital/tests/harness.html");
    await page.evaluate(async () => {
        const base = "/armario-digital/src/";
        window.m = Object.assign(
            {},
            ...(await Promise.all(
                ["engine", "folder", "files"].map(
                    (k) => import(base + k + ".js"),
                ),
            )),
        );
        window.folder = async (n) =>
            (await navigator.storage.getDirectory()).getDirectoryHandle(
                "medicion-" + n,
                { create: true },
            );
    });
    return page;
}
async function seed(page, n) {
    return page.evaluate(async (n) => {
        const canvas = new OffscreenCanvas(512, 512),
            c = canvas.getContext("2d"),
            pixels = c.createImageData(512, 512);
        let rand = 1024;
        for (let i = 0; i < pixels.data.length; i += 4) {
            rand = (Math.imul(rand, 1664525) + 1013904223) >>> 0;
            const value = rand >>> 26;
            pixels.data.set([100 + value, 75 + value, 60 + value, 255], i);
        }
        c.putImageData(pixels, 0, 0);
        const variants = [];
        for (const edge of [512, 384, 256]) {
            const v = new OffscreenCanvas(edge, edge);
            v.getContext("2d").drawImage(canvas, 0, 0, edge, edge);
            const buf = new Uint8Array(
                await (
                    await v.convertToBlob({ type: "image/webp", quality: 0.88 })
                ).arrayBuffer(),
            );
            variants.push({ buf, hash: await m.sha(buf) });
        }
        const sql = [["INSERT INTO locations(name) VALUES('Ficticia')"]];
        const root = await folder(n);
        let batch = [],
            fileBytes = 0;
        const s = await m.create(root, async (dest) => {
            const dir = await dest.getDirectoryHandle("images", {
                create: true,
            });
            for (let g = 1; g <= n; g++) {
                sql.push([
                    "INSERT INTO garments(id,name,category_id,location_id) VALUES(?,?,2,1)",
                    [g, "Prenda ficticia " + g],
                ]);
                for (let p = 0; p < 2; p++) {
                    const token = (g * 2 + p).toString(16).padStart(32, "0"),
                        names = ["", "-preview", "-thumb"].map(
                            (s) => token + s + ".webp",
                        );
                    sql.push([
                        "INSERT INTO garment_images(garment_id,filename,preview,thumbnail,digest,is_primary,sort_order) VALUES(?,?,?,?,?,?,?)",
                        [g, ...names, token, p === 0 ? 1 : 0, p],
                    ]);
                    for (let j = 0; j < 3; j++) {
                        fileBytes += variants[j].buf.length;
                        sql.push([
                            "INSERT INTO image_integrity VALUES(?,?)",
                            [names[j], variants[j].hash],
                        ]);
                        batch.push(m.write(dir, names[j], variants[j].buf));
                    }
                    if (batch.length >= 24) {
                        await Promise.all(batch);
                        batch = [];
                    }
                }
            }
            await Promise.all(batch);
            return m.call("new", null, { statements: sql });
        });
        s.release();
        return {
            catalogBytes: s.head.length,
            photos: n * 2,
            files: n * 6,
            imageBytes: fileBytes,
        };
    }, n);
}
async function rss() {
    if (platform() !== "linux") return null;
    let kb = 0;
    for (const item of await readdir("/proc"))
        if (/^\d+$/.test(item))
            try {
                const cmd = await readFile("/proc/" + item + "/comm", "utf8");
                if (/chrom/i.test(cmd)) {
                    const status = await readFile(
                        "/proc/" + item + "/status",
                        "utf8",
                    );
                    kb += Number(status.match(/VmRSS:\s+(\d+)/)?.[1] || 0);
                }
            } catch {}
    return Math.round(kb / 1024);
}
try {
    for (const n of [100, 1000, 5000]) {
        let page = await openPage();
        const size = await seed(page, n);
        await ctx.close();
        ctx = null;
        page = await openPage();
        let peak = 0;
        const timer = setInterval(async () => {
            peak = Math.max(peak, (await rss()) || 0);
        }, 250);
        let times;
        try {
            times = await page.evaluate(async (n) => {
                const start = performance.now(),
                    root = await folder(n),
                    chosen = performance.now();
                const cold = await m.connect(root),
                    opened = performance.now();
                async function gallery(s) {
                    const rows = await m.call("query", s.head.data, {
                        sql: "SELECT g.name,(SELECT thumbnail FROM garment_images WHERE garment_id=g.id ORDER BY is_primary DESC,coalesce(sort_order,id),id LIMIT 1) thumb FROM garments g WHERE archived=0 ORDER BY g.id DESC LIMIT 24",
                    });
                    const urls = [];
                    await Promise.all(
                        rows.map(async (r) => {
                            const img = document.createElement("img");
                            const url = URL.createObjectURL(
                                await m.read(root, "images/" + r.thumb),
                            );
                            urls.push(url);
                            img.src = url;
                            img.width = 64;
                            img.alt = r.name;
                            document.body.append(img);
                            await img.decode();
                        }),
                    );
                    await new Promise((f) =>
                        requestAnimationFrame(() => requestAnimationFrame(f)),
                    );
                    document.body.replaceChildren();
                    urls.forEach(URL.revokeObjectURL);
                }
                await gallery(cold);
                const visible = performance.now();
                cold.release();
                const warmStart = performance.now(),
                    s = await m.connect(root);
                await gallery(s);
                const warm = performance.now() - warmStart;
                const timings = [];
                for (let i = 0; i < 32; i++) {
                    const before = performance.now();
                    await m.commit(
                        s,
                        {
                            uuid: s.uuid,
                            revision: s.head.revision,
                            operation: crypto.randomUUID(),
                        },
                        [
                            [
                                "UPDATE garments SET notes=? WHERE id=1",
                                ["Edición " + i],
                            ],
                        ],
                    );
                    if (i >= 2) timings.push(performance.now() - before);
                }
                timings.sort((a, b) => a - b);
                s.release();
                return {
                    folderMs: chosen - start,
                    openMs: opened - chosen,
                    firstGalleryMs: visible - chosen,
                    warmGalleryMs: warm,
                    medianMs: (timings[14] + timings[15]) / 2,
                    p95Ms: timings[28],
                    ua: navigator.userAgent,
                };
            }, n);
        } finally {
            clearInterval(timer);
        }
        console.log(
            JSON.stringify({
                n,
                ...size,
                ...times,
                peakBrowserRssMiB: peak || null,
                cpu: cpus()[0].model,
                os: platform() + " " + release(),
            }),
        );
        await ctx.close();
        ctx = null;
    }
} finally {
    await ctx?.close();
    await server.close();
    await rm(profile, { recursive: true, force: true });
}
