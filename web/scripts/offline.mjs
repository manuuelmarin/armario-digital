import { readdir, readFile, writeFile, copyFile } from "node:fs/promises";
import { relative, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
const root = process.argv[2]
    ? resolve(process.argv[2])
    : fileURLToPath(new URL("../dist", import.meta.url));
for (const name of ["OFL-DM-Sans.txt", "OFL-DM-Serif-Display.txt"])
    await copyFile(
        new URL("../../armario/static/fonts/" + name, import.meta.url),
        join(root, name),
    );
const files = (await readdir(root, { recursive: true, withFileTypes: true }))
    .filter((e) => e.isFile() && e.name !== "sw.js")
    .map((e) =>
        relative(root, join(e.parentPath, e.name)).replaceAll("\\", "/"),
    )
    .sort();
const template = await readFile(
    new URL("./sw.template.js", import.meta.url),
    "utf8",
);
const hash = createHash("sha256").update(template);
for (const name of files)
    hash.update(name).update(await readFile(join(root, name)));
await writeFile(
    join(root, "sw.js"),
    template
        .replace("__REVISION__", hash.digest("hex").slice(0, 20))
        .replace('["__ASSETS__"]', JSON.stringify(files)),
);
