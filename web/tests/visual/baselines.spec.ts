// web/tests/visual/baselines.spec.ts
// The first screen of each of decision 19's thirteen sample pages (ADR-0013),
// at 390 and 1440 wide, in light and in dark: fifty-two pictures, each held to
// its baseline in tests/visual/baselines/ (Phase 5 Step 18). A page is
// photographed once it has stopped changing: its fonts loaded, every island in
// view ready, no request in flight, no animation running. The first screen,
// not the whole page: it holds the header, the page's title and its first
// content, where a change of token, font or layout shows, and it keeps the
// baselines small enough to review in a pull request.
//
// The pictures are the Linux runner's (playwright.visual.config.ts). To change
// one on purpose, take it from the web job's `visual-baselines` artifact, as
// AGENTS.md "Design rules" says.
import { existsSync, readdirSync } from "node:fs";

import type { Page } from "@playwright/test";

import { expect, test } from "../e2e/support.ts";
import { SAMPLE, THEMES, WIDTHS, baselineName, baselineNames } from "./sample.ts";

/** Wait until the first screen has stopped changing. */
async function settle(page: Page): Promise<void> {
  await page.waitForLoadState("networkidle");
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
  // Every island in view has loaded: one below the fold has not started, and stays out of the picture.
  await expect
    .poll(
      () =>
        page.evaluate(
          () =>
            [...document.querySelectorAll('[data-ready="false"], [data-hydrated="false"]')].filter((element) => {
              const box = element.getBoundingClientRect();
              return box.bottom > 0 && box.top < window.innerHeight && box.height > 0;
            }).length,
        ),
      { timeout: 20_000 },
    )
    .toBe(0);
  await page.waitForLoadState("networkidle");
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
}

// The baselines are one platform's pictures: another's fonts and rasterizer would fail every one.
test.skip(
  () => process.platform !== "linux" && !process.env.VISUAL_ANY_PLATFORM,
  "the visual baselines are drawn on Linux, in the web job",
);

// This file's tests run in order, so this one, the last, sees every picture a
// run that draws baselines has written.
test.describe.configure({ mode: "default" });

for (const { width, height } of WIDTHS) {
  for (const theme of THEMES) {
    test.describe(`${String(width)} wide, ${theme}`, () => {
      test.use({ viewport: { width, height }, colorScheme: theme });
      for (const sample of SAMPLE) {
        // An island may ask the server's mode (GET /version), which only `api` answers here.
        test(`${sample.name} looks as its baseline`, async ({ page, api, watch }) => {
          await page.goto(sample.path, { waitUntil: "load" });
          await settle(page);
          await expect(page).toHaveScreenshot(baselineName(sample, width, theme));
          expect(watch.violations).toEqual([]);
          expect(watch.errors).toEqual([]);
          expect(api.requests).toEqual([]);
        });
      }
    });
  }
}

// Playwright reads the fixtures a test asks for from its first parameter's pattern, which must be there.
// eslint-disable-next-line no-empty-pattern -- see the line above
test("the baselines are exactly the sample's pictures: none missing, none left over", ({}, testInfo) => {
  const directory = testInfo.snapshotPath("x.png").slice(0, -"x.png".length);
  // The baseline directory the configuration names.
  const found = existsSync(directory) ? readdirSync(directory).sort() : [];
  expect(found).toEqual(baselineNames());
});
