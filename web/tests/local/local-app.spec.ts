// web/tests/local/local-app.spec.ts
// The local app (Phase 5 Step 10; ADR-0013 decision 16): the packaged site as
// the local server serves it (playwright.local.config.ts). A page carries the
// packaged _headers policy and noindex, a calculator runs end to end on the
// same origin, and what only local mode offers lights up from GET /version:
// live data from a source the hosted site may not serve, and a chart of a
// concept the snapshot lacks. Each test also fails on any Content Security
// Policy violation or console error the page raises.
import { readFileSync } from "node:fs";

import type { Page } from "@playwright/test";

import { expect, test } from "../e2e/support.ts";

const SITE = new URL("../../../packages/pyeconomics-app/src/pyeconomics_app/site/", import.meta.url);

/** The policy the packaged _headers sends on every path. */
function packagedPolicy(): string {
  const line = readFileSync(new URL("_headers", SITE), "utf8")
    .split("\n")
    .find((text) => text.trimStart().startsWith("Content-Security-Policy:"));
  if (!line) throw new Error("the packaged site has no policy; run scripts/web/package_site.py");
  return line.split(": ").slice(1).join(": ").trim();
}

async function openCalculator(page: Page, path: string): Promise<void> {
  await page.goto(path);
  const section = page.locator("#calculator");
  await section.scrollIntoViewIfNeeded();
  await expect(section.locator("[data-calculator][data-ready=true]")).toBeVisible();
}

async function run(page: Page): Promise<void> {
  await page.locator("#calculator").getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Result", exact: true })).toBeFocused();
}

test("the local server serves the packaged site with its policy and noindex", async ({ page, request, watch }) => {
  for (const path of ["/", "/models/fixed-income/duration/", "/data/"]) {
    const response = await page.goto(path);
    expect(response?.status(), path).toBe(200);
    const headers = response?.headers() ?? {};
    expect(headers["content-security-policy"], path).toBe(packagedPolicy());
    expect(headers["x-robots-tag"], path).toBe("noindex");
    expect(headers["x-content-type-options"], path).toBe("nosniff");
  }
  const version = await request.get("/version.json");
  expect(await version.json()).toEqual(JSON.parse(readFileSync(new URL("version.json", SITE), "utf8")));
  const mode = await request.get("/version");
  expect(((await mode.json()) as { mode: string }).mode).toBe("local");
  expect(mode.headers()["content-security-policy"]).toBeUndefined();
  const missing = await request.get("/no-such-page/");
  expect(missing.status()).toBe(404);
  expect(await missing.text()).toBe(readFileSync(new URL("404.html", SITE), "utf8"));
  expect(missing.headers()["x-robots-tag"]).toBe("noindex");
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("a calculator runs end to end against the local server", async ({ page, watch }) => {
  await openCalculator(page, "/models/fixed-income/duration/");
  await run(page);
  const outputs = page.getByRole("table", { name: "Outputs of this run" });
  await expect(outputs.getByRole("rowheader", { name: /^macaulay_duration/ })).toBeVisible();
  await expect(page.locator("#calculator").getByRole("status")).toContainText("Done.");
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("local mode offers live data from a source the hosted site may not serve", async ({ page, watch }) => {
  // The us_spf profile reads the Philadelphia Fed's survey, which is library-only.
  await openCalculator(page, "/models/macro/policy-rule/");
  await page.getByLabel(/^Live data/).check();
  await page.locator("#calculator").getByLabel("Profile").selectOption("us_spf");
  await expect(page.locator("[data-live=local]")).toBeVisible();
  await expect(page.locator("[data-live=unserved]")).toHaveCount(0);
  const answer = page.waitForResponse((response) => response.url().includes("/v1/models/macro.policy_rule/run"));
  await run(page);
  expect((await answer).url()).toMatch(/\/v1\/models\/macro\.policy_rule\/run\?profile=us_spf$/);
  await expect(page.getByRole("heading", { name: "Sources" })).toBeVisible();
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("local mode lists every concept and charts one the snapshot lacks", async ({ page, watch }) => {
  await page.goto("/data/");
  await expect(page.locator("[data-concept-search][data-mode=local]")).toBeVisible();
  await expect(page.getByLabel("Only the series this site charts")).toHaveCount(0);
  await expect(page.locator("[data-concept='factors.ff3.us.monthly']")).toContainText("Charted on this site");

  await page.goto("/data/factors/ff3/us/monthly/");
  const section = page.locator("#chart");
  await section.scrollIntoViewIfNeeded();
  await expect(section.locator("[data-series-explorer][data-ready=fetch][data-hydrated=true]")).toBeVisible();
  await expect(page.locator("[data-offer=local]")).toHaveCount(0);
  await page.getByRole("button", { name: "Draw the chart" }).click();
  await expect(section.getByRole("status")).toContainText("Done:");
  await expect(page.locator("[data-series-chart] .main-svg").first()).toBeVisible();
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});
