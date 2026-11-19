import { test as base, chromium } from "@playwright/test";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
export { expect } from "@playwright/test";
// A normal on-disk browser profile exercises persisted directory handles across navigation.
export const test = base.extend({
    context: async ({}, use, info) => {
        const profile = await mkdtemp(join(tmpdir(), "ad-"));
        const options = info.project.use;
        const ctx = await chromium.launchPersistentContext(profile, {
            ...options.launchOptions,
            channel: process.env.ARMARIO_BROWSER_CHANNEL || undefined,
            baseURL: options.baseURL,
            viewport: { width: 1440, height: 900 },
        });
        try {
            await use(ctx);
        } finally {
            await ctx.close();
            await rm(profile, {
                recursive: true,
                force: true,
                maxRetries: 5,
                retryDelay: 250,
            });
        }
    },
});
