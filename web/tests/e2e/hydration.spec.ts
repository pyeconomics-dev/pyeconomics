// web/tests/e2e/hydration.spec.ts
// What a visitor does before an island has loaded is not lost (Phase 5 Step
// 18; round 0 of the dogfooding protocol found typing on /data/ lost when its
// filter loaded, and round 1 a "Draw the chart" that did nothing until the
// explorer had). The class, not the instance: the site's scripts are held
// back, as a slow connection holds them; the visitor types and chooses in each
// form the build rendered; the scripts are released; and every entry must
// still be there and be applied. A control that cannot work before its island
// is disabled until then.
import type { Page } from "@playwright/test";

import { expect, test } from "./support.ts";

/** Hold every script of the site back until `release` is called. */
async function holdScripts(page: Page): Promise<() => void> {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/_astro/**/*.js", async (route) => {
    await gate;
    await route.continue();
  });
  return release;
}

test("/data/ keeps what was typed and chosen before its search loaded", async ({ page, api }) => {
  const release = await holdScripts(page);
  await page.goto("/data/", { waitUntil: "domcontentloaded" });
  await expect(page.locator("[data-concept-search][data-ready=false]")).toBeVisible();
  await page.getByLabel("Search the series").fill("unemployment");
  await page.getByLabel("Frequency").selectOption("monthly");
  release();
  await expect(page.locator("[data-concept-search][data-ready=true]")).toBeVisible();
  await expect(page.getByLabel("Search the series")).toHaveValue("unemployment");
  await expect(page.getByLabel("Frequency")).toHaveValue("monthly");
  const shown = page.locator("[data-concept-list] [data-concept]");
  await expect(shown.first()).toHaveAttribute("data-concept", "us.unemployment.rate");
  await expect(page.getByRole("status").filter({ hasText: "series match" })).toBeVisible();
  expect(api.requests).toEqual([]);
});

test("/models/ keeps a filter chosen before its filters loaded", async ({ page }) => {
  const release = await holdScripts(page);
  await page.goto("/models/", { waitUntil: "domcontentloaded" });
  await expect(page.locator("[data-model-filters][data-ready=false]")).toBeVisible();
  await page.locator("#filter-domain").selectOption("fixed-income");
  release();
  await expect(page.locator("[data-model-filters][data-ready=true]")).toBeVisible();
  await expect(page.locator("#filter-domain")).toHaveValue("fixed-income");
  await expect(page).toHaveURL(/\?domain=fixed-income$/);
  const shown = page.locator("[data-model-list] [data-model]");
  expect(await shown.count()).toBeGreaterThan(0);
  for (const id of await shown.evaluateAll((items) => items.map((item) => item.getAttribute("data-model") ?? ""))) {
    expect(id).toMatch(/^fixed_income\./);
  }
});

test("/search/ searches for what was typed before its island loaded", async ({ page }) => {
  const release = await holdScripts(page);
  await page.goto("/search/", { waitUntil: "domcontentloaded" });
  await page.getByRole("main").getByRole("searchbox").fill("sharpe");
  release();
  await expect(page.getByRole("main").getByRole("searchbox")).toHaveValue("sharpe");
  await expect(page.locator("[data-search-status]")).toContainText("for “sharpe”");
  await expect(page.locator("[data-search-hit]").first()).toBeVisible();
});

test("the header's search box keeps what was typed before it loaded", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const release = await holdScripts(page);
  await page.goto("/coverage/", { waitUntil: "domcontentloaded" });
  const box = page.getByRole("banner").getByRole("searchbox");
  await box.fill("duration");
  release();
  await expect(page.getByRole("banner").locator("[data-search-hit]").first()).toBeVisible();
  await expect(box).toHaveValue("duration");
});

test("the explorer's button waits for the explorer, which then draws the chart unasked", async ({ page, api }) => {
  const release = await holdScripts(page);
  await page.goto("/data/us/unemployment/rate/", { waitUntil: "domcontentloaded" });
  const section = page.locator("#chart");
  await section.scrollIntoViewIfNeeded();
  // Before the island loads, the button could only reload the page: it is off.
  await expect(section.getByRole("button", { name: "Draw the chart" })).toBeDisabled();
  expect(api.requests).toEqual([]);
  release();
  await expect(section.locator("[data-series-explorer][data-hydrated=true]")).toBeVisible();
  await expect(section.locator("[data-series-chart] .main-svg").first()).toBeVisible();
  await expect(section.getByRole("button", { name: "Draw the chart" })).toBeEnabled();
  expect(api.requests).toHaveLength(1);
});

test("a calculator loads when any part of its card comes into view, not only its top", async ({ page }) => {
  await page.goto("/models/fixed-income/bond-pricing/");
  // Arrive from below: the citations first, then up into the card's lower part.
  await page.locator("#citations").scrollIntoViewIfNeeded();
  await expect(page.locator('[data-calculator][data-ready="true"]')).toHaveCount(0);
  const card = page.locator(".calculator-card");
  const box = await card.boundingBox();
  expect(box?.height ?? 0).toBeGreaterThan(900);
  await page.evaluate((bottom) => window.scrollTo(0, bottom - 300), (box?.y ?? 0) + (box?.height ?? 0) + (await page.evaluate(() => window.scrollY)));
  await expect(page.locator('[data-calculator][data-ready="true"]')).toBeVisible();
});
