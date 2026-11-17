// web/tests/e2e/layout-shift.spec.ts
// A page does not move under a visitor as it loads (Phase 5 Step 18; round 0's
// M12 and round 1 of the dogfooding protocol: pages shifted as a calculator,
// the search results or a chart arrived, with a cumulative layout shift up to
// 0.31). The class, not the instance: each sample page is opened at a phone's,
// a tablet's and a desktop's size and scrolled through a screen at a time, as
// the dogfooding harness does, so every island that loads when it comes into
// view loads; the shifts the browser reports, none of them after an input,
// must total less than 0.1, the limit Core Web Vitals call good. A calculator
// holds its form's estimated room before the form loads (src/lib/
// calculator.ts formRoom), so a form that outgrows the estimate fails here.
import type { Page } from "@playwright/test";

import { expect, test } from "./support.ts";

/** Core Web Vitals' "good" limit for cumulative layout shift. */
const LIMIT = 0.1;

const VIEWPORTS = [
  { name: "phone", width: 390, height: 844 },
  { name: "tablet", width: 820, height: 1180 },
  { name: "desktop", width: 1440, height: 900 },
] as const;

/** Pages with an island that loads in view: calculators of each kind, the explorer, the lists and the search. */
const SAMPLE = [
  "/",
  "/models/",
  "/models/fixed-income/bond-pricing/",
  "/models/fixed-income/duration/",
  "/models/foundations/time-value/",
  "/models/macro/policy-rule/",
  "/models/econometrics/garch/",
  "/models/econometrics/ols/",
  "/models/equity/cape/",
  "/models/performance/risk-adjusted/",
  "/models/portfolio/black-litterman/",
  "/data/",
  "/data/us/unemployment/rate/",
  "/search/?q=sharpe",
];

/** Scroll through the page a screen at a time, then wait for what that loaded. */
async function scrollThrough(page: Page, step: number): Promise<void> {
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y < height; y += step) {
    await page.evaluate((top) => window.scrollTo(0, top), y);
    await page.waitForTimeout(150);
  }
  await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => undefined);
  await page.waitForTimeout(300);
}

/** The page's cumulative layout shift so far, leaving out shifts just after an input. */
async function layoutShift(page: Page): Promise<{ total: number; worst: string[] }> {
  return page.evaluate(
    () =>
      new Promise<{ total: number; worst: string[] }>((resolve) => {
        const entries: PerformanceEntry[] = [];
        const observer = new PerformanceObserver((list) => entries.push(...list.getEntries()));
        observer.observe({ type: "layout-shift", buffered: true });
        setTimeout(() => {
          observer.disconnect();
          const shifts = entries
            .map(
              (entry) =>
                entry as PerformanceEntry & {
                  value: number;
                  hadRecentInput: boolean;
                  sources?: { node?: Node | null }[];
                },
            )
            .filter((entry) => !entry.hadRecentInput);
          const name = (node: Node | null | undefined): string => {
            if (!(node instanceof Element)) return "(text)";
            return `${node.tagName.toLowerCase()}${node.id ? `#${node.id}` : ""}.${[...node.classList].slice(0, 2).join(".")}`;
          };
          resolve({
            total: Math.round(shifts.reduce((sum, entry) => sum + entry.value, 0) * 1000) / 1000,
            worst: shifts
              .filter((entry) => entry.value > 0.02)
              .map((entry) => `${entry.value.toFixed(3)} at ${String(Math.round(entry.startTime))} ms: ${(entry.sources ?? []).map((source) => name(source.node)).join(", ")}`),
          });
        }, 100);
      }),
  );
}

for (const viewport of VIEWPORTS) {
  test.describe(`at a ${viewport.name}'s size`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });
    for (const path of SAMPLE) {
      // The islands ask the API (a chart's series, the server's mode), which only `api` answers here.
      test(`page ${path} shifts less than ${String(LIMIT)} as it loads`, async ({ page, api }) => {
        await page.goto(path, { waitUntil: "load" });
        // A visitor reads the first screen before scrolling: what the address
        // itself asks for (a search's results) arrives while they do. Round 2:
        // scrolled to the foot of the page at once, the search page's footer
        // was in view when the results came and moved it.
        await page.waitForLoadState("networkidle", { timeout: 5_000 }).catch(() => undefined);
        await scrollThrough(page, viewport.height);
        const shift = await layoutShift(page);
        expect(shift.total, shift.worst.join(" | ")).toBeLessThan(LIMIT);
        expect(api.requests.every((request) => request.method === "GET")).toBe(true);
      });
    }
  });
}

// The confirmation round on staging (Phase 5 Step 18): a run that takes more
// than half a second put its result into the page after the browser had
// stopped counting the press of Run as the cause, and everything under the
// form moved at once (0.5 to 0.7, where the checks above saw nothing: the
// local API answers in a few milliseconds). The result's place and skeleton
// now arrive with the press, so the answer changes values, not positions.
// A long result, a result of one output and a result with a chart.
const SLOW_RUNS = ["/models/performance/risk-adjusted/", "/models/foundations/time-value/", "/models/econometrics/ols/"];

for (const viewport of VIEWPORTS.filter((entry) => entry.name !== "tablet")) {
  test.describe(`a slow run at a ${viewport.name}'s size`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });
    for (const path of SLOW_RUNS) {
      test(`page ${path} moves nothing when its result arrives a second after the press`, async ({ page, api }) => {
        await page.goto(path, { waitUntil: "load" });
        // Registered after the api fixture's route, so it runs first: hold the run back, then let it through.
        await page.route("**/v1/models/**", async (route) => {
          await new Promise((resolve) => setTimeout(resolve, 900));
          await route.fallback();
        });
        const section = page.locator("#calculator");
        await section.scrollIntoViewIfNeeded();
        await expect(section.locator("[data-calculator][data-ready=true]")).toBeVisible();
        await page.waitForLoadState("networkidle", { timeout: 5_000 }).catch(() => undefined);
        const before = await layoutShift(page);
        await section.getByRole("button", { name: "Run", exact: true }).click();
        // With the press: the result's place, its heading focused and the run's skeleton under it.
        await expect(section.getByRole("heading", { name: "Running the model…" })).toBeFocused();
        await expect(section.locator("[data-pending] [data-outputs] tbody tr").first()).toBeVisible();
        await expect(section.getByRole("heading", { name: "Result", exact: true })).toBeFocused({ timeout: 15_000 });
        await expect(section.locator("[data-pending]")).toHaveCount(0);
        expect(api.requests).toHaveLength(1);
        await page.waitForTimeout(700);
        const after = await layoutShift(page);
        expect(Math.round((after.total - before.total) * 1000) / 1000, after.worst.join(" | ")).toBeLessThan(LIMIT);
      });
    }
  });
}
