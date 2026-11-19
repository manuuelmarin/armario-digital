import { defineConfig } from "vite";
export default defineConfig({
  base: "/armario-digital/",
  server: {
    fs: { allow: [".", "../armario/static", "../armario/migrations"] },
    hmr: false,
  },
  optimizeDeps: { include: ["sql.js", "@zip.js/zip.js/index-native.js"] },
  build: { assetsInlineLimit: 0 },
  worker: { format: "es" },
});
