// web/playwright.local.config.ts
// The local app end to end (Phase 5 Step 10; ADR-0013 decision 16): the site
// packaged into pyeconomics-app (scripts/web/package_site.py), served by the
// local server as `pyeconomics serve` serves it: local mode, the site at /
// behind the API's routes and the loopback guard, its own _headers and
// noindex on every page. tests/web/e2e_api.py --local builds that app over
// the catalog world's stand-in providers, so live data from library-only
// sources runs with no network or key. Build and package first:
// `npm run build && python ../scripts/web/package_site.py`.
import { defineConfig, devices } from "@playwright/test";

/** The port of the local server under test. */
export const LOCAL_PORT = 8798;

export default defineConfig({
  testDir: "tests/local",
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never", outputFolder: "playwright-report/local" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${String(LOCAL_PORT)}`,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `uv run --project .. --locked --all-extras python -I ../tests/web/e2e_api.py --local --port ${String(LOCAL_PORT)}`,
      url: `http://127.0.0.1:${String(LOCAL_PORT)}/healthz`,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
    },
  ],
});
