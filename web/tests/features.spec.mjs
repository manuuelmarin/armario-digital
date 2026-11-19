import { test, expect } from "./profile.mjs";
import { testDirectory, openModules } from "./helpers.mjs";
import { resolve } from "node:path";
import { readFile } from "node:fs/promises";
test("T04/T07/T10 · grupos, colecciones compartidas, tableros y meteorología explícita", async ({
    page,
    context,
}) => {
    await testDirectory(context);
    page.on("dialog", (dialog) => dialog.accept());
    const requests = [];
    page.on("request", (r) => requests.push(r.url()));
    await page.goto("./");
    await page.getByRole("button", { name: "Probar la demo" }).click();
    await page.getByRole("link", { name: "Importar grupos de fotos" }).click();
    const boxes = page.locator("[data-groups] fieldset");
    await boxes
        .nth(0)
        .getByLabel("Nombre", { exact: true })
        .fill("Frente y espalda");
    await boxes
        .nth(0)
        .locator("input[type=file]")
        .setInputFiles([
            resolve(".fixtures/red.jpg"),
            resolve(".fixtures/blue.jpg"),
        ]);
    await page.getByRole("button", { name: "Añadir otro grupo" }).click();
    await boxes
        .nth(1)
        .getByLabel("Nombre", { exact: true })
        .fill("Otra camisa");
    await boxes
        .nth(1)
        .locator("input[type=file]")
        .setInputFiles({
            name: "red.jpg",
            mimeType: "image/jpeg",
            buffer: Buffer.from("inválida"),
        });
    await page.getByRole("button", { name: "Guardar lote" }).click();
    await expect(page.getByRole("status")).toContainText("Formato no admitido");
    await boxes
        .nth(1)
        .locator("input[type=file]")
        .setInputFiles(resolve(".fixtures/red.jpg"));
    await page.getByRole("button", { name: "Guardar lote" }).click();
    await expect(
        page.getByRole("heading", { name: "Catálogo", exact: true }),
    ).toBeVisible();
    await expect(page.locator(".cards article")).toHaveCount(4);
    for (const name of ["Cápsula A", "Cápsula B"]) {
        await page
            .getByRole("link", { name: "Colecciones", exact: true })
            .click();
        await page.getByRole("link", { name: "Crear colección" }).click();
        await page.getByLabel("Nombre", { exact: true }).fill(name);
        await page.getByLabel("Frente y espalda", { exact: true }).check();
        await page.getByRole("button", { name: "Guardar colección" }).click();
        await expect(page.getByRole("heading", { name })).toBeVisible();
    }
    await page.getByRole("button", { name: "Eliminar colección" }).click();
    await page.getByRole("link", { name: "Cápsula A" }).click();
    await expect(page.locator(".row")).toContainText("Frente y espalda");
    await page.goto("./#/etiquetas/nuevo");
    await page.getByLabel("Nombre", { exact: true }).fill("Fiesta");
    await page.getByLabel("Frente y espalda", { exact: true }).check();
    await page.getByRole("button", { name: "Guardar etiqueta" }).click();
    await expect(page.getByRole("heading", { name: "Fiesta" })).toBeVisible();
    await page.getByRole("link", { name: "Inspiración", exact: true }).click();
    await page.getByLabel("Nombre del tablero").fill("Ideas");
    await page.getByRole("button", { name: "Crear tablero" }).click();
    await page.getByLabel("Descripción").fill("Combinación de prueba");
    await page
        .getByLabel("Enlace", { exact: true })
        .fill("https://example.org/inspiracion-ficticia");
    await page.getByLabel("Posición horizontal").fill("32");
    await page.getByLabel("Posición vertical").fill("70");
    await page.getByLabel("Ancho").fill("220");
    await page
        .getByLabel("Imagen opcional")
        .setInputFiles(resolve(".fixtures/green.jpg"));
    await page.getByRole("button", { name: "Añadir elemento" }).click();
    await expect(page.locator(".pin img")).toBeVisible();
    await expect(page.locator(".pin")).toHaveCSS("left", "32px");
    await page.getByRole("link", { name: "Tiempo", exact: true }).click();
    expect(requests.filter((u) => u.startsWith("https://"))).toEqual([]);
    let count = 0;
    await page.route(
        "https://api.open-meteo.com/v1/forecast?*",
        async (route) => {
            count++;
            if (count === 1)
                await route.fulfill({
                    json: {
                        daily: {
                            time: ["2026-11-19"],
                            temperature_2m_max: [18],
                            temperature_2m_min: [12],
                            precipitation_probability_max: [20],
                        },
                    },
                });
            else await route.abort();
        },
    );
    await page.getByLabel("Lugar", { exact: true }).fill("Lugar ficticio");
    await page.getByLabel("Latitud").fill("39");
    await page.getByLabel("Longitud").fill("-2");
    await page.getByRole("button", { name: "Actualizar previsión" }).click();
    await expect(
        page.getByRole("heading", { name: "Lugar ficticio" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Actualizar previsión" }).click();
    await expect(page.getByRole("status")).toContainText("Se conserva");
    await expect(page.getByText("12 a 18", { exact: false })).toBeVisible();
    expect(count).toBe(2);
    await page.goto("./#/inspiracion/1");
    await expect(page.locator(".pin")).toHaveCSS("width", "220px");
    expect(requests.some((u) => u.includes("example.org"))).toBe(false);
});
test("T04 · orientación EXIF, transparencia y nombres de variantes", async ({
    page,
}) => {
    await openModules(page);
    for (const [name, width, height, transparent] of [
        ["rotada.jpg", 24, 36, false],
        ["transparente.png", 32, 32, true],
    ]) {
        const input = (await readFile(".fixtures/" + name)).toString("base64");
        const result = await page.evaluate(
            async ({ input, name }) => {
                const photo = await modules.preparePhoto(
                    new File([Uint8Array.fromBase64(input)], name),
                );
                const first = await createImageBitmap(
                    new Blob([photo.files[0][1]]),
                );
                const c = new OffscreenCanvas(first.width, first.height),
                    ctx = c.getContext("2d");
                ctx.drawImage(first, 0, 0);
                const a = ctx.getImageData(0, 0, 1, 1).data[3];
                first.close();
                return {
                    meta: photo.meta,
                    a,
                    formats: photo.files.map(([, b]) => modules.imageFormat(b)),
                    exif: photo.files.some(([, b]) =>
                        new TextDecoder("latin1").decode(b).includes("EXIF"),
                    ),
                };
            },
            { input, name },
        );
        expect(result.meta.width).toBe(width);
        expect(result.meta.height).toBe(height);
        expect(result.a).toBe(transparent ? 0 : 255);
        expect(result.formats).toEqual(["webp", "webp", "webp"]);
        expect(result.exif).toBe(false);
        expect(result.meta.thumbnail).toBe(
            result.meta.filename.replace(".webp", "-thumb.webp"),
        );
    }
});
test("T01/T02/T03 · carpeta ajena, fallos de escritura en cada fase, esquema futuro y copia diaria", async ({
    page,
}) => {
    await openModules(page);
    const result = await page.evaluate(async () => {
        const m = modules,
            foreign = await directory("ajeno");
        await m.write(foreign, "conservar.txt", "intacto");
        try {
            await m.create(foreign, () => m.call("new"));
        } catch {}
        const notes = [];
        for (const target of ["image", "sqlite", "receipt"]) {
            for (const phase of ["open", "write", "close", "after"]) {
                const root = await directory(target + phase),
                    s = await m.create(root, () => m.call("new"));
                const original = FileSystemFileHandle.prototype.createWritable;
                let failed = false;
                FileSystemFileHandle.prototype.createWritable = async function (
                    ...args
                ) {
                    const match =
                        target === "image"
                            ? this.name.endsWith(".webp")
                            : target === "sqlite"
                              ? this.name === "b.sqlite"
                              : this.name === "b.commit.json";
                    if (!match) return original.apply(this, args);
                    const stop = () => {
                        failed = true;
                        throw new DOMException(
                            "Permiso revocado",
                            "NotAllowedError",
                        );
                    };
                    if (phase === "open") stop();
                    const stream = await original.apply(this, args);
                    return {
                        write: async (data) => {
                            if (phase === "write") stop();
                            await stream.write(data);
                        },
                        close: async () => {
                            if (phase === "close") stop();
                            await stream.close();
                            if (phase === "after") stop();
                        },
                        abort: () => stream.abort(),
                    };
                };
                try {
                    await m.commit(
                        s,
                        {
                            uuid: s.uuid,
                            revision: 1,
                            operation: crypto.randomUUID(),
                        },
                        [["INSERT INTO locations(name) VALUES ('Prueba')"]],
                        [["1".repeat(32) + ".webp", new Uint8Array([1, 2, 3])]],
                    );
                } catch {
                } finally {
                    FileSystemFileHandle.prototype.createWritable = original;
                    s.release();
                }
                const reopened = await m.connect(root);
                notes.push([target, phase, failed, reopened.head.revision]);
                reopened.release();
            }
        }
        const root = await directory("diario"),
            s = await m.create(root, () => m.call("new"));
        await Promise.all([m.daily(s), m.daily(s)]);
        await m.backup(s);
        s.release();
        const again = await m.connect(root);
        await m.daily(again);
        const backupDir = await root.getDirectoryHandle("backups"),
            names = [];
        for await (const name of backupDir.keys()) names.push(name);
        await m.commit(
            again,
            { uuid: again.uuid, revision: 1, operation: crypto.randomUUID() },
            [["INSERT INTO locations(name) VALUES ('Otro')"]],
        );
        again.release();
        const receipt = JSON.parse(
            await (await m.read(root, "catalogo/b.commit.json")).text(),
        );
        receipt.schema = 10;
        await m.write(root, "catalogo/b.commit.json", JSON.stringify(receipt));
        let future;
        try {
            await m.connect(root);
        } catch (e) {
            future = e.message;
        }
        return {
            notes,
            names,
            future,
            foreign: await (await m.read(foreign, "conservar.txt")).text(),
        };
    });
    expect(result.foreign).toBe("intacto");
    expect(result.future).toMatch(/posterior/);
    expect(result.names.filter((n) => n.startsWith("daily-"))).toHaveLength(1);
    expect(result.names.filter((n) => n.startsWith("manual-"))).toHaveLength(1);
    for (const [target, phase, failed, revision] of result.notes) {
        expect(failed).toBe(true);
        expect(revision).toBe(
            target === "receipt" && phase === "after" ? 2 : 1,
        );
    }
});
test("T04 · reparar un máster y una miniatura ausentes y reabrir la ficha", async ({
    page,
    context,
}) => {
    await testDirectory(context);
    page.on("dialog", (d) => d.accept());
    await page.goto("./");
    await page.getByRole("button", { name: "Crear armario" }).click();
    await page.getByRole("link", { name: "Ajustes", exact: true }).click();
    await page.getByLabel("Nombre de ubicación").fill("Prueba");
    await page.getByRole("button", { name: "Crear ubicación" }).click();
    await page.locator("summary", { hasText: "Prueba" }).waitFor();
    await page.getByRole("link", { name: "Catálogo", exact: true }).click();
    await page.getByRole("link", { name: "Añadir prenda" }).click();
    await page.getByLabel("Nombre", { exact: true }).fill("Dos variantes");
    const input = page.locator("input[name=photos]");
    const image = await readFile(resolve(".fixtures/red.jpg"));
    await input.setInputFiles(
        Array.from({ length: 7 }, (_, i) => ({
            name: "foto" + i + ".jpg",
            mimeType: "image/jpeg",
            buffer: image,
        })),
    );
    await page.getByRole("button", { name: "Guardar prenda" }).click();
    await expect(page.getByRole("status")).toContainText(/seis|6/);
    await input.setInputFiles(resolve(".fixtures/red.jpg"));
    await page.getByRole("button", { name: "Guardar prenda" }).click();
    await expect(
        page.getByRole("heading", { name: "Dos variantes" }),
    ).toBeVisible();
    for (const variant of [".webp", "-thumb.webp"]) {
        await page.evaluate(async (variant) => {
            const base = document
                .querySelector("img[data-photo]")
                .dataset.photo.replace(/-(preview|thumb)\.webp$/, "");
            const root = await (
                await navigator.storage.getDirectory()
            ).getDirectoryHandle("Armario de prueba");
            await (
                await root.getDirectoryHandle("images")
            ).removeEntry(base + variant);
        }, variant);
        await page.reload();
        await expect(
            page.getByText("Foto no disponible", { exact: true }),
        ).toBeVisible();
        await page
            .getByLabel("Sustituir foto")
            .setInputFiles(resolve(".fixtures/blue.jpg"));
        await page.getByRole("button", { name: "Reparar o sustituir" }).click();
        await expect(page.locator(".cover img")).toHaveCount(1);
        await page.reload();
        await expect
            .poll(() =>
                page
                    .locator(".cover img")
                    .evaluateAll((xs) => xs.some((x) => x.naturalWidth > 0)),
            )
            .toBe(true);
    }
});
