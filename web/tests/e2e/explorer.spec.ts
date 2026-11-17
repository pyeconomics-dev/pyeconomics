// web/tests/e2e/explorer.spec.ts
// The data explorer (Phase 5 Step 9; ADR-0013 decision 11), served as
// Cloudflare serves it, with the page's /v1/ and /version requests forwarded
// to the local hosted-mode API over stand-in providers (support.ts `api`):
// /data/ lists every concept by topic and searches them; a concept the
// snapshot serves is read through GET /v1/series/ and charted as soon as its
// explorer is in view (Step 18), with its attribution and as-of date drawn on
// the chart and a line to cite it by; it is transformed by the catalog's own transforms, and
// downloaded through ?format= with its attribution in the file; a concept the
// hosted site does not serve gives the local command and is never fetched.
// Every test fails on a Content Security Policy violation or console error.
import { readFileSync } from "node:fs";

import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { expect, test } from "./support.ts";

const AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const UNEMPLOYMENT = "/data/us/unemployment/rate/";
const BLS = "Source: U.S. Bureau of Labor Statistics.";

const concepts = (
  JSON.parse(readFileSync(new URL("../../src/data/generated/concepts.json", import.meta.url), "utf8")) as {
    concepts: { id: string; snapshot: boolean }[];
  }
).concepts;

/**
 * Open a concept page and wait for its explorer to decide what it offers; a
 * concept the site serves is then charted without a click, which is waited for.
 */
async function openConcept(page: Page, path: string, offer: string): Promise<void> {
  await page.goto(path);
  const section = page.locator("#chart");
  await section.scrollIntoViewIfNeeded();
  await expect(section.locator(`[data-series-explorer][data-ready=${offer}][data-hydrated=true]`)).toBeVisible();
  if (offer !== "fetch") return;
  await expect(section.getByRole("status")).toContainText("Done:");
  await expect(page.locator("[data-series-chart] .main-svg").first()).toBeVisible();
}

/** Press "Draw the chart" and wait for the series it asks for. */
async function draw(page: Page): Promise<void> {
  const answered = page.waitForResponse((response) => new URL(response.url()).pathname.startsWith("/v1/series/"));
  await page.getByRole("button", { name: "Draw the chart" }).click();
  await answered;
  await expect(page.locator("#chart").getByRole("status")).toContainText("Done:");
  await expect(page.locator("[data-series-chart] .main-svg").first()).toBeVisible();
}

// The search asks the server's mode (GET /version), which only the `api` fixture answers here.
test("/data/ lists every concept and searches by title, id, unit, frequency and topic", async ({ page, api, watch }) => {
  await page.goto("/data/");
  const list = page.locator("[data-concept-list] [data-concept]");
  await expect(list).toHaveCount(concepts.length);
  await expect(page.locator("[data-concept-search][data-ready=true]")).toBeVisible();
  // With no words, the list is read by topic, each topic a heading a link above jumps to.
  const topics = page.locator("[data-concept-list] [data-topic]");
  expect(await topics.count()).toBeGreaterThan(5);
  await page.getByRole("navigation", { name: "Topics" }).getByRole("link", { name: /^Labour/ }).click();
  await expect(page).toHaveURL(/#topic-labour$/);
  await expect(page.getByRole("heading", { name: "Labour", exact: true })).toBeInViewport();
  await page.getByLabel("Search the series").fill("unemployment rate");
  await expect(list.first()).toHaveAttribute("data-concept", "us.unemployment.rate");
  await expect(topics).toHaveCount(0);
  await page.getByLabel("Only the series this site charts").check();
  const served = await list.evaluateAll((items) => items.map((item) => item.textContent ?? ""));
  expect(served.every((text) => text.includes("Charted on this site"))).toBe(true);
  await page.getByLabel("Search the series").fill("");
  await expect(list).toHaveCount(concepts.filter((concept) => concept.snapshot).length);
  // The list asks the API nothing; a concept's own page does.
  expect(api.requests).toEqual([]);
  await list.first().getByRole("link").click();
  await expect(page).toHaveURL(/\/data\/[a-z0-9/-]+\/$/);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("a served concept charts with its attribution and as-of date drawn on the chart", async ({ page, api, watch }) => {
  await openConcept(page, UNEMPLOYMENT, "fetch");
  await expect(page.getByRole("table", { name: /Candidates of/ })).toContainText("hosted-safe");
  await expect(page.locator("[data-reads]").first()).toBeVisible();
  // The chart was drawn when the explorer came into view: one request, no click.
  expect(api.requests).toHaveLength(1);
  const [request] = api.requests;
  expect(request?.method).toBe("GET");
  expect(request?.url).toMatch(/^\/v1\/series\/us\.unemployment\.rate\?start=\d{4}-\d{2}-\d{2}&end=\d{4}-\d{2}-\d{2}$/);
  await expect(page.locator("[data-series-chart] .annotation-text")).toContainText(BLS);
  await expect(page.locator("[data-series-chart] .annotation-text")).toContainText("Data as of");
  await expect(page.locator("[data-chart-note]")).toContainText(BLS);
  await expect(page.locator("#chart").getByRole("heading", { name: "Sources" })).toBeVisible();
  // The chart is headed by the concept's own title and unit, and a line to cite the series by follows it.
  await expect(page.locator("[data-series-chart] .gtitle")).toHaveText("Unemployment rate");
  await expect(page.locator("[data-series-chart] .ytitle")).toHaveText("Percent");
  const citation = page.locator("#chart [data-citation]");
  await expect(citation).toContainText("US Bureau of Labor Statistics. Unemployment rate, series LNS14000000.");
  await expect(citation).toContainText("pyeconomics: https://pyeconomics.dev/data/us/unemployment/rate/");
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("a transform reaches the series route and is recorded in the sources", async ({ page, api, watch }) => {
  await openConcept(page, UNEMPLOYMENT, "fetch");
  await page.getByLabel("Transform").selectOption("diff");
  await page.getByLabel("Periods back").fill("12");
  await draw(page);
  expect(api.requests.at(-1)?.url).toMatch(/&transform=diff%28periods%3D12%29$|&transform=diff\(periods%3D12\)$/);
  await expect(page.locator("#chart dd").filter({ hasText: "diff(periods=12)" }).first()).toBeVisible();
  await page.getByLabel("Transform").selectOption("convert");
  await page.getByLabel("Method").selectOption("last");
  await draw(page);
  expect(decodeURIComponent(api.requests.at(-1)?.url ?? "")).toContain("transform=convert(to=quarterly,method=last)");
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("a download is the same request with ?format= and carries the attribution", async ({ page, api, watch }) => {
  await openConcept(page, UNEMPLOYMENT, "fetch");
  await draw(page);
  const download = page.waitForEvent("download");
  await page.locator("#chart").getByRole("button", { name: "CSV", exact: true }).click();
  const file = await download;
  expect(api.requests.at(-1)?.url).toBe(`${api.requests[0]?.url ?? ""}&format=csv`);
  const csv = readFileSync((await file.path()) ?? "", "utf8");
  expect(csv).toMatch(/^# pyeconomics: /);
  expect(csv).toContain(`# attribution: ${BLS}`);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("a concept the hosted site does not serve gives the local command and is never fetched", async ({ page, api, watch }) => {
  await openConcept(page, "/data/factors/ff3/us/monthly/", "local");
  await expect(page.locator("[data-offer=local]")).toContainText("pyeconomics data get factors.ff3.us.monthly");
  await expect(page.locator("[data-offer=local]")).toContainText('pip install "pyeconomics[app]"');
  await expect(page.getByRole("button", { name: "Draw the chart" })).toHaveCount(0);
  expect(api.requests).toEqual([]);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("a concept with parameters gives the Python call", async ({ page, api, watch }) => {
  await openConcept(page, "/data/us/sep/unemployment/", "parameters");
  await expect(page.locator("[data-offer=parameters]")).toContainText('pyeconomics.data.get("us.sep.unemployment", parameters=');
  expect(api.requests).toEqual([]);
  expect(watch.violations).toEqual([]);
});

test("a table charts the column chosen", async ({ page, api, watch }) => {
  await openConcept(page, "/data/us/treasury/par-curve/", "fetch");
  expect(api.requests[0]?.url).toMatch(/^\/v1\/series\/us\.treasury\.par_curve\?start=/);
  const column = page.getByLabel("Column");
  const options = await column.locator("option").allTextContents();
  expect(options.length).toBeGreaterThan(1);
  await column.selectOption({ index: 1 });
  await expect(page.locator("[data-series-chart] .gtitle")).toContainText(options[1] ?? "");
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("axe finds no WCAG 2.2 AA violation on /data/ and on a concept page with its chart", async ({ page, api, watch }) => {
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await page.goto("/data/");
    await expect(page.locator("[data-concept-search][data-ready=true]")).toBeVisible();
    let results = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
    expect(results.violations.map((v) => `${colorScheme} /data/ ${v.id}: ${v.help}`)).toEqual([]);
    await openConcept(page, UNEMPLOYMENT, "fetch");
    results = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
    expect(results.violations.map((v) => `${colorScheme} chart ${v.id}: ${v.help}`)).toEqual([]);
  }
  expect(api.requests.length).toBeGreaterThan(0);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});
