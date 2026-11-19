import { chromium } from "playwright";
import { preview } from "vite";
import { mkdtemp, mkdir, rename, readFile, rm } from "node:fs/promises";
import { homedir, tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import assert from "node:assert/strict";
const run = promisify(execFile),
    channel = process.argv[2];
if (process.platform !== "win32" || !["chrome", "msedge"].includes(channel))
    throw Error("Ejecuta este ensayo en Windows con chrome o msedge.");
const documents = join(homedir(), "Documents");
await mkdir(documents, { recursive: true });
const sample = await mkdtemp(join(documents, "Armario-QA-"));
const work = await mkdtemp(join(tmpdir(), "armario-native-")),
    original = join(sample, "Armario ficticio"),
    moved = join(sample, "Carpeta trasladada");
const server = await preview({
    preview: { host: "127.0.0.1", port: 4182, strictPort: true },
});
let ctx;
async function profile(name) {
    ctx = await chromium.launchPersistentContext(join(work, name), {
        channel,
        headless: false,
        args: ["--force-renderer-accessibility"],
    });
    const p = await ctx.newPage();
    p.setDefaultTimeout(30000);
    p.on("dialog", (d) => d.accept());
    await p.goto("http://127.0.0.1:4182/armario-digital/");
    console.log(channel, await p.evaluate(() => navigator.userAgent));
    return p;
}
async function choose(p, button, path) {
    const cdp = await ctx.newCDPSession(p);
    await cdp.send("Page.setInterceptFileChooserDialog", { enabled: false });
    try {
        const [driver] = await Promise.all([
            run(
                "powershell.exe",
                [
                    "-NoProfile",
                    "-File",
                    resolve("tests/native-picker.ps1"),
                    "-Folder",
                    path,
                ],
                { timeout: 85000 },
            ),
            p.getByRole("button", { name: button, exact: true }).click(),
        ]);
        console.log(driver.stdout);
        await p.getByRole("link", { name: "Añadir prenda" }).waitFor();
    } catch (e) {
        console.log(
            "Estado de la aplicación:",
            await p
                .locator("body")
                .innerText({ timeout: 3000 })
                .catch(() => "diálogo activo"),
        );
        throw e;
    } finally {
        await cdp.detach();
    }
}
try {
    await mkdir(original);
    let page = await profile("Perfil-A");
    await choose(page, "Crear armario", original);
    await page.getByRole("link", { name: "Ajustes", exact: true }).click();
    await page.getByLabel("Nombre de ubicación").fill("Madrid");
    await page.getByRole("button", { name: "Crear ubicación" }).click();
    await page.locator("summary", { hasText: "Madrid" }).waitFor();
    await page.getByRole("link", { name: "Catálogo", exact: true }).click();
    await page.getByRole("link", { name: "Añadir prenda" }).click();
    await page.getByLabel("Nombre", { exact: true }).fill("Camisa Windows");
    await page
        .locator("input[name=photos]")
        .setInputFiles([
            resolve(".fixtures/red.jpg"),
            resolve(".fixtures/blue.jpg"),
        ]);
    await page.getByRole("button", { name: "Guardar prenda" }).click();
    await page.getByRole("heading", { name: "Camisa Windows" }).waitFor();
    const marker = JSON.parse(
        await readFile(join(original, "armario.json"), "utf8"),
    );
    assert.equal(marker.version, 1);
    await ctx.close();
    ctx = null;
    await rename(original, moved);
    page = await profile("Perfil-B");
    await choose(page, "Abrir mi carpeta", moved);
    await page.getByRole("heading", { name: "Camisa Windows" }).click();
    assert.equal(await page.locator(".cover img").count(), 2);
    assert.equal(
        JSON.parse(await readFile(join(moved, "armario.json"), "utf8")).uuid,
        marker.uuid,
    );
    console.log(
        "Selector nativo, dos fotos, escritura NTFS y reapertura desde un perfil nuevo tras mover la carpeta: OK.",
    );
} finally {
    await ctx?.close();
    await server.close();
    await rm(sample, {
        force: true,
        recursive: true,
        maxRetries: 6,
        retryDelay: 500,
    });
    await rm(work, { force: true, recursive: true });
}
