// web/tests/e2e/calculator.spec.ts
// The calculators (Phase 5 Step 6; ADR-0013 decisions 8, 9 and 11), served as
// Cloudflare serves them, with the page's /v1/ requests forwarded to the local
// hosted-mode API over stand-in providers (support.ts `api`). Each test also
// fails on any Content Security Policy violation or console error the page
// raises: no validator is compiled in the browser, and Plotly injects no style.
import { readFileSync } from "node:fs";

import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { expect, test } from "./support.ts";

const AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const DURATION = "/models/fixed-income/duration/";

/** Open a model page and wait for its calculator to hydrate and load its model. */
async function openCalculator(page: Page, path: string): Promise<void> {
  await page.goto(path);
  const section = page.locator("#calculator");
  await section.scrollIntoViewIfNeeded();
  await expect(section.locator("[data-calculator][data-ready=true]")).toBeVisible();
}

async function run(page: Page): Promise<void> {
  await page.locator("#calculator").getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Result", exact: true })).toBeFocused();
}

test("a calculator posts its first example's JSON to its run route and shows the result", async ({ page, api, watch }) => {
  await openCalculator(page, DURATION);
  await run(page);
  const [request] = api.requests;
  expect(request?.method).toBe("POST");
  expect(request?.url).toBe("/v1/models/fixed_income.duration/run");
  expect(request?.contentType).toBe("application/json");
  expect(JSON.parse(request?.body ?? "{}")).toMatchObject({ calculation: "macaulay_modified" });
  const outputs = page.getByRole("table", { name: "Outputs of this run" });
  await expect(outputs.getByRole("rowheader", { name: /^macaulay_duration/ })).toBeVisible();
  await expect(outputs.getByRole("cell", { name: "years" }).first()).toBeVisible();
  await expect(page.locator("#calculator").getByRole("status")).toContainText("Done.");
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("every control works from the keyboard, and the run moves focus to the result", async ({ page, api, watch }) => {
  await openCalculator(page, DURATION);
  await page.locator("#calculator select, #calculator input:not([type=hidden]), #calculator textarea").first().focus();
  const runButton = page.locator("#calculator").getByRole("button", { name: "Run", exact: true });
  for (let presses = 0; presses < 80 && !(await runButton.evaluate((button) => button === document.activeElement)); presses += 1) {
    await page.keyboard.press("Tab");
  }
  await expect(runButton).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Result", exact: true })).toBeFocused();
  expect(api.requests).toHaveLength(1);
  expect(watch.violations).toEqual([]);
});

test("axe finds no WCAG 2.2 AA violation on a calculator before and after a run", async ({ page, api, watch }) => {
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await openCalculator(page, DURATION);
    for (const state of ["before", "after"] as const) {
      if (state === "after") await run(page);
      const results = await new AxeBuilder({ page }).include("#calculator").withTags(AXE_TAGS).analyze();
      expect(results.violations.map((v) => `${colorScheme} ${state} ${v.id}: ${v.help}`)).toEqual([]);
    }
  }
  expect(api.requests.length).toBeGreaterThan(0);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("a field the model refuses is announced, and the server is not asked", async ({ page, api, watch }) => {
  await openCalculator(page, DURATION);
  const coupon = page.locator("#calculator").getByLabel("Coupon Rate", { exact: false }).first();
  await coupon.fill("7");
  await page.locator("#calculator").getByRole("button", { name: "Run", exact: true }).click();
  const status = page.locator("#calculator").getByRole("status");
  await expect(status).toContainText("1 input needs fixing before the run: 'Coupon Rate' must be <= 1");
  // Only the chosen calculation's requirements, not every member's of the oneOf.
  await expect(status).not.toContainText("Curve Tenors");
  expect(api.requests).toEqual([]);
  expect(watch.violations).toEqual([]);
});

test("live data binds a profile, shows its sources, and the CSV carries the attribution block", async ({ page, api, watch }) => {
  await openCalculator(page, "/models/macro/policy-rule/");
  await page.getByLabel(/^Live data/).check();
  await expect(page.locator("[data-live=hosted]")).toBeVisible();
  await run(page);
  expect(api.requests[0]?.url).toBe("/v1/models/macro.policy_rule/run?profile=default");
  const sent = JSON.parse(api.requests[0]?.body ?? "{}") as Record<string, unknown>;
  expect(sent.calculation).toBe("taylor_1993");
  expect(sent).not.toHaveProperty("inflation");
  await expect(page.getByRole("heading", { name: "Sources" })).toBeVisible();
  await expect(page.getByText("Source: U.S. Bureau of Economic Analysis.").first()).toBeVisible();

  const download = page.waitForEvent("download");
  await page.locator("#calculator").getByRole("button", { name: "CSV", exact: true }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe("macro.policy_rule.csv");
  expect(api.requests.at(-1)?.url).toBe("/v1/models/macro.policy_rule/run?profile=default&format=csv");
  expect(api.requests.at(-1)?.body).toBe(api.requests[0]?.body);
  const csv = readFileSync((await file.path()) ?? "", "utf8");
  expect(csv).toMatch(/^# pyeconomics: /);
  expect(csv).toContain("# attribution: Source: U.S. Bureau of Economic Analysis.");
  expect(csv).toMatch(/^# notice: /m);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("every download format answers a file under the response's name", async ({ page, api, watch }) => {
  await openCalculator(page, DURATION);
  await run(page);
  const names: Record<string, string> = {
    JSON: "fixed_income.duration.json",
    CSV: "fixed_income.duration.csv",
    XLSX: "fixed_income.duration.xlsx",
    Parquet: "fixed_income.duration.parquet",
    Arrow: "fixed_income.duration.arrow",
    "Reproducibility bundle": "fixed_income.duration.zip",
  };
  for (const [label, name] of Object.entries(names)) {
    const download = page.waitForEvent("download");
    await page.locator("#calculator").getByRole("button", { name: label, exact: true }).click();
    const file = await download;
    expect(file.suggestedFilename(), label).toBe(name);
    const bytes = readFileSync((await file.path()) ?? "");
    expect(bytes.length, label).toBeGreaterThan(0);
    if (label === "JSON") {
      // The JSON download is the run's own bytes, as received.
      const first = await page.request.post("http://127.0.0.1:8799/v1/models/fixed_income.duration/run", {
        headers: { "Content-Type": "application/json" },
        data: api.requests[0]?.body ?? "",
      });
      expect(bytes.equals(await first.body())).toBe(true);
    }
  }
  expect(api.requests.map((r) => new URL(r.url, "http://x").searchParams.get("format"))).toEqual([
    null,
    "csv",
    "xlsx",
    "parquet",
    "arrow",
    "bundle",
  ]);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("a chart loads Plotly only when it renders, with its stylesheet and no injected style", async ({ page, api, watch }) => {
  const loaded: string[] = [];
  page.on("request", (request) => loaded.push(new URL(request.url()).pathname));
  await openCalculator(page, "/models/econometrics/ols/");
  expect(loaded.some((path) => path.includes("plotly"))).toBe(false);
  await run(page);
  expect(api.requests).toHaveLength(1);
  await expect(page.locator("#calculator .js-plotly-plot svg.main-svg").first()).toBeVisible();
  expect(loaded.filter((path) => path.includes("plotly")).length).toBe(2);
  expect(await page.locator('link[data-plotly][rel="stylesheet"]').count()).toBe(1);
  expect(await page.locator("style[id^='plotly.js-style']").count()).toBe(0);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("a problem's text is rendered as text, links its page and is announced", async ({ page, watch }) => {
  const markup = '<img src="x" onerror="document.body.dataset.owned=1"><b>bold</b>';
  await openCalculator(page, DURATION);
  await page.route("**/v1/models/fixed_income.duration/run", (route) =>
    route.fulfill({
      status: 422,
      contentType: "application/problem+json",
      body: JSON.stringify({
        type: "https://pyeconomics.dev/problems/invalid-input",
        title: `Invalid input ${markup}`,
        status: 422,
        detail: `The inputs failed ${markup}`,
        errors: [{ loc: ["macaulay_modified", "coupon_rate"], msg: `too high ${markup}`, type: "less_than_equal" }],
      }),
    }),
  );
  await page.locator("#calculator").getByRole("button", { name: "Run", exact: true }).click();
  const panel = page.locator("[data-problem=invalid-input]");
  await expect(panel).toBeVisible();
  await expect(panel.getByText(`The inputs failed ${markup}`)).toBeVisible();
  expect(await panel.locator("img, b").count()).toBe(0);
  expect(await page.locator("body").getAttribute("data-owned")).toBeNull();
  await expect(panel.getByRole("link", { name: /What this problem means/ })).toHaveAttribute("href", "/problems/invalid-input/");
  await expect(page.locator("#calculator").getByRole("status")).toContainText("The run failed");
  await expect(page.locator("#calculator").getByText(`too high ${markup}`).first()).toBeVisible();
  expect(watch.violations).toEqual([]);
});

test("a problem that points to local mode gives the command, and a 429 when to retry", async ({ page }) => {
  await openCalculator(page, DURATION);
  for (const [status, slug, retry] of [
    [413, "input-too-large", null],
    [429, "too-many-requests", "7"],
  ] as const) {
    await page.unroute("**/v1/models/fixed_income.duration/run");
    await page.route("**/v1/models/fixed_income.duration/run", (route) =>
      route.fulfill({
        status,
        contentType: "application/problem+json",
        headers: retry ? { "Retry-After": retry } : {},
        body: JSON.stringify({ type: `https://pyeconomics.dev/problems/${slug}`, title: slug, status, detail: "x" }),
      }),
    );
    await page.locator("#calculator").getByRole("button", { name: "Run", exact: true }).click();
    const panel = page.locator(`[data-problem=${slug}]`);
    await expect(panel).toBeVisible();
    if (slug === "input-too-large") {
      await expect(panel.getByText("pyeconomics models run fixed_income.duration --inputs FILE")).toBeVisible();
    } else {
      await expect(panel.getByText("try again in 7 seconds")).toBeVisible();
    }
  }
});

test("a bound model whose data the hosted site cannot serve says which fields, and offers the alternatives", async ({ page, api }) => {
  await openCalculator(page, "/models/equity/cape/");
  await page.getByLabel(/^Live data/).check();
  const note = page.locator("[data-live=unserved]");
  await expect(note).toBeVisible();
  await expect(note).toContainText("price");
  await expect(note).toContainText("My own values");
  await expect(note).toContainText("pyeconomics models run equity.cape --profile default");
  await run(page);
  // Unservable data is never asked for: the run sends the form's own values.
  expect(api.requests[0]?.url).toBe("/v1/models/equity.cape/run");
});

test("the snippets name the public endpoint and the form's own inputs", async ({ page }) => {
  await openCalculator(page, DURATION);
  await page.getByText("Copy as Python, command line, curl or MCP").click();
  const text = async (kind: string) => (await page.locator(`[data-snippet=${kind}] pre`).textContent()) ?? "";
  expect(await text("python")).toContain('pyeconomics.run("fixed_income.duration", inputs)');
  expect(await text("cli")).toContain("pyeconomics models run fixed_income.duration --inputs - <<'JSON'");
  expect(await text("curl")).toContain("https://pyeconomics.dev/v1/models/fixed_income.duration/run");
  const mcp = JSON.parse(await text("mcp")) as { name: string; arguments: { model_id: string } };
  expect(mcp).toMatchObject({ name: "run_model", arguments: { model_id: "fixed_income.duration" } });
  for (const kind of ["python", "cli", "curl", "mcp"]) {
    expect(await text(kind)).not.toMatch(/cookie|cf-access|authorization|127\.0\.0\.1/i);
  }
});

test("no input reaches storage or the URL", async ({ page, api }) => {
  await openCalculator(page, DURATION);
  await run(page);
  expect(api.requests).toHaveLength(1);
  expect(page.url()).toMatch(/\/models\/fixed-income\/duration\/$/);
  const stored = await page.evaluate(() => ({
    local: Object.keys(localStorage).length,
    session: Object.keys(sessionStorage).length,
    cookies: document.cookie,
  }));
  expect(stored).toEqual({ local: 0, session: 0, cookies: "" });
});
