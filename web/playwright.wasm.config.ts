// web/playwright.wasm.config.ts
// The documentation's in-browser examples (tests/wasm/), which need a server but
// no site of this project: build the documentation first, and Python's own server
// hands out what `sphinx-build` wrote. Set WASM_BASE_URL (with its trailing slash)
// to check a deployed copy instead, as Phase 5 Step 12's Deployed & verified does.
import { defineConfig, devices } from "@playwright/test";

const PORT = 8797;
const deployed = process.env.WASM_BASE_URL;

export default defineConfig({
  testDir: "tests/wasm",
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  // One at a time: each page compiles Python and loads its wheels.
  workers: 1,
  timeout: 240_000,
  reporter: "list",
  use: {
    baseURL: deployed ?? `http://127.0.0.1:${PORT}/wasm/`,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: deployed
    ? undefined
    : {
        command: `uv run --no-project python -I -m http.server ${PORT} --bind 127.0.0.1 --directory ../docs/_build/html`,
        url: `http://127.0.0.1:${PORT}/wasm/time-value.html`,
        reuseExistingServer: !process.env.CI,
        timeout: 60_000,
        // http.server logs each of a page's hundreds of requests.
        stderr: "ignore",
      },
});
