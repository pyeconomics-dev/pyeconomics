// web/playwright.config.ts
// End-to-end tests of the built site (tests/e2e/), served by `wrangler dev`
// as Workers static assets so dist/_headers applies as it does on Cloudflare
// (ADR-0013 decisions 3 and 9). Build first: `npm run build`. The calculator
// tests forward the page's /v1/ requests (tests/e2e/support.ts) to the API on
// API_PORT: tests/web/e2e_api.py, the REST app in hosted mode over the catalog
// world's stand-in providers, so live data runs with no network or key.
import { defineConfig, devices } from "@playwright/test";

import { API_PORT } from "./tests/e2e/support.ts";

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
  webServer: [
    {
      command: `npx wrangler dev --ip 127.0.0.1 --port ${PORT}`,
      url: `http://127.0.0.1:${PORT}/version.json`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: `uv run --project .. --locked --all-extras python -I ../tests/web/e2e_api.py --port ${API_PORT}`,
      url: `http://127.0.0.1:${API_PORT}/healthz`,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
    },
  ],
});
