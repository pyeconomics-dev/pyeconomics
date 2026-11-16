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
  // Each output under its name in words, with its id and its unit.
  await expect(outputs.getByRole("rowheader", { name: /^Macaulay duration\s*macaulay_duration/ })).toBeVisible();
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
  await expect(status).toContainText("1 input needs fixing before the run: Coupon rate must be 1 or less");
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
  // Plotly is its bundle and its stylesheet; src/lib/plotly.ts, the small
  // loader the calculator and the data explorer share, is not.
  const isPlotly = (path: string) => /\/plotly-basic\.min\.[\w-]+\.js$|\/plotly\.[\w-]+\.css$/.test(path);
  page.on("request", (request) => loaded.push(new URL(request.url()).pathname));
  await openCalculator(page, "/models/econometrics/ols/");
  expect(loaded.some(isPlotly)).toBe(false);
  await run(page);
  expect(api.requests).toHaveLength(1);
  await expect(page.locator("#calculator .js-plotly-plot svg.main-svg").first()).toBeVisible();
  expect(loaded.filter(isPlotly).length).toBe(2);
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
  // The title and each field's error, as text; the detail, which repeats the
  // field errors in the API's own words, is left out when there are any.
  await expect(panel.getByText(`Invalid input ${markup}`)).toBeVisible();
  await expect(panel.locator("li")).toHaveText([`Coupon rate: Too high ${markup}`]);
  await expect(panel).not.toContainText("The inputs failed");
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
  // The snippets are in view beside the form, one at a time, chosen from a row of buttons.
  const code = page.locator("#calculator [data-snippets]");
  await expect(code.locator("[data-snippet=python] pre")).toBeVisible();
  const text = async (kind: string) => {
    await code.locator(`[data-snippet-tab=${kind}]`).click();
    await expect(code.locator(`[data-snippet-tab=${kind}]`)).toHaveAttribute("aria-pressed", "true");
    return (await code.locator(`[data-snippet=${kind}] pre`).textContent()) ?? "";
  };
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

// Phase 5 Step 18's round 1. The class, not the instance: a result must be
// readable on a phone with no sideways scroll, whatever the model's outputs.
for (const path of ["/models/performance/risk-adjusted/", "/models/fixed-income/bond-pricing/", "/models/macro/policy-rule/"]) {
  test(`a result on ${path} fits a phone: every value and unit, with no sideways scroll`, async ({ page, api }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openCalculator(page, path);
    await run(page);
    const outputs = page.locator("#calculator [data-outputs]");
    await expect(outputs).toBeVisible();
    const fit = await outputs.evaluate((table) => {
      const within = (element: Element) => element.getBoundingClientRect().right <= window.innerWidth + 0.5;
      const scrollers = [...document.querySelectorAll("#calculator [data-outcome] *")].filter((element) => {
        const style = getComputedStyle(element);
        return ["auto", "scroll"].includes(style.overflowX) && element.scrollWidth > element.clientWidth + 1 && element.tagName !== "PRE";
      });
      return {
        table: within(table),
        cells: [...table.querySelectorAll("th, td")].every(within),
        units: [...table.querySelectorAll("[data-unit]")].every(within),
        scrollers: scrollers.map((element) => element.tagName.toLowerCase()),
        page: document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      };
    });
    expect(fit).toEqual({ table: true, cells: true, units: true, scrollers: [], page: true });
    expect(api.requests).toHaveLength(1);
  });
}

test("the form asks first for what a run needs, names its options, and keeps optional inputs in a disclosure", async ({ page }) => {
  await openCalculator(page, "/models/fixed-income/bond-pricing/");
  const form = page.locator("#calculator form");
  // The fields a run cannot do without come first, in the model's own order.
  const labels = await form.locator("[data-fields] label").allTextContents();
  expect(labels.map((label) => label.replace("*", "").trim()).slice(0, 4)).toEqual([
    "Settlement",
    "Maturity",
    "Coupon rate",
    "Yield to maturity",
  ]);
  // An option reads as words, with its id beside a name that does not spell it.
  await expect(form.getByLabel("Day count").locator("option").first()).toHaveText("Actual/Actual ICMA (act_act_icma)");
  await expect(form.getByLabel("Frequency").locator("option").first()).toHaveText("Annual");
  // An example is named in words, and its note sits under the picker.
  const picker = page.locator("#calculator").getByLabel("Start from an example");
  await expect(picker.locator("option").first()).toHaveText("Treasury thirty year");
  await expect(page.locator("#calculator [data-example-note]")).toContainText("31 CFR Part 356");
  // A field that may be left out waits in a disclosure that names it.
  const optional = form.locator("[data-optional-fields]");
  await expect(optional.locator("summary")).toContainText("1 optional input");
  await expect(optional.locator("summary")).toContainText("Issue date");
  expect(await optional.evaluate((details) => (details as HTMLDetailsElement).open)).toBe(false);
  await optional.locator("summary").click();
  expect(await optional.evaluate((details) => (details as HTMLDetailsElement).open)).toBe(true);
  await expect(optional.getByRole("combobox").first()).toBeVisible();
  await expect(optional.getByRole("combobox").first().locator("option")).toHaveText(["Enter a value", "Leave it out"]);
});

test("an error about two inputs together marks both, in plain words, once", async ({ page, api, watch }) => {
  await openCalculator(page, "/models/fixed-income/bond-pricing/");
  const form = page.locator("#calculator form");
  await form.getByLabel(/^Settlement/).fill("2031-01-01");
  await form.getByLabel(/^Maturity/).fill("2026-01-01");
  await page.locator("#calculator").getByRole("button", { name: "Run", exact: true }).click();
  const problem = page.locator("#calculator [data-problem=invalid-input]");
  await expect(problem).toBeVisible();
  // Once, in a reader's words: no calculation name, no "Value error".
  await expect(problem.locator("li")).toHaveText(["Settlement must be before maturity"]);
  await expect(problem).not.toContainText("Value error");
  await expect(problem).not.toContainText("price_from_yield");
  // Both fields the message names carry it, each under its own input.
  await expect(form.locator("[data-fields]").getByText("Settlement must be before maturity", { exact: true })).toHaveCount(2);
  for (const label of [/^Settlement/, /^Maturity/]) {
    const described = (await form.getByLabel(label).getAttribute("aria-describedby")) ?? "";
    const error = described.split(" ").find((id) => id.endsWith("__error")) ?? "";
    await expect(form.locator(`[id="${error}"]`)).toHaveText("Settlement must be before maturity");
  }
  expect(api.requests).toHaveLength(1);
  expect(watch.violations).toEqual([]);
});

test("a run says it finished, shows the manifest's hashes, and names the model's two MCP tools", async ({ page, api }) => {
  await openCalculator(page, "/models/performance/risk-adjusted/");
  await run(page);
  const result = page.locator("#calculator [data-outcome=result]");
  await expect(result.locator("[data-run-summary]")).toHaveText("The run finished: 16 outputs, no warnings.");
  const manifest = result.locator("[data-manifest]");
  await manifest.locator("summary").click();
  await expect(manifest).toContainText("Inputs SHA-256");
  await expect(manifest.locator("dd").filter({ hasText: /^[0-9a-f]{64}$/ })).toHaveCount(2);
  const code = page.locator("#calculator [data-snippets]");
  await code.locator("[data-snippet-tab=mcp]").click();
  await expect(code.locator("[data-mcp-note]")).toContainText("run_model");
  await expect(code.locator("[data-mcp-note]")).toContainText("performance_risk_adjusted");
  expect(api.requests).toHaveLength(1);
});
