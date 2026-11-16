// web/tests/dogfood/playwright.config.ts
// The dogfooding harness (docs/design/dogfooding.md section 5): every page
// type at three widths in both themes, and the scripted task states, into the
// git-ignored web/dogfood-out/<run>/. Not part of the end-to-end run, whose
// testDir is tests/e2e. Chromium is launched without --hide-scrollbars, so
// scrollbars are drawn as on Windows, where #319 showed. Against the local
// build it starts `wrangler dev` and the e2e API as the end-to-end tests do,
// or reuses them; with DOGFOOD_BASE_URL it starts nothing and reads that site,
// through Cloudflare Access when CF_ACCESS_CLIENT_ID and
// CF_ACCESS_CLIENT_SECRET are set (sent as headers only, never printed).
//
//     npm run build && npm run dogfood
import { defineConfig, devices } from "@playwright/test";

import { API_ORIGIN, BASE_URL, LAUNCH, LOCAL, LOCAL_ORIGIN, accessHeaders } from "./support.ts";

// One name for the run, read by every worker from the environment.
process.env.DOGFOOD_RUN ??= new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);

export default defineConfig({
  testDir: ".",
  testMatch: /\.spec\.ts$/,
  fullyParallel: true,
  workers: process.env.CI ? 2 : 4,
  retries: 0,
  timeout: 120_000,
  reporter: "list",
  globalTeardown: "./teardown.ts",
  outputDir: "../../test-results/dogfood",
  use: {
    baseURL: BASE_URL,
    extraHTTPHeaders: accessHeaders(),
    trace: "off",
    screenshot: "off",
    video: "off",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], launchOptions: LAUNCH } }],
  webServer: LOCAL
    ? [
        {
          command: "npx wrangler dev --ip 127.0.0.1 --port 8788",
          url: `${LOCAL_ORIGIN}/version.json`,
          cwd: "../..",
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
        {
          command: "uv run --project .. --locked --all-extras python -I ../tests/web/e2e_api.py --port 8799",
          url: `${API_ORIGIN}/healthz`,
          cwd: "../..",
          reuseExistingServer: !process.env.CI,
          timeout: 180_000,
        },
      ]
    : undefined,
});
