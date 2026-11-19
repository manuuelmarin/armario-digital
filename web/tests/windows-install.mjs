import { chromium } from "@playwright/test";
import { preview } from "vite";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { promisify } from "node:util";
import { execFile } from "node:child_process";
const channel = process.argv[2],
    run = promisify(execFile);
if (process.platform !== "win32" || !["chrome", "msedge"].includes(channel))
    throw Error("Se necesita Chrome o Edge en Windows.");
const base = "http://127.0.0.1:4192/armario-digital/";
const root = await mkdtemp(join(tmpdir(), "ad-pwa-"));
const server = await preview({
    preview: { host: "127.0.0.1", port: 4192, strictPort: true },
});
let ctx,
    cdp,
    installed = false;
try {
    ctx = await chromium.launchPersistentContext(root, {
        channel,
        headless: false,
        viewport: null,
        args: [
            "--force-renderer-accessibility",
            "--disable-features=Translate",
        ],
    });
    ctx.setDefaultTimeout(20000);
    ctx.setDefaultNavigationTimeout(20000);
    const page = await ctx.newPage();
    await page.goto(base);
    await page.bringToFront();
    await page.waitForFunction(() => !!navigator.serviceWorker.controller);
    console.log("Service worker activo. Instalando desde el manifiesto.");
    cdp = await ctx.newCDPSession(page);
    await cdp.send("PWA.install", {
        manifestId: base,
        installUrlOrBundleUrl: base,
    });
    installed = true;
    await cdp.send("PWA.getOsAppState", { manifestId: base });
    await cdp.send("PWA.changeAppUserSettings", {
        manifestId: base,
        displayMode: "standalone",
    });
    if (channel === "msedge") {
        try {
            const apps = await ctx.newPage();
            await apps.goto("edge://apps");
            const name = apps
                .getByText("Mi Armario Digital", { exact: true })
                .first();
            await name.waitFor({ timeout: 10000 });
            let card = name;
            const details = () =>
                card
                    .getByText(/^details$/i)
                    .or(card.getByRole("button", { name: /details/i }))
                    .first();
            for (
                let level = 0;
                level < 8 && !(await details().count());
                level++
            )
                card = card.locator("..");
            const detail = (await details().count())
                ? details()
                : apps.getByText(/^details$/i).first();
            console.log(
                "Aplicaciones de Edge:",
                await apps.locator("body").innerText(),
            );
            await detail.click();
            const shortcut = apps
                .getByText(/create desktop shortcut|create shortcut/i)
                .first();
            await shortcut.click();
            console.log(
                "Acceso de escritorio solicitado desde los detalles de Edge.",
            );
        } catch (error) {
            console.log("El menú de Edge no ofreció el acceso:", error.message);
        }
    }
    const result = await run(
        "powershell.exe",
        [
            "-NoProfile",
            "-File",
            resolve("tests/launch-shortcut.ps1"),
            "-Channel",
            channel,
        ],
        { timeout: 60000 },
    );
    console.log(result.stdout);
} finally {
    if (installed)
        await cdp.send("PWA.uninstall", { manifestId: base }).catch(() => {});
    await ctx?.close();
    await server.close();
    await rm(root, {
        force: true,
        recursive: true,
        maxRetries: 5,
        retryDelay: 300,
    });
}
