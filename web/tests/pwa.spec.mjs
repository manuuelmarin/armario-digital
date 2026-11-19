import { test, expect } from "./profile.mjs";
import { testDirectory } from "./helpers.mjs";
test("T09/T11 · edición durante una actualización, reapertura offline y caché hermana", async ({
    context,
    page,
    request,
}) => {
    await request.post("http://127.0.0.1:4175/choose-a");
    await testDirectory(context);
    page.on("dialog", (d) => d.accept());
    await page.goto("http://127.0.0.1:4175/armario-digital/#/catalogo");
    await page.getByRole("button", { name: "Crear armario" }).click();
    await expect(
        page.getByRole("link", { name: "Añadir prenda" }),
    ).toBeVisible();
    const worker = await page.evaluate(async () => {
        const response = await fetch("./sw.js");
        const script = await response.text();
        const list = script.match(/const assets = (\[[^\n]+?\])\.map/);
        if (!list)
            throw Error(
                "Lista de recursos ausente en " +
                    response.status +
                    " " +
                    script.slice(0, 80),
            );
        const missing = (
            await Promise.all(
                JSON.parse(list[1]).map(async (path) => {
                    const r = await fetch(path);
                    return r.ok ? null : [path, r.status];
                }),
            )
        ).filter(Boolean);
        return { missing, workerStatus: response.status };
    });
    expect(worker).toEqual({ missing: [], workerStatus: 200 });
    await expect
        .poll(
            async () =>
                await page.evaluate(async () => {
                    const r = await navigator.serviceWorker.getRegistration();
                    return (
                        r?.active?.state ||
                        r?.installing?.state ||
                        "sin registro"
                    );
                }),
            { timeout: 15000 },
        )
        .toBe("activated");
    await page.evaluate(async () => {
        await navigator.serviceWorker.ready;
        await caches.open("finances-ensayo");
    });
    await page.getByRole("link", { name: "Ajustes", exact: true }).click();
    await page.getByLabel("Nombre de ubicación").fill("Espacio A");
    await request.post("http://127.0.0.1:4175/choose-b");
    await page.evaluate(async () =>
        (await navigator.serviceWorker.ready).update(),
    );
    const update = page.getByRole("button", {
        name: "Nueva versión disponible · Actualizar",
    });
    await expect(update).toBeVisible();
    await update.click();
    await expect(page.locator("#notice")).toContainText("Guarda el formulario");
    await expect(page.getByLabel("Nombre de ubicación")).toHaveValue(
        "Espacio A",
    );
    await page.getByRole("button", { name: "Crear ubicación" }).click();
    await expect(
        page.locator("summary", { hasText: "Espacio A" }),
    ).toBeVisible();
    await update.click();
    await expect(update).toHaveCount(0);
    expect(await page.evaluate(() => caches.has("finances-ensayo"))).toBe(true);
    await context.setOffline(true);
    await page.reload();
    await expect(
        page.locator("summary", { hasText: "Espacio A" }),
    ).toBeVisible();
    await page.getByLabel("Nombre de ubicación").fill("Espacio offline");
    await page.getByRole("button", { name: "Crear ubicación" }).click();
    await expect(
        page.locator("summary", { hasText: "Espacio offline" }),
    ).toBeVisible();
});
