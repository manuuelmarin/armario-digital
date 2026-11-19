import { open, inspect, migrate, rows, latest } from "./catalog";
self.onmessage = async ({ data }) => {
    const { id, kind, bytes, statements = [], hashes } = data;
    let db;
    try {
        db = await open(bytes);
        let result;
        if (kind === "inspect") result = await inspect(db);
        else if (kind === "query") result = rows(db, data.sql, data.params);
        else {
            if (kind === "new" || kind === "upgrade")
                migrate(
                    db,
                    kind === "new" ? 0 : (await inspect(db)).version,
                    latest,
                    hashes,
                );
            if (kind === "write" || kind === "new") {
                db.run("BEGIN");
                for (const [sql, params = []] of statements)
                    db.run(sql, params);
                db.run("COMMIT");
            }
            result = db.export();
        }
        self.postMessage({ id, result });
    } catch (error) {
        self.postMessage({
            id,
            error: String(error instanceof Error ? error.message : error),
        });
    } finally {
        db?.close();
    }
};
