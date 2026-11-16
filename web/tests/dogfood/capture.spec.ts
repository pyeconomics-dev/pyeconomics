// web/tests/dogfood/capture.spec.ts
// Every page type at every width in both themes (docs/design/dogfooding.md
// section 5): the first screen, the whole page, viewport-high tiles, the
// accessibility tree, and a record of load timings, fonts, horizontal
// overflow, boxes that scroll without a maximum height (#319's class),
// console errors and policy violations. A phone's width is emulated as a
// phone. The harness records what it sees; it fails only when a page does not
// answer with its status, so a round always gets every capture it can.
import { expect, test } from "@playwright/test";

import { PAGE_TYPES, THEMES, VIEWPORTS } from "./pages.ts";
import { measure, prepare, screenshots, scrollThrough, write, writeRecord } from "./support.ts";

for (const type of PAGE_TYPES) {
  for (const viewport of VIEWPORTS) {
    for (const theme of THEMES) {
      test(`capture ${type.id} ${viewport.name} ${theme}`, async ({ browser }) => {
        const context = await browser.newContext({
          viewport: { width: viewport.width, height: viewport.height },
          isMobile: viewport.phone,
          hasTouch: viewport.phone,
          deviceScaleFactor: 1,
          colorScheme: theme,
          reducedMotion: "no-preference",
        });
        const page = await context.newPage();
        const watch = await prepare(page);
        const response = await page.goto(type.path, { waitUntil: "load" });
        await scrollThrough(page);
        const measures = await measure(page);
        const stem = `pages/${type.id}/${viewport.name}-${theme}`;
        const shots = await screenshots(page, stem);
        const aria = write(`${stem}.aria.yml`, await page.locator("body").ariaSnapshot());
        writeRecord({
          kind: "page",
          id: type.id,
          path: type.path,
          label: type.label,
          viewport: viewport.name,
          theme,
          status: response?.status() ?? null,
          files: [shots.first, shots.full, ...shots.tiles, aria],
          measures,
          violations: watch.violations,
          // Chromium logs the 404 page's own status as a resource error.
          errors: watch.errors.filter((text) => !(type.status === 404 && /status of 404/.test(text))),
        });
        await context.close();
        expect(response?.status(), type.path).toBe(type.status);
      });
    }
  }
}
