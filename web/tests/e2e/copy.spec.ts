// web/tests/e2e/copy.spec.ts
// A copy that fails says so (Phase 5 Step 18; round 0 of the dogfooding
// protocol found a copy button that failed without a word). The class, not the
// instance: with the browser refusing the clipboard, every copy control a
// calculator, its result, a command and the data explorer show is pressed, and
// each must say that the text can be selected instead. tests/unit/
// build-tools.test.ts holds that only the one copy control touches the
// clipboard, so a new one cannot skip this.
import type { Page } from "@playwright/test";

import { expect, test } from "./support.ts";

const REFUSED = "The browser would not copy it";

/** Make the page's clipboard refuse every write, before any script runs. */
async function refuseClipboard(page: Page): Promise<void> {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: () => Promise.reject(new Error("refused")) },
    });
  });
}

/** Press every copy control in view of the page, one at a time, and require its message. */
async function pressEach(page: Page, least: number): Promise<void> {
  const controls = page.locator("[data-copy]");
  const count = await controls.count();
  expect(count).toBeGreaterThanOrEqual(least);
  for (let index = 0; index < count; index += 1) {
    const control = controls.nth(index);
    if (!(await control.isVisible())) continue;
    await control.getByRole("button").click();
    await expect(control).toHaveAttribute("data-copy", "failed");
    await expect(control.locator("[data-copy-message]")).toContainText(REFUSED);
  }
}

test("a calculator's copy controls say when the clipboard refuses", async ({ page, api }) => {
  await refuseClipboard(page);
  await page.goto("/models/performance/risk-adjusted/");
  const section = page.locator("#calculator");
  await section.scrollIntoViewIfNeeded();
  await expect(section.locator("[data-calculator][data-ready=true]")).toBeVisible();
  await section.getByRole("button", { name: "Run", exact: true }).click();
  await expect(section.getByRole("heading", { name: "Result", exact: true })).toBeVisible();
  // Copy JSON, the manifest's facts and the snippet.
  await pressEach(page, 3);
  expect(api.requests).toHaveLength(1);
});

test("a command's copy control says when the clipboard refuses", async ({ page, api }) => {
  await refuseClipboard(page);
  await page.goto("/models/equity/cape/");
  const section = page.locator("#calculator");
  await section.scrollIntoViewIfNeeded();
  await expect(section.locator("[data-calculator][data-ready=true]")).toBeVisible();
  await section.getByLabel(/^Live data/).check();
  await expect(section.locator("[data-live=unserved] [data-command]").first()).toBeVisible();
  await pressEach(page, 3);
  expect(api.requests).toEqual([]);
});

test("the explorer's citation copy says when the clipboard refuses", async ({ page, api }) => {
  await refuseClipboard(page);
  await page.goto("/data/us/unemployment/rate/");
  const section = page.locator("#chart");
  await section.scrollIntoViewIfNeeded();
  await expect(section.locator("[data-cite]")).toBeVisible();
  await pressEach(page, 1);
  expect(api.requests.length).toBeGreaterThan(0);
});

test("a copy that works says so", async ({ page, api }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: (text: string) => {
          (window as unknown as { copied: string }).copied = text;
          return Promise.resolve();
        },
      },
    });
  });
  await page.goto("/data/us/unemployment/rate/");
  const cite = page.locator("#chart [data-cite]");
  await page.locator("#chart").scrollIntoViewIfNeeded();
  await expect(cite).toBeVisible();
  const citation = (await cite.locator("[data-citation]").textContent()) ?? "";
  await cite.getByRole("button", { name: "Copy the citation" }).click();
  await expect(cite.locator("[data-copy]")).toHaveAttribute("data-copy", "copied");
  await expect(cite.getByRole("button", { name: "Copied" })).toBeVisible();
  expect(await page.evaluate(() => (window as unknown as { copied: string }).copied)).toBe(citation);
  expect(api.requests.length).toBeGreaterThan(0);
});
