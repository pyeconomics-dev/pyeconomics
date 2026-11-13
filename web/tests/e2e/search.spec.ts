// web/tests/e2e/search.spec.ts
// Search (Phase 5 Step 7; ADR-0013 decision 10) against the built index,
// served by `wrangler dev` with decision 9's headers: Pagefind's own API finds
// every model by its title and by its id; /search/ and the header box show
// results with a model's domain and summary; no request leaves the site; and
// /search/ with results passes axe with no policy violation or console error.
import AxeBuilder from "@axe-core/playwright";

import { modelPath } from "../../src/lib/paths.ts";
import { expect, test, useColorScheme } from "./support.ts";
import { MODELS } from "./catalog.ts";

const AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

/** How far down the hits a model may be and still count as found. */
const TOP = 5;

test("Pagefind's API finds every model by its title and by its id", async ({ page, watch }) => {
  await page.goto("/search/");
  const queries = MODELS.flatMap((model) => [
    { query: model.title, path: modelPath(model.id), by: "title" },
    { query: model.id, path: modelPath(model.id), by: "id" },
  ]);
  const found = await page.evaluate(
    async ({ queries, top }) => {
      // A URL the page serves, which the type checker cannot resolve.
      const bundle = "/pagefind/pagefind.js";
      const pagefind = (await import(/* @vite-ignore */ bundle)) as {
        init: () => Promise<void>;
        search: (q: string) => Promise<{ results: { data: () => Promise<{ url: string }> }[] }>;
      };
      await pagefind.init();
      const missed: string[] = [];
      for (const { query, path, by } of queries) {
        const response = await pagefind.search(query);
        const urls = await Promise.all(response.results.slice(0, top).map(async (result) => (await result.data()).url));
        if (!urls.includes(path)) missed.push(`${by} "${query}" -> ${urls.join(", ")}`);
      }
      return missed;
    },
    { queries, top: TOP },
  );
  expect(found).toEqual([]);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("/search/ lists results with a model's domain and summary, sends nothing off the site, and passes axe", async ({
  page,
  watch,
}) => {
  const requests: string[] = [];
  page.on("request", (request) => requests.push(request.url()));
  await page.goto("/search/?q=duration");
  const hit = page.locator('[data-search-hit="/models/fixed-income/duration/"]');
  await expect(hit).toBeVisible();
  await expect(hit).toContainText("Model · Fixed income");
  await expect(hit).toContainText("Macaulay");
  await expect(page.locator("[data-search-status]")).toContainText("for “duration”");
  for (const colorScheme of ["light", "dark"] as const) {
    await useColorScheme(page, colorScheme);
    const results = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
    expect(results.violations.map((violation) => `${colorScheme} ${violation.id}: ${violation.help}`)).toEqual([]);
  }
  const origin = new URL(page.url()).origin;
  expect(requests.filter((url) => new URL(url).origin !== origin)).toEqual([]);
  expect(requests.some((url) => url.includes("/pagefind/"))).toBe(true);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("/search/ treats the query as text", async ({ page, watch }) => {
  await page.goto(`/search/?q=${encodeURIComponent('<img src=x onerror="document.title=1">')}`);
  await expect(page.locator("[data-search-status]")).toContainText("<img src=x");
  expect(await page.locator("main img").count()).toBe(0);
  expect(await page.title()).not.toBe("1");
  expect(watch.violations).toEqual([]);
});

test("the header box loads search only when used, shows hits, and opens /search/ on Enter", async ({ page, watch }) => {
  const requests: string[] = [];
  page.on("request", (request) => requests.push(new URL(request.url()).pathname));
  await page.goto("/models/fixed-income/");
  await page.waitForLoadState("load");
  expect(requests.filter((path) => path.startsWith("/pagefind/") || path.endsWith(".js"))).toEqual([]);
  const box = page.getByRole("searchbox", { name: "Search models and pages" });
  await box.focus();
  await box.pressSequentially("garch");
  const hit = page.locator('header [data-search-hit="/models/econometrics/garch/"]');
  await expect(hit).toBeVisible();
  await expect(hit).toContainText("Econometrics");
  await page.keyboard.press("Escape");
  await expect(hit).toBeHidden();
  // Escape also clears a search box's text, as browsers do.
  await box.fill("garch");
  await box.press("Enter");
  await expect(page).toHaveURL(/\/search\/\?q=garch$/);
  await expect(page.locator('main [data-search-hit="/models/econometrics/garch/"]')).toBeVisible();
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("the header box works as a plain form before it hydrates", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("/");
  await page.getByRole("searchbox", { name: "Search models and pages" }).fill("bond");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/search\/\?q=bond$/);
  await context.close();
});
