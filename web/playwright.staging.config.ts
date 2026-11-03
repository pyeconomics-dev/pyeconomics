// web/playwright.staging.config.ts
// The deployed calculator, data explorer and user-data upload on staging
// (Phase 5 Steps 6 and 9): tests/staging/ against
// STAGING_BASE_URL (https://staging.pyeconomics.dev by default), through
// Cloudflare Access with the service token in CF_ACCESS_CLIENT_ID and
// CF_ACCESS_CLIENT_SECRET, which the browser sends with every request of the
// site's one origin and the edge Worker strips before the API. No local
// server starts. deploy-staging.yml's site job runs it after each deploy:
//
//     npx playwright test --config playwright.staging.config.ts
import { defineConfig, devices } from "@playwright/test";

const id = process.env.CF_ACCESS_CLIENT_ID ?? "";
const secret = process.env.CF_ACCESS_CLIENT_SECRET ?? "";

export default defineConfig({
  testDir: "tests/staging",
  forbidOnly: Boolean(process.env.CI),
  retries: 1,
  reporter: "list",
  use: {
    baseURL: process.env.STAGING_BASE_URL ?? "https://staging.pyeconomics.dev",
    extraHTTPHeaders: id && secret ? { "CF-Access-Client-Id": id, "CF-Access-Client-Secret": secret } : {},
    trace: "off",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
