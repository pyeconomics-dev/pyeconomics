// web/tests/e2e/motion.spec.ts
// Reduced motion (Phase 5 Step 17; WCAG 2.2 SC 2.3.3): with the visitor's
// system asking for reduced motion, no element of a sample page declares a
// transition or animation longer than 0.01 s, and none runs longer, before or
// after the pointer and the keyboard have touched the page's controls (hover
// and focus start most transitions) and its islands have loaded. The site's
// motion is CSS classes and keyframes in its stylesheets, all of which the
// reduced-motion rule in global.css turns off.
import type { Page } from "@playwright/test";

import { expect, test } from "./support.ts";

const LIMIT_SECONDS = 0.01;

const SAMPLE = [
  "/",
  "/models/",
  "/models/fixed-income/duration/",
  "/models/econometrics/ols/",
  "/data/us/unemployment/rate/",
  "/search/",
  "/newsletter/",
];

/** Seconds in a CSS time list ("0.15s, 200ms"): the longest. */
function longest(list: string): number {
  return Math.max(
    0,
    ...list.split(",").map((part) => {
      const text = part.trim();
      return text.endsWith("ms") ? Number(text.slice(0, -2)) / 1000 : Number(text.replace(/s$/, ""));
    }),
  );
}

/** Every element's declared motion longer than the limit, and every running animation's. */
async function motion(page: Page): Promise<string[]> {
  const declared = await page.evaluate(() =>
    [...document.querySelectorAll("*")].flatMap((element) => {
      const style = getComputedStyle(element);
      const name = `${element.tagName.toLowerCase()}${element.id ? `#${element.id}` : ""}.${[...element.classList].slice(0, 3).join(".")}`;
      const found: { name: string; kind: string; value: string }[] = [];
      if (style.transitionProperty !== "none") found.push({ name, kind: "transition", value: style.transitionDuration });
      if (style.animationName !== "none") found.push({ name, kind: "animation", value: style.animationDuration });
      return found;
    }),
  );
  const running = await page.evaluate(() =>
    document.getAnimations().map((animation) => ({
      kind: animation.constructor.name,
      duration: Number(animation.effect?.getComputedTiming().duration ?? 0),
    })),
  );
  return [
    ...declared.filter((entry) => longest(entry.value) > LIMIT_SECONDS).map((entry) => `${entry.kind} ${entry.value} on ${entry.name}`),
    ...running.filter((entry) => entry.duration / 1000 > LIMIT_SECONDS).map((entry) => `running ${entry.kind} of ${String(entry.duration)} ms`),
  ];
}

test.use({ reducedMotion: "reduce" });

for (const path of SAMPLE) {
  test(`page ${path} has no motion longer than 0.01 s under reduced motion`, async ({ page, api }) => {
    await page.goto(path);
    await page.waitForLoadState("load");
    expect(await motion(page)).toEqual([]);
    // Hover and focus the controls, and bring the islands into view.
    const controls = (await page.locator("main a, main button, header a").all()).slice(0, 40);
    for (const control of controls) {
      if (!(await control.isVisible())) continue;
      await control.hover({ timeout: 2_000 }).catch(() => undefined);
      await control.focus().catch(() => undefined);
    }
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await page.waitForLoadState("networkidle").catch(() => undefined);
    expect(await motion(page)).toEqual([]);
    // Only a concept's page asks the API anything unasked: its chart's series.
    expect(api.requests.filter((request) => !request.url.startsWith("/v1/series/"))).toEqual([]);
  });
}

// Step 17's trap, made a check in Step 18: a transition on anything a closed
// <details> holds never finishes, because the browser does not render it, so
// whatever waits for transitions (the tests' useColorScheme among them) waits
// forever. global.css turns every such transition off; this holds it, with
// motion allowed, on pages whose islands have loaded their disclosures.
test.describe("with motion allowed", () => {
  test.use({ reducedMotion: "no-preference" });

  for (const path of ["/", "/models/fixed-income/duration/", "/models/fixed-income/bond-pricing/", "/models/equity/cape/"]) {
    test(`nothing a closed disclosure holds on ${path} declares a transition`, async ({ page }) => {
      await page.goto(path);
      const calculator = page.locator("[data-calculator]").first();
      await calculator.scrollIntoViewIfNeeded();
      await expect(page.locator('[data-calculator][data-ready="true"]').first()).toBeVisible();
      const found = await page.evaluate(() =>
        [...document.querySelectorAll("details:not([open])")].flatMap((details) =>
          [...details.querySelectorAll(":scope > :not(summary), :scope > :not(summary) *")]
            .filter((element) => {
              const style = getComputedStyle(element);
              return style.transitionProperty !== "none" && style.transitionDuration.split(",").some((part) => parseFloat(part) > 0);
            })
            .map((element) => `${element.tagName.toLowerCase()}.${[...element.classList].slice(0, 3).join(".")}`),
        ),
      );
      expect(found).toEqual([]);
      expect(await page.locator("details:not([open])").count()).toBeGreaterThan(0);
    });
  }
});
