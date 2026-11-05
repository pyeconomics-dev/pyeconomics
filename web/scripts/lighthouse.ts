// web/scripts/lighthouse.ts
// Lighthouse on decision 19's page sample (ADR-0013): for each sample page the
// build wrote, three mobile runs against `wrangler dev`, each in a Chrome of
// its own after one uncounted warm-up run, at a CPU slowdown that follows the
// host's speed, and the median score of each category must be at least 90. A
// run that measured nothing is repeated. It drives Lighthouse 13 directly in
// Playwright's Chromium: @lhci/cli 0.15.1, last published in June 2025,
// bundles Lighthouse 12.6.1 and a dependency tree that fails `npm audit` at
// high. Reports go to .lighthouse/ (git-ignored), one JSON file per run, and
// the trace of the first runs that hold a long task no script accounts for.
//
// Usage, after `npm run build`: npm run lighthouse
import { execFileSync, spawn, type ChildProcess } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";
import * as chromeLauncher from "chrome-launcher";
import lighthouse, { type RunnerResult } from "lighthouse";

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

/** The traces kept of runs with a long task no script accounts for. */
export const MAX_TRACES = 3;

/** The attempts at one run before the page is reported as not measured. */
export const ATTEMPTS = 3;

/** Lighthouse's mobile CPU slowdown, and the benchmark index of a CI runner at full speed. */
const CPU_SLOWDOWN = 4;
const FULL_SPEED_BENCHMARK = 2000;

/**
 * The CPU slowdown that keeps the simulated phone the same on any host.
 * Lighthouse throttles relative to the host, and its throttling guide asks for
 * this calibration. One CI runner type read from 844 to 2,691, and at half
 * speed the machine itself was 90% idle, so the cause is outside it. At a
 * constant 4x, a page that scores 100 at full speed read 78 at half speed
 * (#274). A runner at full speed keeps about 4x.
 */
export function cpuSlowdown(benchmarkIndex: number): number {
  return Math.max(1, (CPU_SLOWDOWN * benchmarkIndex) / FULL_SPEED_BENCHMARK);
}

/**
 * Why a run measured nothing, or null if it measured every category. Such a
 * run has no score, which is not a score of 0: `NO_NAVSTART`, a trace with no
 * navigation in it, took about one run in twenty-five in CI on pages that
 * score 100.
 */
export function unmeasured(lhr: {
  runtimeError?: { code?: string } | undefined;
  categories: Record<string, { score: number | null } | undefined>;
}): string | null {
  if (lhr.runtimeError) return lhr.runtimeError.code ?? "a runtime error";
  const found = new Map(Object.entries(lhr.categories));
  const missing = CATEGORIES.filter((category) => typeof found.get(category)?.score !== "number");
  return missing.length > 0 ? `no score for ${missing.join(", ")}` : null;
}

/**
 * Whether a run's long tasks include one Lighthouse attributes to no script
 * and longer than 300 ms. In Phase 5 Step 6 a shared Chrome showed one in most
 * CI runs: V8 walking a reused renderer's heap as the page loaded, a cost of
 * the measurement, which is why each run now has a Chrome of its own. The
 * reports keep such a run's trace (`<report>.trace.json.gz`) to say what it is.
 */
export function unattributed(details: unknown): boolean {
  const items = (details as { items?: { url?: string; duration?: number }[] } | undefined)?.items ?? [];
  return items.some((item) => item.url === "Unattributable" && (item.duration ?? 0) > 300);
}

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

/**
 * One Lighthouse run in a Chrome of its own, as the Lighthouse command line
 * runs: a shared Chrome puts every run of the origin in one renderer process,
 * whose heap the next run pays for.
 */
async function measure(url: string, slowdown: number): Promise<RunnerResult> {
  const chrome = await chromeLauncher.launch({
    chromePath: chromium.executablePath(),
    chromeFlags: ["--headless=new", "--no-sandbox"],
  });
  try {
    const result = await lighthouse(url, {
      port: chrome.port,
      output: "json",
      logLevel: "error",
      onlyCategories: [...CATEGORIES],
      throttling: { cpuSlowdownMultiplier: slowdown },
    });
    if (!result) throw new Error(`Lighthouse returned nothing for ${url}`);
    return result;
  } finally {
    chrome.kill();
  }
}

/** One run that measured every category, however many attempts that took. */
async function measured(url: string, slowdown: number): Promise<RunnerResult> {
  let reason = "";
  for (let attempt = 1; attempt <= ATTEMPTS; attempt += 1) {
    const result = await measure(url, slowdown);
    const problem = unmeasured(result.lhr);
    if (problem === null) return result;
    reason = problem;
    process.stdout.write(`lighthouse ${url}: attempt ${attempt} measured nothing (${problem})\n`);
  }
  throw new Error(`Lighthouse measured nothing for ${url} in ${ATTEMPTS} attempts: ${reason}`);
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
  const failures: string[] = [];
  let traces = 0;
  try {
    // One uncounted run first: a fresh runner's first Chrome loads its binary
    // and builds its font caches, which slowed the first page's runs in CI.
    let benchmark = (await measure(`${ORIGIN}${pages[0] ?? "/"}`, CPU_SLOWDOWN)).lhr.environment.benchmarkIndex;
    for (const path of pages) {
      const scores = new Map<string, number[]>(CATEGORIES.map((category) => [category, []]));
      for (let run = 1; run <= RUNS; run += 1) {
        const result = await measured(`${ORIGIN}${path}`, cpuSlowdown(benchmark));
        benchmark = result.lhr.environment.benchmarkIndex;
        const name = `${path.replaceAll("/", "_") || "_"}run${run}.json`;
        // A name built from a fixed sample path, under .lighthouse/.
        // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
        writeFileSync(join(reports, name), String(result.report));
        if (traces < MAX_TRACES && unattributed(result.lhr.audits["long-tasks"]?.details)) {
          traces += 1;
          // The same fixed name, with the trace that shows what the task was.
          // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
          writeFileSync(join(reports, `${name}.trace.json.gz`), gzipSync(JSON.stringify(result.artifacts.Trace)));
        }
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
      process.stdout.write(`lighthouse ${path}: ${line} (median of ${RUNS} mobile runs; benchmark ${Math.round(benchmark)})\n`);
    }
  } finally {
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
