// web/playwright.config.ts
// End-to-end tests of the built site (tests/e2e/), served by `wrangler dev`
// as Workers static assets so dist/_headers applies as it does on Cloudflare
// (ADR-0013 decisions 3 and 9). Build first: `npm run build`.
import { defineConfig, devices } from "@playwright/test";

const PORT = 8788;

export default defineConfig({
  testDir: "tests/e2e",
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `npx wrangler dev --ip 127.0.0.1 --port ${PORT}`,
    url: `http://127.0.0.1:${PORT}/version.json`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
