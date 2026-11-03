// web/tests/e2e/user-data.spec.ts
// The privacy proof of "use my own data" (Phase 5 Step 9; ADR-0013 decision
// 11). On a library-only model's page (equity.cape: Shiller's data, which the
// hosted site may not serve), a CSV and an XLSX are uploaded that hold
// formulas, a link to another origin, a reference into an external workbook,
// a marker in a column no field maps, and a column longer than any field
// takes (tests/web/build_user_data_fixtures.py). The file is read in a Web
// Worker; the long column is refused; the mapped columns fill the form; the
// model runs. The browser's whole network log (support.ts `network`) then
// holds no request to another origin, no API request but the one same-origin
// POST of the run, and nothing of the file in that POST: not its name, its
// marker, its formulas or its link, only the values the run takes.
import { fileURLToPath } from "node:url";

import type { Page } from "@playwright/test";

import { expect, test, type NetworkLog } from "./support.ts";

const CAPE = "/models/equity/cape/";
const FIXTURES = new URL("./fixtures/", import.meta.url);
const MARKER = "PRIVATE-MARKER-7c41";
const ELSEWHERE = "files.example.org";
const CPI = [220, 225, 230, 236, 241, 246, 252, 260, 275, 290];
const EARNINGS = [100, 105, 98, 120, 140, 150, 160, 170, 190, 210];

async function openCalculator(page: Page): Promise<void> {
  await page.goto(CAPE);
  const section = page.locator("#calculator");
  await section.scrollIntoViewIfNeeded();
  await expect(section.locator("[data-calculator][data-ready=true]")).toBeVisible();
}

function origin(page: Page): string {
  return new URL(page.url()).origin;
}

/** The requests after the page and its scripts loaded: what the upload and the run sent. */
function sentSince(network: NetworkLog, start: number): NetworkLog["requests"] {
  return network.requests.slice(start);
}

for (const name of ["user-data.csv", "user-data.xlsx"]) {
  test(`a ${name.split(".")[1]?.toUpperCase() ?? ""} file never leaves the browser: only the mapped values travel, in the run's POST`, async ({
    page,
    api,
    network,
    watch,
  }) => {
    await openCalculator(page);
    await expect(page.locator("[data-library-only]")).toContainText("library-only");
    await expect(page.locator("[data-library-only]")).toContainText('pip install "pyeconomics[app]"');
    const start = network.requests.length;
    const panel = page.locator("[data-user-data]");
    await panel.locator("summary").click();
    await panel.getByLabel("File").setInputFiles(fileURLToPath(new URL(name, FIXTURES)));
    await expect(panel.getByRole("status")).toContainText("Read 480 rows and 5 columns. It holds more rows than any field takes");
    await expect(panel.getByRole("region", { name: "The file's first rows" })).toContainText("cpi");

    // The long column is refused: more rows than the field takes.
    await panel.locator("[data-map-field=cpi] select").selectOption({ label: "long" });
    await panel.getByRole("button", { name: "Fill the form" }).click();
    await expect(panel.locator("[data-map-field=cpi]")).toContainText("runs past the 480 rows read");

    // The marker column is refused: it is not a number.
    await panel.locator("[data-map-field=earnings] select").selectOption({ label: "note" });
    await panel.getByRole("button", { name: "Fill the form" }).click();
    await expect(panel.locator("[data-map-field=earnings]")).toContainText("is not a number");

    await panel.locator("[data-map-field=cpi] select").selectOption({ label: "cpi" });
    await panel.locator("[data-map-field=earnings] select").selectOption({ label: "earnings" });
    await panel.getByRole("button", { name: "Fill the form" }).click();
    await expect(panel.getByRole("status")).toContainText("Filled cpi, earnings from the file.");

    await page.locator("#calculator").getByRole("button", { name: "Run", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Result", exact: true })).toBeFocused();

    const sent = sentSince(network, start);
    const here = origin(page);
    // A blob: URL is the browser's own memory (the parsers' inner workers), never the network.
    const inBrowser = (url: string) => url.startsWith(`blob:${here}/`);
    expect(sent.filter((r) => !r.url.startsWith(`${here}/`) && !inBrowser(r.url)).map((r) => r.url)).toEqual([]);
    expect(sent.some((request) => request.url.includes(ELSEWHERE))).toBe(false);
    // The file was read by the worker, whose script the page loaded from its own origin.
    expect(sent.some((r) => /^\/_astro\/parse-file[\w.-]*\.js$/.test(new URL(r.url).pathname))).toBe(true);
    // Besides the worker's own script, the only request is the run's POST.
    const others = sent.filter((r) => !inBrowser(r.url) && !/\/_astro\/[^/]+\.js$/.test(new URL(r.url).pathname));
    expect(others.map((request) => `${request.method} ${new URL(request.url).pathname}`)).toEqual(["POST /v1/models/equity.cape/run"]);
    const body = others[0]?.body?.toString("utf8") ?? "";
    for (const forbidden of [name, MARKER, ELSEWHERE, "HYPERLINK", "SUM(", "external.xlsx", "1599"]) {
      expect(body, forbidden).not.toContain(forbidden);
    }
    const inputs = JSON.parse(body) as Record<string, unknown>;
    expect(inputs.cpi).toEqual(CPI);
    expect(inputs.earnings).toEqual(EARNINGS);
    expect(api.requests).toHaveLength(1);
    expect(watch.violations).toEqual([]);
    expect(watch.errors).toEqual([]);
  });
}

test("a template CSV downloads with no request", async ({ page, network, watch }) => {
  await openCalculator(page);
  const panel = page.locator("[data-user-data]");
  await panel.locator("summary").click();
  const start = network.requests.length;
  const download = page.waitForEvent("download");
  await panel.getByRole("button", { name: "Download a template CSV" }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe("equity_cape_template.csv");
  expect(sentSince(network, start).filter((request) => !request.url.startsWith("blob:"))).toEqual([]);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("a file of another kind is refused before it is read", async ({ page, network, watch }) => {
  await openCalculator(page);
  const panel = page.locator("[data-user-data]");
  await panel.locator("summary").click();
  const start = network.requests.length;
  await panel.getByLabel("File").setInputFiles({ name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("1,2,3") });
  await expect(panel.getByRole("status")).toContainText("not a .csv or an .xlsx file");
  expect(sentSince(network, start).filter((r) => !/\/_astro\/[^/]+\.js$/.test(new URL(r.url).pathname))).toEqual([]);
  expect(watch.violations).toEqual([]);
});
