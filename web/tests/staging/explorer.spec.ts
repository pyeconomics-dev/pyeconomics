// web/tests/staging/explorer.spec.ts
// The deployed data explorer and user data (Phase 5 Step 9's Deployed &
// verified check), through Cloudflare Access with the service token: the
// staging API's /v1/series/ answers a hosted-safe concept with ?transform=yoy
// and records the transform; /data/ charts the same concept with its
// attribution drawn on the chart; and a run fed from an uploaded CSV returns
// its result while the browser's network log holds no request to another
// origin and no API request but the run's one same-origin POST.
import { fileURLToPath } from "node:url";

import { expect, test } from "../e2e/support.ts";

const CONCEPT = "us.unemployment.rate";
const BLS = "Source: U.S. Bureau of Labor Statistics.";

test("the series route applies a transform and records it", async ({ request }) => {
  const response = await request.get(`/v1/series/${CONCEPT}`, { params: { start: "2020-01-01", transform: "yoy" } });
  expect(response.status()).toBe(200);
  const body = (await response.json()) as { frame: { index: string[] }; sources: { transforms: string[] }[]; attributions: string[] };
  expect(body.frame.index.length).toBeGreaterThan(12);
  expect((body.frame.index.at(0) ?? "") >= "2020-01-01").toBe(true);
  for (const record of body.sources) expect(record.transforms.at(-1)).toBe("yoy");
  expect(body.attributions).toContain(BLS);
});

test("the explorer charts the concept with its attribution drawn on the chart", async ({ page, watch }) => {
  await page.goto("/data/us/unemployment/rate/");
  const section = page.locator("#chart");
  await section.scrollIntoViewIfNeeded();
  await expect(section.locator("[data-series-explorer][data-ready=fetch][data-hydrated=true]")).toBeVisible({ timeout: 30_000 });
  await page.getByLabel("Transform").selectOption("yoy");
  await page.getByRole("button", { name: "Draw the chart" }).click();
  await expect(section.getByRole("status")).toContainText("Done:", { timeout: 60_000 });
  await expect(page.locator("[data-series-chart] .annotation-text")).toContainText(BLS);
  await expect(page.locator("[data-series-chart] .annotation-text")).toContainText("Data as of");
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});

test("a run fed from an uploaded CSV returns its result, and only its POST leaves the browser", async ({ page, network, watch }) => {
  await page.goto("/models/equity/cape/");
  const section = page.locator("#calculator");
  await section.scrollIntoViewIfNeeded();
  await expect(section.locator("[data-calculator][data-ready=true]")).toBeVisible({ timeout: 30_000 });
  const start = network.requests.length;
  const panel = page.locator("[data-user-data]");
  await panel.locator("summary").click();
  await panel.getByLabel("File").setInputFiles(fileURLToPath(new URL("../e2e/fixtures/user-data.csv", import.meta.url)));
  await expect(panel.getByRole("status")).toContainText("Read 480 rows");
  await panel.locator("[data-map-field=cpi] select").selectOption({ label: "cpi" });
  await panel.locator("[data-map-field=earnings] select").selectOption({ label: "earnings" });
  await panel.getByRole("button", { name: "Fill the form" }).click();
  await expect(panel.getByRole("status")).toContainText("Filled cpi, earnings from the file.");
  await section.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Result", exact: true })).toBeFocused({ timeout: 60_000 });

  const here = new URL(page.url()).origin;
  const sent = network.requests.slice(start).filter((r) => !r.url.startsWith(`blob:${here}/`));
  expect(sent.filter((r) => !r.url.startsWith(`${here}/`)).map((r) => r.url)).toEqual([]);
  const others = sent.filter((r) => !/\/_astro\/[^/]+\.js$/.test(new URL(r.url).pathname));
  expect(others.map((r) => `${r.method} ${new URL(r.url).pathname}`)).toEqual(["POST /v1/models/equity.cape/run"]);
  const body = others[0]?.body?.toString("utf8") ?? "";
  for (const forbidden of ["user-data.csv", "PRIVATE-MARKER", "example.org", "HYPERLINK"]) expect(body).not.toContain(forbidden);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});
