import test from "node:test";
import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import init from "sql.js";
test("Las nueve migraciones originales se ejecutan sin redefinir SQL ni perder las claves externas", async () => {
    const SQL = await init(),
        db = new SQL.Database();
    try {
        const dir = new URL("../../armario/migrations/", import.meta.url);
        const scripts = (await readdir(dir))
            .filter((p) => p.endsWith(".sql"))
            .sort();
        assert.equal(scripts.length, 9);
        db.run("PRAGMA foreign_keys=ON");
        for (const [i, path] of scripts.entries()) {
            db.exec(await readFile(new URL(path, dir), "utf8"));
            db.run("PRAGMA user_version=" + (i + 1));
        }
        assert.deepEqual(db.exec("PRAGMA foreign_key_check"), []);
        assert.throws(
            () =>
                db.run(
                    "INSERT INTO garments(name,category_id,location_id) VALUES('Prueba',1,500)",
                ),
            /FOREIGN KEY/,
        );
        assert.equal(
            db.exec("SELECT count(*) FROM locations")[0].values[0][0],
            0,
        );
    } finally {
        db.close();
    }
});
