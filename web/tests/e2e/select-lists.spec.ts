// web/tests/e2e/select-lists.spec.ts
// A select's open list is drawn by the browser, outside the page, so no
// screenshot and no axe pass sees it, and the harness chooses options by key.
// On 2026-11-23 the dark theme's lists were near-white on white in Chrome on
// Windows: the options were transparent, with the page's text colour. The
// browser draws the list from the options' own colours, so each kind of select
// the site has is held here, in both themes, to options with an opaque
// background and text at 4.5:1 or more (global.css's `option` rule).
import type { Page } from "@playwright/test";

import { contrastRatio, parseColour } from "@/lib/contrast";

import { expect, test } from "./support.ts";

const NO_TOKENS = new Map<string, string>();

/** Open a model page's calculator and choose live data, which shows the profile select. */
async function liveData(page: Page): Promise<void> {
  const section = page.locator("#calculator");
  await section.scrollIntoViewIfNeeded();
  await expect(section.locator("[data-calculator][data-ready=true]")).toBeVisible();
  await page.getByLabel(/^Live data/).check();
}

/** Each page with selects, and how to bring every one of them onto it. */
const PAGES: { path: string; open: (page: Page) => Promise<void> }[] = [
  {
    // The calculator's own selects (the example, and with live data the
    // profile) and a schema's select (the calculation).
    path: "/models/macro/solow-growth/",
    open: async (page) => {
      await liveData(page);
      await expect(page.locator("#calculator").getByLabel("Profile")).toBeVisible();
    },
  },
  {
    // A profile select whose profiles run in different places, in groups.
    path: "/models/macro/policy-rule/",
    open: async (page) => {
      await liveData(page);
      await expect(page.locator("#calculator optgroup").first()).toBeAttached();
    },
  },
  {
    path: "/data/us/unemployment/rate/",
    open: async (page) => {
      const section = page.locator("#chart");
      await section.scrollIntoViewIfNeeded();
      await expect(section.locator("[data-series-explorer][data-hydrated=true]")).toBeVisible();
    },
  },
  {
    path: "/models/",
    open: async (page) => {
      await expect(page.locator("select").first()).toBeAttached();
    },
  },
];

for (const scheme of ["light", "dark"] as const) {
  for (const { path, open } of PAGES) {
    test(`every select's list on ${path} is readable in the ${scheme} theme`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: scheme });
      await page.goto(path);
      await open(page);
      const lists = await page.evaluate(() =>
        [...document.querySelectorAll("select")].flatMap((select, at) =>
          [...select.querySelectorAll("option, optgroup")].map((item) => {
            const style = getComputedStyle(item);
            return {
              where: `select ${String(at)} ${item.tagName.toLowerCase()} "${(item.getAttribute("label") ?? item.textContent ?? "").trim().slice(0, 30)}"`,
              background: style.backgroundColor,
              text: style.color,
            };
          }),
        ),
      );
      expect(lists.length).toBeGreaterThan(0);
      const unreadable = lists.flatMap(({ where, background, text }) => {
        if (/^(transparent|rgba\(0, 0, 0, 0\))$/.test(background)) return [`${where}: a transparent background`];
        const back = parseColour(background, NO_TOKENS);
        if (back.a < 1) return [`${where}: a translucent background (${background})`];
        const ratio = contrastRatio(parseColour(text, NO_TOKENS), back);
        return ratio < 4.5 ? [`${where}: ${ratio.toFixed(2)}:1 (${text} on ${background})`] : [];
      });
      expect(unreadable).toEqual([]);
    });
  }
}
