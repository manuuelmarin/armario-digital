import { defineConfig } from "vite";
export default defineConfig({
  base: "/armario-digital/",
  build: { assetsInlineLimit: 0 },
  worker: { format: "es" },
});
