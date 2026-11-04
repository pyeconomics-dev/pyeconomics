// web/tests/wasm/in-browser.spec.ts
// The documentation's in-browser examples: each exported page loads Pyodide and
// the pinned pyeconomics wheel, and runs a model until its first result shows.
// Every request a page makes is held to what it may fetch: its own origin, the
// core files of the runtime marimo loads, and what docs/wasm/pyodide-lock.json
// pins. The result is a figure the model works out, so seeing it proves the
// wheel ran, not only that the page drew.
import { readFileSync } from "node:fs";

import { expect, type Page, test } from "@playwright/test";

interface LockEntry {
  name: string;
  file_name: string;
  version: string;
}

const LOCK = JSON.parse(
  readFileSync(new URL("../../../docs/wasm/pyodide-lock.json", import.meta.url), "utf8"),
) as { packages: Record<string, LockEntry> };

const PINNED = new Set(Object.values(LOCK.packages).map((entry) => entry.file_name));
// The interpreter marimo's export loads; pin_wasm.py says why the wheels are newer.
const RUNTIME = ["pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip"].map(
  (file) => `https://cdn.jsdelivr.net/pyodide/v314.0.0/full/${file}`,
);
const CORE_WHEEL = LOCK.packages.pyeconomics?.file_name ?? "";

const PAGES = [
  { page: "time-value.html", result: "Present value: 61.39" },
  { page: "bond-price-duration.html", result: "Price per 100 of face value: 96.10" },
  {
    page: "mean-variance-frontier.html",
    result: "Minimum-variance portfolio: a return of 9.70% at a volatility of 13.33%",
  },
];

/** What a page fetched from anywhere but its own origin. */
function watchRequests(page: Page, origin: string): string[] {
  const fetched: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.protocol.startsWith("http") && url.origin !== origin) {
      fetched.push(request.url());
    }
  });
  return fetched;
}

for (const { page: name, result } of PAGES) {
  test(`${name} runs a model in the browser and fetches only what is pinned`, async ({
    baseURL,
    page,
  }) => {
    const fetched = watchRequests(page, new URL(baseURL ?? "").origin);
    await page.goto(name);

    await expect(
      page.getByText("runs entirely in your browser and needs no install"),
    ).toBeVisible({ timeout: 60_000 });
    // Loading Python and the wheels is the slow part; a result ends it.
    await expect(page.getByText(result)).toBeVisible({ timeout: 180_000 });

    expect(fetched).toContain(CORE_WHEEL);
    expect(fetched.filter((url) => !PINNED.has(url) && !RUNTIME.includes(url))).toEqual(
      [],
    );
  });
}

test("a value the reader types reaches the model", async ({ page }) => {
  await page.goto("time-value.html");
  await expect(page.getByText("Present value: 61.39")).toBeVisible({ timeout: 180_000 });

  const periods = page.getByRole("textbox", { name: "Periods" });
  await periods.fill("20");
  await periods.press("Enter");

  await expect(page.getByText("Present value: 37.69")).toBeVisible({ timeout: 30_000 });
});
