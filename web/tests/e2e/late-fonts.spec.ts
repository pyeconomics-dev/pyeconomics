// web/tests/e2e/late-fonts.spec.ts
// A page does not move when its fonts arrive late (issue #354, from the
// confirmation round on staging). The text font is declared `font-display:
// swap`, so where it arrives after the first paint the page is drawn in a
// system serif and then again in Literata. With fallback faces that carry
// Literata's metrics (src/styles/global.css; the numbers are
// scripts/fallback-metrics.ts's), the second drawing changes the letters and
// not where anything is. Here every font file is held back for a second and a
// half, on pages whose first screen is text, formulas, a form and a list.
//
// One scale fits a fallback face only where a letter's width grows with its
// size. Chromium on Linux at ordinary density, which is what CI's runner is,
// rounds each letter to whole pixels instead, and there the same faces are 7%
// narrower than Literata at 14 pixels and 2% wider at 17: the privacy policy
// moved by 0.228 on the runner and by 0.004 at most on Windows. So this file's
// browser is started without that rounding (LINEAR, a switch only Linux
// reads): text is then measured as Windows measures it, where the faces were
// fitted, and as any system does that keeps a letter's width in proportion to
// its size. What a Linux desktop still shows is written down in
// src/styles/global.css and docs/design/direction.md ("Late fonts").
import { SHIFT_LIMIT, expect, layoutShift, test } from "./support.ts";

/** Letter widths in proportion to their size. A browser's switches are set for a whole file, so this suite has its own. */
const LINEAR = { args: ["--font-render-hinting=none"] };
test.use({ launchOptions: LINEAR });

const VIEWPORTS = [
  { name: "phone", width: 390, height: 844 },
  { name: "desktop", width: 1440, height: 900 },
] as const;

const LATE_FONT = ["/", "/models/", "/models/fixed-income/duration/", "/search/?q=sharpe", "/sources/", "/legal/privacy/"];

for (const viewport of VIEWPORTS) {
  test.describe(`late fonts at a ${viewport.name}'s size`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });
    for (const path of LATE_FONT) {
      test(`page ${path} does not move when its fonts arrive after its first paint`, async ({ page, api }) => {
        let held = 0;
        await page.route("**/*.woff2", async (route) => {
          held += 1;
          await new Promise((resolve) => setTimeout(resolve, 1500));
          await route.continue();
        });
        await page.goto(path, { waitUntil: "domcontentloaded" });
        // The page is painted in the fallback face first, which is what this check is about.
        const painted = await page.evaluate(
          () => new Promise<boolean>((resolve) => requestAnimationFrame(() => resolve(!document.fonts.check('1rem "Literata Variable"')))),
        );
        expect(painted, "the page painted before its font arrived").toBe(true);
        await page.evaluate(() => document.fonts.ready.then(() => undefined));
        await expect.poll(() => page.evaluate(() => document.fonts.check('1rem "Literata Variable"')), { timeout: 10_000 }).toBe(true);
        await page.waitForLoadState("networkidle", { timeout: 5_000 }).catch(() => undefined);
        await page.waitForTimeout(400);
        expect(held).toBeGreaterThan(0);
        const shift = await layoutShift(page);
        expect(shift.total, shift.worst.join(" | ")).toBeLessThan(SHIFT_LIMIT);
        expect(api.requests.every((request) => request.method === "GET")).toBe(true);
      });
    }
  });
}
