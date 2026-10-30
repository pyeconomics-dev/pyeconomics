// web/tests/e2e/pages.spec.ts
// Every page the build wrote, and the 404 page, served as Cloudflare serves
// them: decision 9's headers, the layout's notices and landmarks, MathML with
// no inline style, no WCAG 2.2 AA violation under axe, and no Content Security
// Policy violation or console error.
import AxeBuilder from "@axe-core/playwright";

import { AS_IS_NOTICE, CFA_NOTICE, FOOTER_LINKS } from "../../src/lib/links.ts";
import { expect, headerPolicy, pages, test } from "./support.ts";

const AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const NOT_FOUND = "/no-such-page/";

for (const path of [...pages(), NOT_FOUND]) {
  test.describe(`page ${path}`, () => {
    test("sends decision 9's headers", async ({ page }) => {
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
    });

    test("carries the layout, the notices and the links", async ({ page }) => {
      await page.goto(path);
      await expect(page.getByRole("banner")).toBeVisible();
      await expect(page.getByRole("main")).toBeVisible();
      const footer = page.getByRole("contentinfo");
      await expect(footer.getByText(CFA_NOTICE, { exact: true })).toBeVisible();
      await expect(footer.getByText(AS_IS_NOTICE, { exact: true })).toBeVisible();
      for (const link of FOOTER_LINKS) {
        await expect(footer.getByRole("link", { name: link.label, exact: true })).toHaveAttribute(
          "href",
          link.href,
        );
      }
      expect(await page.locator("[style]").count()).toBe(0);
      expect(await page.locator("script:not([src])").count()).toBe(0);
    });

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

    test("passes axe at WCAG 2.2 AA with no policy violation or console error", async ({
      page,
      watch,
    }) => {
      // The site follows the system's colour scheme, so both are checked.
      for (const colorScheme of ["light", "dark"] as const) {
        await page.emulateMedia({ colorScheme });
        await page.goto(path);
        await page.waitForLoadState("load");
        const results = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
        expect(
          results.violations.map((violation) => `${colorScheme} ${violation.id}: ${violation.help}`),
        ).toEqual([]);
      }
      expect(watch.violations).toEqual([]);
      // Chromium logs the 404 page's own status as a resource error.
      const errors = watch.errors.filter((text) => !(path === NOT_FOUND && /404/.test(text)));
      expect(errors).toEqual([]);
    });
  });
}

test("formulas render as MathML with no inline style", async ({ page }) => {
  await page.goto("/");
  const math = page.locator(".katex math");
  await expect(math.first()).toBeAttached();
  expect(await page.locator(".katex [style], .katex-html").count()).toBe(0);
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
