import { build } from "vite";
import { resolve } from "node:path";
import { execFileSync } from "node:child_process";
await build({
    base: "/armario-digital/",
    define: { "import.meta.env.VITE_RELEASE": JSON.stringify("ensayo-a") },
    build: { outDir: resolve(".fixtures/build-a"), emptyOutDir: true },
});
execFileSync(process.execPath, ["scripts/offline.mjs", ".fixtures/build-a"]);
