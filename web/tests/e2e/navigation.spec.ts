// web/tests/e2e/navigation.spec.ts
// Navigation (Phase 5 Step 7; ADR-0013 decision 10): the header's fifteen
// domain sections, as a row on a wide screen and a disclosure menu on a small
// one, both worked from the keyboard; the /models/ filters, worked from the
// keyboard, kept in the query string, counted from the registry and the seed,
// and reading the query string as data only; and axe at WCAG 2.2 AA on
// /models/ with filters applied, /coverage/ and an empty-state domain page.
import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { DOMAINS, domainPath } from "../../src/lib/paths.ts";
import { MODELS, SEED } from "./catalog.ts";
import { expect, test } from "./support.ts";

/** Wait for the /models/ filter island to hydrate and read the address. */
async function filtersReady(page: Page): Promise<void> {
  await expect(page.locator('[data-model-filters][data-ready="true"]')).toBeAttached();
}

const AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function axe(page: Page): Promise<string[]> {
  const found: string[] = [];
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    const results = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
    found.push(...results.violations.map((violation) => `${colorScheme} ${violation.id}: ${violation.help}`));
  }
  return found;
}

test("a wide screen shows the fifteen domain sections in the header, reachable by Tab", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/");
  const row = page.getByRole("navigation", { name: "Domains" }).locator("[data-domains-row]");
  const links = row.getByRole("link");
  await expect(links).toHaveCount(15);
  expect(await links.evaluateAll((elements) => elements.map((element) => element.getAttribute("href")))).toEqual(
    DOMAINS.map((domain) => domainPath(domain.id)),
  );
  await expect(page.locator("[data-domains-menu]")).toBeHidden();
  const first = links.first();
  for (let presses = 0; presses < 30 && !(await first.evaluate((element) => element === document.activeElement)); presses += 1) {
    await page.keyboard.press("Tab");
  }
  await expect(first).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/models\/foundations\/$/);
  await expect(row.getByRole("link", { name: "Foundations" })).toHaveAttribute("aria-current", "page");
});

test("a small screen puts the sections in a disclosure menu the keyboard opens", async ({ page, watch }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/coverage/");
  await expect(page.locator("[data-domains-row]")).toBeHidden();
  const summary = page.locator("[data-domains-menu] > summary");
  await summary.focus();
  await page.keyboard.press("Enter");
  const menu = page.locator("[data-domains-menu]");
  await expect(menu).toHaveAttribute("open", "");
  const micro = menu.getByRole("link", { name: "Microeconomics" });
  await expect(micro).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(menu.getByRole("link", { name: "Foundations" })).toBeFocused();
  await micro.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/models\/micro\/$/);
  expect(await axe(page)).toEqual([]);
  expect(watch.violations).toEqual([]);
});

test("an empty-state domain page says Phase 7, links /coverage/ and passes axe", async ({ page, watch }) => {
  for (const path of ["/models/micro/", "/models/alternatives/"]) {
    await page.goto(path);
    await expect(page.locator("[data-empty-domain]")).toContainText("Phase 7");
    await expect(page.locator("[data-empty-domain]").getByRole("link", { name: "coverage matrix" })).toHaveAttribute(
      "href",
      "/coverage/",
    );
    expect(await axe(page)).toEqual([]);
  }
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("/coverage/ passes axe", async ({ page, watch }) => {
  await page.goto("/coverage/");
  await expect(page.getByRole("heading", { name: "By domain" })).toBeVisible();
  expect(await axe(page)).toEqual([]);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

/** How many models a filter on domain and evidence leaves, from the registry. */
function expected(domain: string, evidence: string): number {
  return MODELS.filter((model) => model.domain === domain && model.evidence === evidence).length;
}

test("a filtered /models/ URL renders the registry's count and passes axe", async ({ page, watch }) => {
  await page.goto("/models/?domain=fixed-income&evidence=standard");
  await filtersReady(page);
  const count = expected("fixed_income", "standard");
  await expect(page.locator("[data-filter-count]")).toHaveAttribute("data-filter-count", String(count));
  await expect(page.locator("[data-model-list] > li")).toHaveCount(count);
  await expect(page.locator("#filter-domain")).toHaveValue("fixed-income");
  expect(await axe(page)).toEqual([]);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("the filters work from the keyboard and keep their state in the query string", async ({ page }) => {
  await page.goto("/models/");
  await filtersReady(page);
  await expect(page.locator("[data-model-list] > li")).toHaveCount(MODELS.length);
  await page.locator("#filter-topic").focus();
  // The first syllabus topic any model implements, by the seed.
  await page.keyboard.press("ArrowDown");
  const topic = await page.locator("#filter-topic").inputValue();
  expect(topic).not.toBe("");
  const count = [...SEED.values()].filter((topics) => topics.includes(topic)).length;
  await expect(page).toHaveURL((url) => url.pathname === "/models/" && url.search === `?topic=${topic}`);
  await expect(page.locator("[data-model-list] > li")).toHaveCount(count);
  await page.keyboard.press("Tab");
  await expect(page.locator("#filter-evidence")).toBeFocused();
  await page.goto(`/models/?topic=${topic}`);
  await filtersReady(page);
  await expect(page.locator("#filter-topic")).toHaveValue(topic);
  await expect(page.locator("[data-model-list] > li")).toHaveCount(count);
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(page).toHaveURL(/\/models\/$/);
  await expect(page.locator("[data-model-list] > li")).toHaveCount(MODELS.length);
});

test("the filters read the query string as data only", async ({ page, watch }) => {
  await page.goto(`/models/?domain=${encodeURIComponent("<img src=x onerror=alert(1)>")}&tag=no-such-tag&cost=light`);
  await filtersReady(page);
  await expect(page.locator("#filter-cost")).toHaveValue("light");
  await expect(page.locator("#filter-domain")).toHaveValue("");
  await expect(page.locator("#filter-tag")).toHaveValue("");
  expect(await page.locator("main img").count()).toBe(0);
  await expect(page.locator("[data-model-list] > li")).toHaveCount(MODELS.filter((model) => model.cost === "light").length);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});
