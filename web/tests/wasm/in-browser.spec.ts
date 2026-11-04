// web/tests/wasm/in-browser.spec.ts
// The documentation's in-browser examples: each exported page loads Pyodide and
// the pinned pyeconomics wheel, and runs a model until its first result shows.
// Every request a page makes is held to what it may fetch: the core files of the
// runtime marimo loads, marimo's frontend at the version the lockfile holds, and
// what docs/wasm/pyodide-lock.json pins. A page itself makes only a handful of
// requests to its own host, which is why it is exported as a single file: Read the
// Docs answers 429 to the 310 a page makes otherwise. The result is a figure the
// model works out, so seeing it proves the wheel ran, not only that the page drew.
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
const FRONTEND = `https://cdn.jsdelivr.net/npm/@marimo-team/frontend@${LOCK.packages["marimo-base"]?.version ?? ""}/dist/`;
// Read the Docs adds its own script to every page it serves, and that script
// shows an ad: no part of a page, so this holds only on a deployed copy.
const HOSTED = process.env.WASM_BASE_URL
  ? ["https://media.ethicalads.io/", "https://server.ethicalads.io/"]
  : [];
const MOST_FROM_OWN_HOST = 12;

const PAGES = [
  { page: "time-value.html", result: "Present value: 61.39" },
  { page: "bond-price-duration.html", result: "Price per 100 of face value: 96.10" },
  {
    page: "mean-variance-frontier.html",
    result: "Minimum-variance portfolio: a return of 9.70% at a volatility of 13.33%",
  },
];

/** What a page fetched, split into its own host's requests and everyone else's. */
function watchRequests(page: Page, origin: string) {
  const fetched: string[] = [];
  const ownHost: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.protocol.startsWith("http")) {
      (url.origin === origin ? ownHost : fetched).push(request.url());
    }
  });
  return { fetched, ownHost };
}

function isAllowed(url: string): boolean {
  return (
    PINNED.has(url) ||
    RUNTIME.includes(url) ||
    url.startsWith(FRONTEND) ||
    HOSTED.some((prefix) => url.startsWith(prefix))
  );
}

for (const { page: name, result } of PAGES) {
  test(`${name} runs a model in the browser and fetches only what is pinned`, async ({
    baseURL,
    page,
  }) => {
    const { fetched, ownHost } = watchRequests(page, new URL(baseURL ?? "").origin);
    await page.goto(name);

    await expect(
      page.getByText("runs entirely in your browser and needs no install"),
    ).toBeVisible({ timeout: 60_000 });
    // Loading Python and the wheels is the slow part; a result ends it.
    await expect(page.getByText(result)).toBeVisible({ timeout: 180_000 });

    expect(fetched).toContain(CORE_WHEEL);
    expect(fetched.filter((url) => !isAllowed(url))).toEqual([]);
    expect(ownHost.length).toBeLessThanOrEqual(MOST_FROM_OWN_HOST);
  });
}

test("a value the reader types reaches the model and stays on the page", async ({
  page,
}) => {
  await page.goto("time-value.html");
  await expect(page.getByText("Present value: 61.39")).toBeVisible({ timeout: 180_000 });

  // The page's promise: what happens from here on, in full, goes nowhere with it.
  const sent: string[] = [];
  page.on("request", (request) => {
    sent.push(`${request.url()} ${request.postData() ?? ""}`);
  });
  const finalSum = page.getByRole("textbox", { name: "Final sum" });
  await finalSum.fill("987650");
  await finalSum.press("Enter");

  await expect(page.getByText("Present value: 606,331.42")).toBeVisible({
    timeout: 30_000,
  });
  expect(sent.filter((request) => request.includes("987650"))).toEqual([]);
});
