// web/tests/e2e/pages.spec.ts
// Every page the build wrote, and the 404 page, served as Cloudflare serves
// them: decision 9's headers, the layout's notices and landmarks, and no
// inline style, and no executable inline script but the island runtime the
// policy hashes (every page has the header's search island). A sample (decision 19's pages that exist, a model page per
// cost class, a bound model, models with a chart, and a problem page) is also
// checked for a skip link with a visible focus, no WCAG 2.2 AA violation under
// axe in light and dark, and no Content Security Policy violation or console
// error; the calculator's own states (before and after a run) are axe-checked
// in calculator.spec.ts.
import AxeBuilder from "@axe-core/playwright";

import { hashSource } from "../../scripts/headers.ts";
import { AS_IS_NOTICE, CFA_NOTICE, FOOTER_LINKS } from "../../src/lib/links.ts";
import { expect, headerPolicy, pages, test } from "./support.ts";

const AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const NOT_FOUND = "/no-such-page/";

/** The pages axe and the keyboard checks run on. */
const SAMPLE = [
  "/",
  "/models/",
  "/models/fixed-income/",
  // light, and decision 19's
  "/models/fixed-income/bond-pricing/",
  "/models/foundations/time-value/",
  // instant and bound, decision 19's
  "/models/macro/policy-rule/",
  // heavy, bound and with a chart, decision 19's
  "/models/econometrics/garch/",
  // instant, reads no data
  "/models/derivatives/black-scholes-merton/",
  // a planned section's empty state
  "/models/micro/",
  "/search/",
  "/data/",
  "/data/us/unemployment/rate/",
  "/coverage/",
  // light, with a chart
  "/models/econometrics/ols/",
  "/problems/",
  "/problems/invalid-input/",
  // Step 15's sign-up forms and the Pro preview
  "/newsletter/",
  "/pro/",
  // Step 16's legal and trust pages: decision 19's two, and the terms
  "/legal/privacy/",
  "/sources/",
  "/legal/terms/",
  NOT_FOUND,
];

test("the sample pages all exist in the build", () => {
  const built = pages();
  for (const path of SAMPLE.filter((p) => p !== NOT_FOUND)) expect(built, path).toContain(path);
});

for (const path of [...pages(), NOT_FOUND]) {
  test(`page ${path} sends decision 9's headers and carries the layout`, async ({ page }) => {
    const response = await page.goto(path);
    expect(response?.status()).toBe(path === NOT_FOUND ? 404 : 200);
    const headers = response?.headers() ?? {};
    const policy = headers["content-security-policy"] ?? "";
    expect(policy).toBe(headerPolicy());
    expect(policy).toContain("frame-ancestors 'none'");
    expect(policy).not.toMatch(/'unsafe-inline'|'unsafe-eval'/);
    expect(headers["strict-transport-security"]).toBe("max-age=63072000; includeSubDomains; preload");
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
    expect(headers["cross-origin-opener-policy"]).toBe("same-origin");
    expect(headers["permissions-policy"]).toContain("camera=()");

    await expect(page.getByRole("banner")).toBeVisible();
    await expect(page.getByRole("main")).toBeVisible();
    const footer = page.getByRole("contentinfo");
    await expect(footer.getByText(CFA_NOTICE, { exact: true })).toBeVisible();
    await expect(footer.getByText(AS_IS_NOTICE, { exact: true })).toBeVisible();
    for (const link of FOOTER_LINKS) {
      await expect(footer.getByRole("link", { name: link.label, exact: true })).toHaveAttribute("href", link.href);
    }
    expect(await page.locator("[style]").count()).toBe(0);
    // Inline scripts: the JSON-LD, which no browser executes, and the islands'
    // runtime (the header's search box on every page), whose every script the
    // policy hashes.
    const inline = await page.locator('script:not([src]):not([type="application/ld+json"])').allTextContents();
    expect(inline.length).toBeGreaterThan(0);
    for (const text of inline) expect(policy).toContain(hashSource(text));
  });
}

for (const path of SAMPLE) {
  test.describe(`sample page ${path}`, () => {
    test("has a skip link to the main content and a visible focus", async ({ page }) => {
      await page.goto(path);
      await page.keyboard.press("Tab");
      const skip = page.getByRole("link", { name: "Skip to content" });
      await expect(skip).toBeFocused();
      await expect(skip).toBeVisible();
      const outline = await skip.evaluate((element) => getComputedStyle(element).outlineStyle);
      expect(outline).not.toBe("none");
      await page.keyboard.press("Enter");
      await expect(page.locator("main#main")).toBeFocused();
    });

    // An island may ask the server's mode (GET /version), which only `api` answers here.
    test("passes axe at WCAG 2.2 AA with no policy violation or console error", async ({ page, api, watch }) => {
      // The site follows the system's colour scheme, so both are checked.
      for (const colorScheme of ["light", "dark"] as const) {
        await page.emulateMedia({ colorScheme });
        await page.goto(path);
        await page.waitForLoadState("load");
        const results = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
        expect(results.violations.map((violation) => `${colorScheme} ${violation.id}: ${violation.help}`)).toEqual(
          [],
        );
      }
      expect(watch.violations).toEqual([]);
      // Chromium logs the 404 page's own status as a resource error.
      const errors = watch.errors.filter((text) => !(path === NOT_FOUND && /404/.test(text)));
      expect(errors).toEqual([]);
      expect(api.requests).toEqual([]);
    });

    // Issue #319's class: a box scrolls vertically only when it is given a
    // maximum height (a code panel). Any other box that overflows by a few
    // pixels shows a stray scrollbar where scrollbars are always drawn
    // (Windows), which headless Chromium hides, so the boxes are measured.
    test("no box scrolls vertically unless it has a maximum height", async ({ page }) => {
      await page.goto(path);
      await page.waitForLoadState("load");
      const stray = await page.evaluate(() =>
        [...document.querySelectorAll("body *")]
          .filter((element) => {
            const style = getComputedStyle(element);
            return (
              ["auto", "scroll"].includes(style.overflowY) &&
              style.maxHeight === "none" &&
              element.scrollHeight > element.clientHeight + 1
            );
          })
          .map((element) => `${element.tagName.toLowerCase()}.${[...element.classList].join(".")}`),
      );
      expect(stray).toEqual([]);
    });
  });
}

test("formulas render as MathML with no inline style", async ({ page }) => {
  for (const path of ["/", "/models/fixed-income/duration/"]) {
    await page.goto(path);
    const math = page.locator(".katex math");
    await expect(math.first()).toBeAttached();
    expect(await page.locator(".katex [style], .katex-html").count()).toBe(0);
  }
});

// Issue #319: a display formula scrolls sideways only. Headless Chromium hides
// scrollbars, so the check reads the boxes, not the bars: no vertical
// scrolling, and nothing clipped by the rule that prevents it.
test("display formulas never scroll vertically and are not clipped", async ({ page }) => {
  for (const path of ["/models/equity/cape/", "/models/fixed-income/duration/"]) {
    await page.goto(path);
    const boxes = await page.locator(".katex:has(> math[display='block'])").evaluateAll((elements) =>
      elements.map((element) => ({
        overflowY: getComputedStyle(element).overflowY,
        spare: element.clientHeight - element.scrollHeight,
      })),
    );
    expect(boxes.length, path).toBeGreaterThan(0);
    for (const box of boxes) {
      expect(box.overflowY, path).toBe("hidden");
      expect(box.spare, path).toBeGreaterThanOrEqual(0);
    }
  }
});

test("a model page loads no script file until its calculator is in view, and its JSON-LD is not executed", async ({
  page,
  watch,
}) => {
  const loaded: string[] = [];
  page.on("request", (request) => {
    if (request.resourceType() === "script") loaded.push(new URL(request.url()).pathname);
  });
  await page.goto("/models/macro/policy-rule/");
  await page.waitForLoadState("load");
  expect(await page.locator("script[src]").count()).toBe(0);
  expect(loaded).toEqual([]);
  const block = await page.locator('script[type="application/ld+json"]').textContent();
  expect((JSON.parse(block ?? "{}") as { "@type"?: string })["@type"]).toBe("WebPage");
  expect(watch.violations).toEqual([]);
});

test("the policy blocks an inline script, and the listener sees it", async ({ page, watch }) => {
  await page.goto("/");
  await page.evaluate(() => {
    const script = document.createElement("script");
    script.textContent = "document.body.dataset.injected = 'yes';";
    document.body.append(script);
  });
  await expect.poll(() => watch.violations.length).toBeGreaterThan(0);
  expect(watch.violations[0]?.directive).toMatch(/^script-src/);
  expect(await page.locator("body").getAttribute("data-injected")).toBeNull();
});

test("hashed build assets are immutable", async ({ page, request }) => {
  await page.goto("/");
  const stylesheet = await page.locator('link[rel="stylesheet"]').first().getAttribute("href");
  expect(stylesheet).toMatch(/^\/_astro\//);
  const response = await request.get(stylesheet ?? "");
  expect(response.headers()["cache-control"]).toBe("public, max-age=31536000, immutable");
});
