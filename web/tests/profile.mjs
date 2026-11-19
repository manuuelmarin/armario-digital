import { test as base, chromium } from "@playwright/test";
export { expect } from "@playwright/test";
// A normal on-disk browser profile exercises persisted directory handles across navigation.
export const test = base.extend({
    context: async ({}, use, info) => {
        const profile = info.outputPath("browser-profile");
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
        }
    },
});
