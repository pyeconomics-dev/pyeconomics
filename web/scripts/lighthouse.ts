// web/scripts/lighthouse.ts
// Lighthouse on decision 19's page sample (ADR-0013): for each sample page the
// build wrote, three mobile runs against `wrangler dev`, and the median score
// of each category must be at least 90. It drives Lighthouse 13 directly in
// Playwright's Chromium: @lhci/cli 0.15.1, last published in June 2025,
// bundles Lighthouse 12.6.1 and a dependency tree that fails `npm audit` at
// high. Reports go to .lighthouse/ (git-ignored), one JSON file per run.
//
// Usage, after `npm run build`: npm run lighthouse
import { execFileSync, spawn, type ChildProcess } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";
import * as chromeLauncher from "chrome-launcher";
import lighthouse from "lighthouse";

const WEB = fileURLToPath(new URL("..", import.meta.url));
const PORT = 8788;
const ORIGIN = `http://127.0.0.1:${PORT}`;
const RUNS = 3;
const MINIMUM = 0.9;

/** Decision 19's thirteen pages; those the build has not written yet are skipped. */
export const SAMPLE = [
  "/",
  "/models/",
  "/models/fixed-income/",
  "/models/fixed-income/bond-pricing/",
  "/models/foundations/time-value/",
  "/models/macro/policy-rule/",
  "/models/econometrics/garch/",
  "/data/",
  "/search/",
  "/coverage/",
  "/sources/",
  "/legal/privacy/",
  "/problems/invalid-input/",
] as const;

export const CATEGORIES = ["performance", "accessibility", "best-practices", "seo"] as const;

/** The median of an odd number of scores. */
export function median(scores: readonly number[]): number {
  const sorted = [...scores].sort((a, b) => a - b);
  const middle = sorted[Math.floor(sorted.length / 2)];
  if (middle === undefined) throw new Error("no scores");
  return middle;
}

/** The sample pages the build wrote, under `dist`. */
export function built(dist: string): string[] {
  // Fixed sample paths under the build output.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  return SAMPLE.filter((path) => existsSync(join(dist, path, "index.html")));
}

async function answers(): Promise<boolean> {
  try {
    return (await fetch(`${ORIGIN}/version.json`)).ok;
  } catch {
    return false;
  }
}

async function serve(): Promise<ChildProcess> {
  // Another server on the port would be measured instead of this build.
  if (await answers()) throw new Error(`${ORIGIN} is already serving; stop that server first`);
  // wrangler's own entry point, run by this Node with fixed arguments and no shell.
  const wrangler = join(WEB, "node_modules", "wrangler", "bin", "wrangler.js");
  const server = spawn(
    process.execPath,
    [wrangler, "dev", "--ip", "127.0.0.1", "--port", String(PORT)],
    // Its own process group, so stop() can end workerd with it.
    { cwd: WEB, stdio: "ignore", detached: process.platform !== "win32" },
  );
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (await answers()) return server;
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  stop(server);
  throw new Error(`wrangler dev did not answer on ${ORIGIN}`);
}

/** Stop wrangler and the workerd it started: the whole process tree. */
function stop(server: ChildProcess): void {
  if (server.pid === undefined || server.exitCode !== null) return;
  if (process.platform === "win32") {
    // A fixed command; the pid is our own child's.
    execFileSync("taskkill", ["/pid", String(server.pid), "/T", "/F"], { stdio: "ignore" });
  } else {
    process.kill(-server.pid, "SIGTERM");
  }
}

async function main(): Promise<number> {
  const pages = built(join(WEB, "dist"));
  if (pages.length === 0) {
    process.stderr.write("lighthouse: no sample page in dist/; run `npm run build`\n");
    return 1;
  }
  const reports = join(WEB, ".lighthouse");
  // A fixed directory under web/.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  mkdirSync(reports, { recursive: true });
  const server = await serve();
  const chrome = await chromeLauncher.launch({
    chromePath: chromium.executablePath(),
    chromeFlags: ["--headless=new", "--no-sandbox"],
  });
  const failures: string[] = [];
  try {
    for (const path of pages) {
      const scores = new Map<string, number[]>(CATEGORIES.map((category) => [category, []]));
      for (let run = 1; run <= RUNS; run += 1) {
        const result = await lighthouse(`${ORIGIN}${path}`, {
          port: chrome.port,
          output: "json",
          logLevel: "error",
          onlyCategories: [...CATEGORIES],
        });
        if (!result) throw new Error(`Lighthouse returned nothing for ${path}`);
        const name = `${path.replaceAll("/", "_") || "_"}run${run}.json`;
        // A name built from a fixed sample path, under .lighthouse/.
        // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
        writeFileSync(join(reports, name), String(result.report));
        const found = new Map(Object.entries(result.lhr.categories));
        for (const category of CATEGORIES) {
          scores.get(category)?.push(found.get(category)?.score ?? 0);
        }
      }
      const line = CATEGORIES.map((category) => {
        const score = median(scores.get(category) ?? []);
        if (score < MINIMUM) failures.push(`${path} ${category} ${Math.round(score * 100)}`);
        return `${category} ${Math.round(score * 100)}`;
      }).join(", ");
      process.stdout.write(`lighthouse ${path}: ${line} (median of ${RUNS} mobile runs)\n`);
    }
  } finally {
    chrome.kill();
    stop(server);
  }
  if (failures.length > 0) {
    process.stderr.write(
      `lighthouse: below ${MINIMUM * 100} (ADR-0013 decision 19):\n${failures.map((f) => `  ${f}`).join("\n")}\n`,
    );
    return 1;
  }
  return 0;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  process.exit(await main());
}
