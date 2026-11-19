import initSqlJs, { type Database, type SqlValue } from "sql.js";
import wasm from "sql.js/dist/sql-wasm-browser.wasm?url";
const migrations = Object.entries(
    import.meta.glob("../../armario/migrations/*.sql", {
        query: "?raw",
        import: "default",
        eager: true,
    }),
)
    .sort()
    .map(([, source]) => String(source));
const engine = initSqlJs({ locateFile: () => wasm });
type Params = SqlValue[];
export const latest = migrations.length;
export async function open(bytes?: Uint8Array) {
    const db = new (await engine).Database(bytes);
    db.run("PRAGMA trusted_schema=OFF; PRAGMA foreign_keys=ON");
    db.create_function("fold", (s: unknown) =>
        String(s ?? "")
            .normalize("NFKD")
            .replace(/\p{M}/gu, "")
            .toLowerCase()
            .replaceAll("ß", "ss"),
    );
    return db;
}
export function rows(db: Database, sql: string, params: Params = []) {
    const stmt = db.prepare(sql);
    try {
        stmt.bind(params);
        const records = [];
        while (stmt.step()) records.push(stmt.getAsObject());
        return records;
    } finally {
        stmt.free();
    }
}
function value(db: Database, sql: string) {
    return db.exec(sql)[0]?.values[0][0];
}
export function migrate(
    db: Database,
    from: number,
    until = latest,
    hashes: Record<string, string> = {},
) {
    for (let version = from + 1; version <= until; version++) {
        db.run("BEGIN");
        try {
            db.exec(migrations[version - 1]);
            if (version === 5)
                for (const [filename, hash] of Object.entries(hashes))
                    db.run("INSERT INTO image_integrity VALUES (?,?)", [
                        filename,
                        hash,
                    ]);
            if (rows(db, "PRAGMA foreign_key_check").length)
                throw Error("Relaciones inválidas tras migrar.");
            db.run("PRAGMA user_version=" + version + "; COMMIT");
        } catch (error) {
            db.run("ROLLBACK");
            throw error;
        }
    }
}
const contracts = new Map<number, string>();
function structure(db: Database) {
    const tables = rows(
        db,
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name",
    );
    return JSON.stringify(
        tables.map(({ name }) => {
            if (!/^[a-z_]+$/.test(String(name)))
                throw Error("Tabla desconocida.");
            return [
                name,
                rows(db, "PRAGMA table_info(" + name + ")"),
                rows(db, "PRAGMA foreign_key_list(" + name + ")"),
            ];
        }),
    );
}
export async function inspect(db: Database) {
    const version = Number(value(db, "PRAGMA user_version"));
    if (!Number.isInteger(version) || version < 1 || version > latest)
        throw Error("Versión de SQLite incompatible. Actualiza la aplicación.");
    if (!contracts.has(version)) {
        const reference = await open();
        try {
            migrate(reference, 0, version);
            contracts.set(version, structure(reference));
        } finally {
            reference.close();
        }
    }
    if (contracts.get(version) !== structure(db))
        throw Error(
            "Las columnas o claves externas difieren del esquema original.",
        );
    if (
        value(db, "PRAGMA integrity_check") !== "ok" ||
        rows(db, "PRAGMA foreign_key_check").length
    )
        throw Error("Catálogo dañado o relaciones huérfanas.");
    const files = new Set<string>();
    for (const table of version >= 7
        ? ["garment_images", "board_items"]
        : ["garment_images"]) {
        for (const row of rows(
            db,
            "SELECT filename,thumbnail" +
                (version >= 3 ? ",preview" : "") +
                " FROM " +
                table,
        ))
            for (const name of Object.values(row))
                if (name !== null) {
                    if (
                        typeof name !== "string" ||
                        !/^[a-f0-9]{32}(?:-thumb|-preview)?\.webp$/.test(name)
                    )
                        throw Error("Nombre de imagen no válido.");
                    files.add(name);
                }
    }
    const hashes =
        version >= 5
            ? Object.fromEntries(
                  rows(db, "SELECT name,sha256 FROM image_integrity").map(
                      (r) => [String(r.name), String(r.sha256)],
                  ),
              )
            : {};
    return {
        version,
        files: [...files],
        hashes,
        garments: value(db, "SELECT count(*) FROM garments"),
        outfits: value(db, "SELECT count(*) FROM outfits"),
    };
}
