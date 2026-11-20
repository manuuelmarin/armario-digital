import { test, expect } from "./profile.mjs";
import { testDirectory } from "./helpers.mjs";

import path from "node:path";
import { execFileSync } from "node:child_process";
const fixture = path.resolve(".fixtures");
test("T01/T04/T07/T08/T10/T11 · catálogo, portada, traslado explícito y copia de vuelta", async ({
    context,
    page,
}, testInfo) => {
    await testDirectory(context);
    page.on("dialog", (dialog) => dialog.accept());
    const requests = [];
    page.on("request", (r) => requests.push(r.url()));
    await page.goto("./");
    await page.getByRole("button", { name: "Probar la demo" }).click();
    await expect(
        page.getByRole("heading", { name: "Camisa blanca" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Ajustes", exact: true }).click();
    await page
        .getByRole("button", { name: "Crear armario", exact: true })
        .click();
    await expect(page.locator("#connection")).toContainText(
        "Armario de prueba",
    );
    for (const name of ["Madrid", "Albacete"]) {
        await page.getByLabel("Nombre de ubicación").fill(name);
        await page.getByRole("button", { name: "Crear ubicación" }).click();
        await expect(page.locator("summary", { hasText: name })).toBeVisible();
    }
    await page.getByRole("link", { name: "Catálogo", exact: true }).click();
    await expect(page.getByText("No hay prendas que coincidan.")).toBeVisible();
    for (const [name, price] of [
        ["Camisa blanca", "35"],
        ["Camisa viaje", "18"],
        ["Pantalón", ""],
        ["Archivada", "90"],
    ]) {
        await page.getByRole("link", { name: "Añadir prenda" }).click();
        await page.getByLabel("Nombre", { exact: true }).fill(name);
        await page
            .getByRole("combobox", { name: "Categoría", exact: true })
            .selectOption({ label: "Camisas" });
        await page
            .getByRole("combobox", { name: "Ubicación", exact: true })
            .selectOption({ label: "Madrid" });
        if (price) await page.getByLabel("Precio (€)").fill(price);
        if (name === "Camisa blanca") {
            await page
                .locator("input[type=file]")
                .setInputFiles(
                    ["red", "green", "blue"].map((c) =>
                        path.join(fixture, c + ".jpg"),
                    ),
                );
            await page.getByLabel("Número de la nueva foto").fill("2");
            await page.getByLabel("Verano", { exact: true }).check();
        }
        await page.getByRole("button", { name: "Guardar prenda" }).click();
        await expect(
            page.getByRole("heading", { name, exact: true }),
        ).toBeVisible();
        if (name === "Camisa blanca") {
            await expect(page.locator(".cover img")).toHaveCount(3);
            await page
                .getByRole("button", { name: "Eliminar foto" })
                .first()
                .click();
            await expect(page.locator(".cover img")).toHaveCount(2);
        }
        if (name === "Archivada") {
            await page
                .getByRole("button", { name: "Archivar", exact: true })
                .click();
            await expect(
                page.getByRole("button", { name: "Reactivar" }),
            ).toBeVisible();
        }
        await page.getByRole("link", { name: "Volver al catálogo" }).click();
    }
    await page.getByLabel("Buscar", { exact: true }).fill("pantalon");
    await page.getByRole("button", { name: "Aplicar filtros" }).click();
    await expect(page.locator(".cards article")).toHaveCount(1);
    await expect(page.getByRole("heading", { name: "Pantalón" })).toBeVisible();
    await page.getByRole("link", { name: "Resumen", exact: true }).click();
    await expect(page.locator("tbody")).toContainText("2 de 3");
    await expect(page.locator("tbody")).toContainText("53,00");
    await page.getByRole("link", { name: "Outfits", exact: true }).click();
    await page.getByRole("link", { name: "Crear outfit" }).click();
    await page.getByLabel("Nombre", { exact: true }).fill("Conjunto ficticio");
    await page.getByLabel("Camisa blanca", { exact: true }).check();
    await page.getByLabel("Camisa viaje", { exact: true }).check();
    await page.getByRole("button", { name: "Guardar outfit" }).click();
    await expect(
        page.getByRole("heading", { name: "Conjunto ficticio" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Maletas", exact: true }).click();
    await page.getByRole("link", { name: "Crear maleta" }).click();
    await page.getByLabel("Nombre del viaje").fill("Viaje de prueba");
    await page.getByLabel("Salida", { exact: true }).fill("2026-11-20");
    await page.getByLabel("Vuelta", { exact: true }).fill("2026-11-19");
    await page.getByRole("button", { name: "Guardar viaje" }).click();
    await expect(page.getByRole("status")).toContainText(
        "anterior a la salida",
    );
    await page.getByLabel("Vuelta", { exact: true }).fill("2026-11-20");
    await page.getByRole("button", { name: "Guardar viaje" }).click();
    await expect(
        page.getByRole("heading", { name: "Viaje de prueba" }),
    ).toBeVisible();
    await page.getByLabel("Camisa viaje", { exact: true }).check();
    await page.getByLabel("Objeto libre").fill("Neceser");
    await page.getByRole("button", { name: "Añadir a la maleta" }).click();
    await expect(
        page.locator(".row").filter({ hasText: "Neceser" }),
    ).toBeVisible();
    await page
        .locator(".row")
        .filter({ hasText: "Camisa viaje" })
        .getByRole("button", { name: "Marcar preparado" })
        .click();
    await expect(
        page.getByRole("button", { name: "Confirmar traslado" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Resumen", exact: true }).click();
    await expect(page.locator("tbody")).toContainText("2 de 3");
    await page.goto("./#/maletas/1");
    await page.getByRole("button", { name: "Confirmar traslado" }).click();
    await expect(page.getByText("Se podrán trasladar")).toBeVisible();
    await page.getByRole("link", { name: "Resumen", exact: true }).click();
    await expect(
        page.locator("tr").filter({ hasText: "Madrid" }),
    ).toContainText("1 de 2");
    await expect(
        page.locator("tr").filter({ hasText: "Madrid" }),
    ).toContainText("35,00");
    await expect(
        page.locator("tr").filter({ hasText: "Albacete" }),
    ).toContainText("18,00");
    await page.getByRole("link", { name: "Madrid · Camisas" }).click();
    await expect(page.locator(".cards article")).toHaveCount(2);
    await expect(page.locator(".cards h3")).toHaveText([
        "Pantalón",
        "Camisa blanca",
    ]);
    await page.getByRole("link", { name: "Resumen", exact: true }).click();
    await page.getByRole("link", { name: "Albacete · Camisas" }).click();
    await expect(page.locator(".cards h3")).toHaveText(["Camisa viaje"]);
    await page.getByRole("link", { name: "Ajustes", exact: true }).click();
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Crear y descargar copia" }).click();
    const file = testInfo.outputPath("web.zip");
    await (await download).saveAs(file);
    execFileSync(
        process.env.PYTHON || "python",
        ["web/tests/oracle.py", "roundtrip", file],
        { cwd: path.resolve("..") },
    );
    await page
        .getByRole("link", { name: "Verificar o restaurar una copia" })
        .click();
    await page.getByLabel("Selecciona el ZIP").setInputFiles(file);
    await page.getByRole("button", { name: "Verificar copia" }).click();
    await expect(
        page.getByText("Copia verificada", { exact: true }),
    ).toBeVisible();
    await page.evaluate(() => (window.testTarget = "Restaurado"));
    await page
        .getByRole("button", { name: "Restaurar en una carpeta vacía" })
        .click();
    await expect(page.locator("#connection")).toContainText("Restaurado");
    await expect(
        page.getByRole("heading", { name: "Armario listo" }),
    ).toBeVisible();
    await expect(
        page.getByText(/4 prendas · .*archivos de imagen/),
    ).toBeVisible();
    await page.getByRole("link", { name: "Abrir armario" }).click();
    await expect(page.locator(".cards article")).toHaveCount(3);
    await page.reload();
    await expect(
        page.getByRole("heading", { name: "Camisa blanca" }),
    ).toBeVisible();
    await page.setViewportSize({ width: 390, height: 844 });
    expect(
        await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
        ),
    ).toBe(true);
    expect(
        requests.filter(
            (r) =>
                r.startsWith("http") &&
                !r.startsWith("http://127.0.0.1:4173/armario-digital/"),
        ),
    ).toEqual([]);
});
test("T01/T03 · cancelar, carpeta ajena, una pestaña escritora y perfil sin referencia", async ({
    page,
    context,
}) => {
    await testDirectory(context);
    page.on("dialog", (d) => d.accept());
    await page.goto("./");
    await page.getByRole("button", { name: "Crear armario" }).click();
    await expect(page.locator("#connection")).toContainText("Guardado");
    await page.goto("./#/ajustes");
    await page.evaluate(() => (window.cancelPicker = true));
    await page.getByRole("button", { name: "Abrir mi carpeta" }).click();
    await expect(page.locator("#connection")).toContainText(
        "Armario de prueba",
    );
    const second = await context.newPage();
    await second.goto("./");
    await expect(second.locator("#connection")).toContainText("Solo lectura");
    await second.close();
    await page.close();
    const reopened = await context.newPage();
    await reopened.goto("./");
    await expect(reopened.locator("#connection")).toContainText("Guardado");
});
test("T01/T11 · permiso revocado, reconexión y teclado a 320 píxeles", async ({
    page,
    context,
}) => {
    await testDirectory(context);
    page.on("dialog", (d) => d.accept());
    await page.goto("./");
    await page.getByRole("button", { name: "Crear armario" }).click();
    await expect(page.locator("#connection")).toContainText("Guardado");
    await page.evaluate(() => {
        sessionStorage.setItem("qa-permission", "denied");
        sessionStorage.setItem("qa-denied", "true");
    });
    await page.reload();
    await page.getByRole("button", { name: "Reconectar" }).click();
    await expect(page.locator("#notice")).toContainText("Permiso denegado");
    await expect(page.locator("#notice")).toBeFocused();
    await page.evaluate(() => sessionStorage.removeItem("qa-denied"));
    await page.getByRole("button", { name: "Reconectar" }).click();
    await expect(page.locator("#connection")).toContainText("Guardado");
    await page.setViewportSize({ width: 320, height: 700 });
    const menu = page.getByRole("button", { name: "Menú" });
    await menu.focus();
    await page.keyboard.press("Enter");
    await expect(menu).toHaveAttribute("aria-expanded", "true");
    await page.getByRole("link", { name: "Ajustes", exact: true }).click();
    await expect(page.locator("main")).toBeFocused();
    expect(
        await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
        ),
    ).toBe(true);
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.evaluate(() => {
        document.documentElement.style.zoom = "2";
    });
    for (const theme of ["Oscuro", "Claro"]) {
        await page.getByRole("button", { name: theme, exact: true }).click();
        await expect(page.locator("html")).toHaveAttribute(
            "data-theme",
            theme.toLowerCase(),
        );
        const measured = await page.evaluate(() => {
            const luminance = (rgb) => {
                const values = rgb
                    .match(/\d+/g)
                    .map((v) => Number(v) / 255)
                    .map((v) =>
                        v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4,
                    );
                return (
                    values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722
                );
            };
            return {
                width: document.documentElement.scrollWidth,
                viewport: innerWidth,
                contrast: [
                    document.body,
                    document.querySelector("button.primary"),
                ].map((el) => {
                    const style = getComputedStyle(el),
                        a = luminance(style.color),
                        b = luminance(style.backgroundColor);
                    return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
                }),
            };
        });
        expect(measured.width).toBeLessThanOrEqual(measured.viewport);
        for (const ratio of measured.contrast)
            expect(ratio).toBeGreaterThanOrEqual(4.5);
    }
});
test("Catálogo · la edición en lote guía la selección y confirma el cambio", async ({
    page,
    context,
}) => {
    await testDirectory(context);
    page.on("dialog", (dialog) => dialog.accept());
    await page.goto("./");
    await page.getByRole("button", { name: "Probar la demo" }).click();
    const submit = page.getByRole("button", {
        name: "Confirmar cambios en la selección",
    });
    await expect(submit).toBeHidden();
    await page.getByText("Editar selección", { exact: true }).click();
    await expect(submit).toBeVisible();
    await page.getByLabel("Seleccionar Camisa blanca").check();
    await submit.click();
    await expect(page.getByRole("status")).toContainText(
        "Elige al menos un cambio",
    );
    await page.getByLabel("Nueva categoría").selectOption({ label: "Punto" });
    await submit.click();
    await expect(page.getByRole("status")).toContainText("Cambios guardados");
    await expect(
        page.locator("article", { hasText: "Camisa blanca" }),
    ).toContainText("Punto");
});
