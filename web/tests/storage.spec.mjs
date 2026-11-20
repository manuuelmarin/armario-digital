import { test, expect } from "@playwright/test";
import { openModules } from "./helpers.mjs";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { execFileSync } from "node:child_process";
test.beforeEach(async ({ page }) => openModules(page));
for (let version = 1; version <= 9; version++)
    test(
        "T05 · copia histórica de Python, esquema " + version,
        async ({ page }) => {
            const blob = (
                await readFile(".fixtures/v" + version + ".zip")
            ).toString("base64");
            const expected = JSON.parse(
                await readFile(".fixtures/v" + version + ".json", "utf8"),
            );
            const actual = await page.evaluate(
                async ({ blob, tables }) => {
                    const m = window.modules,
                        dir = await directory("importado");
                    const file = new Blob([Uint8Array.fromBase64(blob)]);
                    const s = await m.create(
                            dir,
                            async (root) =>
                                (await m.inspectZip(file, root)).data,
                        ),
                        out = {};
                    for (const table of tables)
                        out[table] = await m.call("query", s.head.data, {
                            sql: "SELECT * FROM " + table + " ORDER BY rowid",
                        });
                    const copy = await m.backup(s);
                    await m.inspectZip(copy);
                    s.release();
                    return out;
                },
                { blob, tables: Object.keys(expected) },
            );
            for (const obj of [actual, expected])
                obj.image_integrity.sort((a, b) =>
                    a.name.localeCompare(b.name),
                );
            expect(actual).toEqual(expected);
        },
    );
test("T02 · interrupción y reintento antes y después de rotar las dos generaciones", async ({
    page,
}) => {
    const result = await page.evaluate(async () => {
        const m = window.modules,
            root = await directory("reintento");
        const seed = [
            ["INSERT INTO locations(name) VALUES ('A'),('B')"],
            [
                "INSERT INTO garments(name,category_id,location_id) VALUES ('Camisa',1,1)",
            ],
        ];
        const s = await m.create(root, () =>
            m.call("new", null, { statements: seed }),
        );
        const intent = () => ({
            uuid: s.uuid,
            operation: crypto.randomUUID(),
            revision: s.head.revision,
        });
        const once = intent(),
            movement = [
                [
                    "INSERT INTO garment_movements(garment_id,from_id,to_id) VALUES(1,1,2)",
                ],
                ["UPDATE garments SET location_id=2 WHERE id=1"],
            ];
        await m.commit(s, once, movement);
        await m.commit(s, once, movement);
        for (const name of ["Una", "Dos"])
            await m.commit(s, intent(), [
                ["UPDATE garments SET name=? WHERE id=1", [name]],
            ]);
        let stale;
        try {
            await m.commit(s, once, movement);
        } catch (e) {
            stale = e.message;
        }
        const retry = intent();
        const original = FileSystemFileHandle.prototype.createWritable;
        FileSystemFileHandle.prototype.createWritable = async function (
            ...args
        ) {
            if (this.name.endsWith(".commit.json"))
                throw new DOMException("Sin espacio", "QuotaExceededError");
            return original.apply(this, args);
        };
        let failure;
        try {
            await m.commit(s, retry, [
                ["UPDATE garments SET name='Incompleta'"],
            ]);
        } catch (e) {
            failure = e.name;
        } finally {
            FileSystemFileHandle.prototype.createWritable = original;
        }
        s.release();
        const reopened = await m.connect(root);
        const rows = await m.call("query", reopened.head.data, {
            sql: "SELECT name,location_id,(SELECT count(*) FROM garment_movements) moves FROM garments",
        });
        reopened.release();
        return { stale, failure, rows, damaged: reopened.damaged };
    });
    expect(result.stale).toMatch(/revisión/);
    expect(result.failure).toBe("QuotaExceededError");
    expect(result.rows).toEqual([{ name: "Dos", location_id: 2, moves: 1 }]);
    expect(result.damaged).toBe(true);
});
test("T03 · creación concurrente y restauración comparten el bloqueo inicial", async ({
    page,
    context,
}) => {
    const tab = await context.newPage();
    await openModules(tab);
    const fixture = (await readFile(".fixtures/v9.zip")).toString("base64");
    const run = (p, restore) =>
        p.evaluate(
            async ({ fixture, restore }) => {
                const m = modules,
                    root = await directory("compartido");
                try {
                    window.session = await m.create(root, async (dest) =>
                        restore
                            ? (
                                  await m.inspectZip(
                                      new Blob([
                                          Uint8Array.fromBase64(fixture),
                                      ]),
                                      dest,
                                  )
                              ).data
                            : m.call("new"),
                    );
                    return "writer";
                } catch (e) {
                    return e.message;
                }
            },
            { fixture, restore },
        );
    const results = await Promise.all([run(tab, true), run(page, false)]);
    expect(results.filter((x) => x === "writer")).toHaveLength(1);
    expect(results.join(" ")).toContain("contiene archivos");
    const loser = results[0] === "writer" ? page : tab;
    expect(
        await loser.evaluate(async () => {
            const s = await modules.connect(await directory("compartido"));
            return [s.head.revision, s.release === null];
        }),
    ).toEqual([1, true]);
});
test("T06 · copias inválidas se rechazan sin activar el destino", async ({
    page,
}) => {
    const { readdir } = await import("node:fs/promises");
    const files = (await readdir(".fixtures")).filter((f) =>
        f.startsWith("invalid-"),
    );
    expect(files.length).toBeGreaterThanOrEqual(8);
    for (const file of files) {
        const blob = (await readFile(".fixtures/" + file)).toString("base64");
        const result = await page.evaluate(async (blob) => {
            try {
                await modules.inspectZip(
                    new Blob([Uint8Array.fromBase64(blob)]),
                );
                return "ACEPTADA";
            } catch (e) {
                return e.message;
            }
        }, blob);
        expect(result, file).not.toBe("ACEPTADA");
    }
});
test("T08 · ZIP Python migrado con foto nueva vuelve a Python con sus hashes", async ({
    page,
}, info) => {
    const blob = (await readFile(".fixtures/v3.zip")).toString("base64"),
        jpeg = (await readFile(".fixtures/red.jpg")).toString("base64");
    const exported = await page.evaluate(
        async ({ blob, jpeg }) => {
            const m = modules,
                root = await directory("original");
            const s = await m.create(
                root,
                async (dest) =>
                    (
                        await m.inspectZip(
                            new Blob([Uint8Array.fromBase64(blob)]),
                            dest,
                        )
                    ).data,
            );
            const p = await m.preparePhoto(
                    new File([Uint8Array.fromBase64(jpeg)], "IMG_4831.jpg"),
                ),
                cols = Object.keys(p.meta);
            await m.commit(
                s,
                {
                    operation: crypto.randomUUID(),
                    revision: s.head.revision,
                    uuid: s.uuid,
                },
                [
                    [
                        "INSERT INTO garment_images(garment_id," +
                            cols.join(",") +
                            ") VALUES(1," +
                            cols.map(() => "?").join(",") +
                            ")",
                        Object.values(p.meta),
                    ],
                    ...p.integrity,
                ],
                p.files,
            );
            const copy = await m.backup(s),
                restored = await m.create(
                    await directory("segunda"),
                    async (dest) => (await m.inspectZip(copy, dest)).data,
                );
            const rows = await m.call("query", restored.head.data, {
                sql: "SELECT filename,preview,thumbnail FROM garment_images ORDER BY id",
            });
            s.release();
            restored.release();
            return {
                zip: new Uint8Array(await copy.arrayBuffer()).toBase64(),
                rows,
            };
        },
        { blob, jpeg },
    );
    expect(exported.rows).toHaveLength(2);
    expect(exported.rows[0].preview).toBe(null);
    expect(exported.rows[1].filename).toMatch(/^[0-9a-f]{32}\.webp$/);
    const { writeFile } = await import("node:fs/promises"),
        file = info.outputPath("regreso.zip");
    await writeFile(file, Buffer.from(exported.zip, "base64"));
    execFileSync(
        process.env.PYTHON || "python",
        ["tests/oracle.py", "roundtrip", file],
        { cwd: resolve(".") },
    );
});
test("T03 · una sesión cerrada no puede volver a escribir", async ({
    page,
}) => {
    await openModules(page);
    const message = await page.evaluate(async () => {
        const s = await modules.create(await directory("cerrada"), () =>
            modules.call("new"),
        );
        s.release();
        try {
            await modules.commit(
                s,
                { uuid: s.uuid, revision: 1, operation: crypto.randomUUID() },
                [],
            );
        } catch (e) {
            return e.message;
        }
    });
    expect(message).toMatch(/solo lectura/);
});
test("T02 · tras un conflicto se puede revisar la última versión y guardar", async ({
    page,
}) => {
    const result = await page.evaluate(async () => {
        const m = modules,
            s = await m.create(await directory("conflicto"), () =>
                m.call("new"),
            );
        const intent = () => ({
            uuid: s.uuid,
            revision: s.head.revision,
            operation: crypto.randomUUID(),
        });
        const old = s.head,
            stale = intent();
        await m.commit(s, intent(), [
            ["INSERT INTO locations(name) VALUES ('Actual')"],
        ]);
        s.head = old;
        let conflict = false;
        try {
            await m.commit(s, stale, [["UPDATE locations SET name='Antigua'"]]);
        } catch (e) {
            conflict = e instanceof m.StaleRevisionError;
        }
        const current = await m.call("query", s.head.data, {
            sql: "SELECT name FROM locations",
        });
        await m.commit(s, intent(), [["UPDATE locations SET name='Revisada'"]]);
        s.release();
        const reopened = await m.connect(s.root);
        const final = await m.call("query", reopened.head.data, {
            sql: "SELECT name FROM locations",
        });
        reopened.release();
        return { conflict, current, final };
    });
    expect(result).toEqual({
        conflict: true,
        current: [{ name: "Actual" }],
        final: [{ name: "Revisada" }],
    });
});
test("T08 · repara la copia diaria vacía y conserva una copia dañada con datos", async ({
    page,
}) => {
    const result = await page.evaluate(async () => {
        const m = modules,
            root = await directory("diaria-interrumpida"),
            s = await m.create(root, () => m.call("new"));
        const day = new Date().toISOString().slice(0, 10),
            path = "backups/daily-" + day + ".zip";
        await m.write(root, path, new Uint8Array());
        await m.daily(s);
        await m.inspectZip(await m.read(root, path));
        s.release();
        const reopened = await m.connect(root);
        await m.write(root, path, "incompleta");
        let error;
        try {
            await m.daily(reopened);
        } catch (e) {
            error = e.message;
        }
        reopened.release();
        return { error, remaining: await (await m.read(root, path)).text() };
    });
    expect(result.error).toContain("fuera de backups");
    expect(result.remaining).toBe("incompleta");
});
test("T04 · el catálogo lee cada miniatura cuando entra en pantalla", async ({
    page,
}) => {
    await page.evaluate(async () => {
        const ui = await import("/armario-digital/src/ui.js"),
            root = await directory("miniaturas");
        const canvas = new OffscreenCanvas(20, 20);
        canvas.getContext("2d").fillRect(0, 0, 20, 20);
        const photo = await canvas.convertToBlob({
            type: "image/webp",
        });
        for (const name of ["primera", "segunda"])
            await modules.write(root, "images/" + name + ".webp", photo);
        ui.state.session = { root };
        const getFile = FileSystemDirectoryHandle.prototype.getFileHandle;
        window.reads = [];
        FileSystemDirectoryHandle.prototype.getFileHandle = function (
            name,
            ...args
        ) {
            window.reads.push(name);
            return getFile.call(this, name, ...args);
        };
        document.body.innerHTML = ["primera", "segunda"]
            .map(
                (name, i) =>
                    '<article class="card" style="height:3000px"><a href="#/prendas/' +
                    i +
                    '"><img width="60" height="60" data-photo="' +
                    name +
                    '.webp"></a></article>',
            )
            .join("");
        await ui.hydrate();
    });
    const images = page.locator("img");
    await expect
        .poll(() => images.first().evaluate((el) => el.naturalWidth))
        .toBe(20);
    expect(await page.evaluate(() => window.reads)).toEqual(["primera.webp"]);
    await images.last().scrollIntoViewIfNeeded();
    await expect
        .poll(() => images.last().evaluate((el) => el.naturalWidth))
        .toBe(20);
    expect(await page.evaluate(() => window.reads)).toEqual([
        "primera.webp",
        "segunda.webp",
    ]);
});
