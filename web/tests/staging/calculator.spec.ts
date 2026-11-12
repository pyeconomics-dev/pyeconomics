// web/tests/staging/calculator.spec.ts
// The deployed site's calculator (Phase 5 Step 6's Deployed & verified
// check): /version.json reports the commit deployed, and the duration page's
// calculator, filled with its first example, runs against the staging API on
// the same origin and shows the result, with no Content Security Policy
// violation or console error.
import { expect, test } from "./support.ts";

test("staging serves the commit deployed", async ({ request }) => {
  const response = await request.get("/version.json");
  expect(response.status()).toBe(200);
  const body = (await response.json()) as { git_sha: string };
  expect(body.git_sha).toMatch(/^[0-9a-f]{40}$/);
  if (process.env.GIT_SHA) expect(body.git_sha).toBe(process.env.GIT_SHA);
});

test("the duration calculator runs against the staging API and shows the result", async ({ page, watch }) => {
  const runs: number[] = [];
  page.on("response", (response) => {
    if (new URL(response.url()).pathname === "/v1/models/fixed_income.duration/run") runs.push(response.status());
  });
  await page.goto("/models/fixed-income/duration/");
  const section = page.locator("#calculator");
  await section.scrollIntoViewIfNeeded();
  await expect(section.locator("[data-calculator][data-ready=true]")).toBeVisible({ timeout: 30_000 });
  await section.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Result", exact: true })).toBeFocused({ timeout: 60_000 });
  const outputs = page.getByRole("table", { name: "Outputs of this run" });
  await expect(outputs.getByRole("rowheader", { name: /^macaulay_duration/ })).toBeVisible();
  expect(runs).toEqual([200]);
  expect(watch.violations).toEqual([]);
  expect(watch.errors).toEqual([]);
});
