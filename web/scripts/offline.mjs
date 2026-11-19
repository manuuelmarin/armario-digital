import { readdir, readFile, writeFile } from "node:fs/promises";
import { relative, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
const root = new URL("../dist/", import.meta.url);
const files = (await readdir(root, { recursive: true, withFileTypes: true }))
    .filter((e) => e.isFile() && e.name !== "sw.js")
    .map((e) =>
        relative(fileURLToPath(root), join(e.parentPath, e.name)).replaceAll(
            "\\",
            "/",
        ),
    )
    .sort();
const hash = createHash("sha256");
for (const name of files)
    hash.update(name).update(await readFile(new URL(name, root)));
const template = await readFile(
    new URL("./sw.template.js", import.meta.url),
    "utf8",
);
await writeFile(
    new URL("sw.js", root),
    template
        .replace("__REVISION__", hash.digest("hex").slice(0, 20))
        .replace('["__ASSETS__"]', JSON.stringify(files)),
);
