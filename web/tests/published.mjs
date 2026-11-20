import { chromium } from "playwright";
import { testDirectory } from "./helpers.mjs";
import { expect } from "@playwright/test";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import assert from "node:assert/strict";
const base = process.argv[2];
if (!base?.endsWith("/armario-digital/"))
    throw Error("URL de proyecto requerida.");
const profile = await mkdtemp(join(tmpdir(), "ad-web-"));
const ctx = await chromium.launchPersistentContext(profile, {
    executablePath: process.env.BROWSER_EXECUTABLE || undefined,
    args: ["--no-sandbox"],
    viewport: { width: 1365, height: 865 },
});
try {
    await testDirectory(ctx);
    const page = await ctx.newPage();
    page.on("dialog", (dialog) => dialog.accept());
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const res = await page.goto(base, { waitUntil: "networkidle" });
    assert.equal(res.status(), 200);
    await expect(
        page.getByRole("button", { name: "Crear armario" }),
    ).toBeVisible();
    const manifest = await page.evaluate(async () =>
        (await fetch("./manifest.webmanifest")).json(),
    );
    assert.equal(manifest.display, "standalone");
    const cdp = await ctx.newCDPSession(page);
    const installedManifest = (await cdp.send("Page.getAppManifest")).manifest;
    assert.equal(installedManifest.id, base);
    assert.equal(installedManifest.scope, base);
    await cdp.detach();
    await page.getByRole("button", { name: "Probar la demo" }).click();
    await expect(
        page.getByRole("heading", { name: "Camisa blanca" }),
    ).toBeVisible();
    await page.locator(".cards img").first().scrollIntoViewIfNeeded();
    await expect
        .poll(() =>
            page
                .locator(".cards img")
                .evaluateAll(
                    (imgs) =>
                        imgs.filter(
                            (img) => img.complete && img.naturalWidth > 0,
                        ).length,
                ),
        )
        .toBe(2);
    await expect
        .poll(() => page.evaluate(() => !!navigator.serviceWorker.controller), {
            timeout: 20000,
        })
        .toBe(true);
    await page.setViewportSize({ width: 375, height: 812 });
    await expect(page.getByRole("button", { name: "Menú" })).toBeVisible();
    assert.equal(
        await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
        ),
        true,
    );
    await ctx.setOffline(true);
    await page.goto(base + "#/demo");
    await page.reload();
    await expect(
        page.getByRole("heading", { name: "Camisa blanca" }),
    ).toBeVisible();
    await page.setViewportSize({ width: 1365, height: 865 });
    await page.getByRole("link", { name: "Ajustes", exact: true }).click();
    await page
        .getByRole("button", { name: "Crear armario", exact: true })
        .click();
    await expect(page.locator("#connection")).toContainText(
        "Armario de prueba",
    );
    await page.getByLabel("Nombre de ubicación").fill("Ubicación ficticia");
    await page.getByRole("button", { name: "Crear ubicación" }).click();
    await expect(
        page.locator("summary", { hasText: "Ubicación ficticia" }),
    ).toBeVisible();
    await page.reload();
    await expect(
        page.locator("summary", { hasText: "Ubicación ficticia" }),
    ).toBeVisible();
    assert.deepEqual(errors, []);
    console.log(
        "URL, recursos de producción, SQLite WASM, dos fotos, manifest, vista móvil, demo y guardado en carpeta ficticia sin conexión verificados en",
        base,
    );
} finally {
    await ctx.close();
    await rm(profile, {
        force: true,
        recursive: true,
        maxRetries: 5,
        retryDelay: 250,
    });
}
