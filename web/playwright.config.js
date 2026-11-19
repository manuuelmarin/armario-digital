import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  testMatch: "**/*.spec.mjs",
  workers: 1,
  timeout: 90000,
  use: {
    actionTimeout: 12000,
    baseURL: "http://127.0.0.1:4173/armario-digital/",
    launchOptions: process.env.BROWSER_EXECUTABLE
      ? {
          executablePath: process.env.BROWSER_EXECUTABLE,
          args: ["--no-sandbox", "--disable-dev-shm-usage"],
        }
      : {},
  },
  webServer: [
    {
      command: "node tests/build-a.mjs && node tests/pwa-server.mjs",
      url: "http://127.0.0.1:4175/armario-digital/",
    },
    {
      command: "npx vite preview --host 127.0.0.1 --port 4173 --strictPort",
      url: "http://127.0.0.1:4173/armario-digital/",
    },
    {
      command: "npx vite --host 127.0.0.1 --port 4174 --strictPort",
      url: "http://127.0.0.1:4174/armario-digital/",
    },
  ],
});
