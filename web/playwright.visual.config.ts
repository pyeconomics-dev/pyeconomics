// web/playwright.visual.config.ts
// The site's visual baselines (Phase 5 Step 18; ADR-0013 decision 19): the
// first screen of each of decision 19's sample pages at a phone's and a
// desktop's width, in light and in dark, compared with the pictures in
// tests/visual/baselines/. The design the dogfooding protocol's rounds arrived
// at is held by a test for each bug class they found; this holds what no such
// test can name: how the pages look.
//
// Pixels depend on the machine that draws them (fonts, the rasterizer), so the
// baselines are the Linux runner's and this runs in one CI cell, the web job.
// Elsewhere every test skips. A baseline changes only on purpose: when the web
// job's comparison fails, it draws the pictures the commit would need and
// uploads them as the `visual-baselines` artifact; AGENTS.md "Design rules"
// says how to take them in.
//
//     npm run build && npm run e2e:visual
import { defineConfig, devices } from "@playwright/test";

import { API_PORT } from "./tests/e2e/support.ts";

const PORT = 8788;

export default defineConfig({
  testDir: "tests/visual",
  // One picture per test, named by the test, with no platform in its name:
  // only one platform draws them.
  snapshotPathTemplate: "{snapshotDir}/{arg}{ext}",
  snapshotDir: process.env.VISUAL_BASELINES ?? "tests/visual/baselines",
  outputDir: "test-results/visual",
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  // In CI a missing baseline is a failure, never a file written unseen.
  updateSnapshots: process.env.CI ? "none" : "missing",
  // A failed comparison leaves its expected, actual and difference pictures
  // in test-results/visual/, which the web job uploads.
  reporter: "list",
  expect: {
    toHaveScreenshot: {
      // A count that moved by one changes a few dozen pixels; a moved line,
      // a changed colour or another font changes thousands.
      maxDiffPixels: 300,
      animations: "disabled",
      caret: "hide",
      scale: "css",
    },
  },
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "off",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], deviceScaleFactor: 1 } }],
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
