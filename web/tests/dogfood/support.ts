// web/tests/dogfood/support.ts
// What the dogfooding harness's captures, tasks and `visit` tool share: where
// the site is, how a page is prepared, what a capture records and where it is
// written. The site is the local build by default (`wrangler dev` on 8788,
// with the API of tests/web/e2e_api.py on 8799, to which a page's /v1/
// requests and GET /version are forwarded as the end-to-end tests forward
// them), or a deployed site named by DOGFOOD_BASE_URL. Behind Cloudflare
// Access the service token is read from CF_ACCESS_CLIENT_ID and
// CF_ACCESS_CLIENT_SECRET and sent only as request headers, and only to the
// site's own origin (`prepare` adds them per request): a production build
// talks to the analytics collector and the error tracker, which must never see
// it (Phase 5 Step 20). Nothing here prints, logs or writes it, and a record
// holds no request header at all. On a deployed site the analytics tracker is
// switched off before any page script runs, so a round adds nothing to the
// Gate G2 counts. Output goes to the git-ignored web/dogfood-out/<run>/.
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import type { Locator, Page } from "@playwright/test";

import { MAX_TILES } from "./pages.ts";

export const WEB = fileURLToPath(new URL("../../", import.meta.url));

/** The local build's address, and the API its pages' requests go to. */
export const LOCAL_ORIGIN = "http://127.0.0.1:8788";
/** The local API's port: 8799, or E2E_API_PORT where another program on the machine holds it. */
export const API_PORT = Number(process.env.E2E_API_PORT ?? "8799");
export const API_ORIGIN = `http://127.0.0.1:${String(API_PORT)}`;

/** The site under test. */
export const BASE_URL = (process.env.DOGFOOD_BASE_URL ?? LOCAL_ORIGIN).replace(/\/$/, "");
export const LOCAL = BASE_URL === LOCAL_ORIGIN;

/** Chromium draws scrollbars as Windows does: no --hide-scrollbars (issue #319). */
export const LAUNCH = { ignoreDefaultArgs: ["--hide-scrollbars"] };

/** Cloudflare Access's headers for a deployed site, or none. Never printed. */
export function accessHeaders(): Record<string, string> {
  const id = process.env.CF_ACCESS_CLIENT_ID ?? "";
  const secret = process.env.CF_ACCESS_CLIENT_SECRET ?? "";
  if (LOCAL || id === "" || secret === "") return {};
  return { "CF-Access-Client-Id": id, "CF-Access-Client-Secret": secret };
}

/** This run's output directory, shared by every worker through the environment. */
export function runDirectory(): string {
  const run = process.env.DOGFOOD_RUN ?? "adhoc";
  if (!/^[\w.-]+$/.test(run)) throw new Error("DOGFOOD_RUN may hold letters, digits, '.', '_' and '-' only");
  return join(WEB, "dogfood-out", run);
}

/** Write a file under the run's directory, creating its folder. */
export function write(relativePath: string, data: string | Buffer): string {
  const path = join(runDirectory(), relativePath);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, data);
  return relativePath;
}

/** What a page raised while it was watched. */
export interface Watch {
  violations: { directive: string; blocked: string }[];
  errors: string[];
}

/**
 * Prepare a page before its first navigation: forward the API locally, and
 * record every Content Security Policy violation (through a listener the
 * policy cannot block) and console error. On a deployed site, add Access's
 * headers to the site's own requests alone, refuse and record a request to any
 * other origin, and switch the analytics tracker off (as tests/staging/support.ts
 * does for a deploy's checks).
 */
export async function prepare(page: Page): Promise<Watch> {
  const watch: Watch = { violations: [], errors: [] };
  if (!LOCAL) {
    const origin = new URL(BASE_URL).origin;
    const headers = accessHeaders();
    await page.route("**/*", async (route) => {
      const url = new URL(route.request().url());
      if (url.origin === origin) {
        await route.continue({ headers: { ...route.request().headers(), ...headers } });
      } else {
        watch.errors.push(`a request to another origin was refused: ${url.origin}`);
        await route.abort("blockedbyclient");
      }
    });
    await page.addInitScript(() => {
      try {
        window.localStorage.setItem("umami.disabled", "1");
      } catch {
        // Storage refused: the tracker's request is then refused above, and recorded.
      }
    });
  }
  if (LOCAL) {
    await page.route(
      (url) => url.pathname === "/version",
      async (route) => {
        const response = await route.fetch({ url: `${API_ORIGIN}/version` });
        await route.fulfill({ response });
      },
    );
    await page.route("**/v1/**", async (route) => {
      const url = new URL(route.request().url());
      const response = await route.fetch({ url: `${API_ORIGIN}${url.pathname}${url.search}` });
      await route.fulfill({ response });
    });
  }
  await page.exposeFunction("__dogfoodViolation", (violation: { directive: string; blocked: string }) => {
    watch.violations.push(violation);
  });
  await page.addInitScript(() => {
    document.addEventListener("securitypolicyviolation", (event) => {
      const report = (window as unknown as { __dogfoodViolation: (v: unknown) => void }).__dogfoodViolation;
      report({ directive: event.effectiveDirective, blocked: event.blockedURI });
    });
  });
  page.on("console", (message) => {
    if (message.type() === "error") watch.errors.push(message.text());
  });
  page.on("pageerror", (error) => watch.errors.push(error.message));
  return watch;
}

/**
 * Scroll through the page a screen at a time, so every island that hydrates
 * when visible does, then wait for the network to settle and return to the top.
 */
export async function scrollThrough(page: Page): Promise<void> {
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  const step = page.viewportSize()?.height ?? 800;
  for (let y = 0; y < height; y += step) {
    await page.evaluate((top) => window.scrollTo(0, top), y);
    await page.waitForTimeout(150);
  }
  await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => undefined);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
  await page.waitForTimeout(250);
}

/**
 * Choose a select's option as a visitor does: after a key press (Phase 5 Step
 * 18's round 2). Playwright sets a select's value from script, which the
 * browser does not count as input, so the change it causes (another example's
 * form is taller) was scored as an unexpected layout shift, 0.176 on the
 * duration page; a visitor's own choice never is, because the Layout
 * Instability API leaves out a shift within half a second of a key or a
 * pointer press.
 */
export async function choose(page: Page, picker: Locator, option: Parameters<Locator["selectOption"]>[0]): Promise<void> {
  await picker.focus();
  await page.keyboard.press("Shift");
  await picker.selectOption(option);
}

/**
 * Wait until every animation and transition that ends has ended, so a
 * screenshot shows a state a visitor sees, not a frame of the way there
 * (Phase 5 Step 18's round 1: the phone menu was captured mid-fade, once
 * half-transparent and once not at all). A looping animation is not waited
 * for, and the wait gives up after two seconds.
 *
 * Then wait until the page has stopped scrolling (the confirmation round on
 * staging): a control that takes focus is scrolled into view smoothly, over
 * about a second, and a picture taken on the way showed the part of the page
 * the browser had not painted yet as a blank strip, 360 pixels of a phone's
 * screen in five captures of six. The page is still when its scroll position
 * has not changed for five frames; this wait gives up after three seconds.
 */
export async function settled(page: Page): Promise<void> {
  await page
    .evaluate(
      () =>
        Promise.race([
          Promise.all(
            document
              .getAnimations()
              .filter((animation) => animation.effect?.getComputedTiming().iterations !== Infinity)
              .map((animation) => animation.finished.catch(() => undefined)),
          ),
          new Promise((resolve) => setTimeout(resolve, 2000)),
        ]).then(() => undefined),
    )
    .catch(() => undefined);
  await page
    .evaluate(
      () =>
        new Promise<void>((resolve) => {
          const deadline = performance.now() + 3000;
          let last = window.scrollY;
          let still = 0;
          const frame = (): void => {
            still = window.scrollY === last ? still + 1 : 0;
            last = window.scrollY;
            if (still >= 5 || performance.now() > deadline) resolve();
            else requestAnimationFrame(frame);
          };
          requestAnimationFrame(frame);
        }),
    )
    .catch(() => undefined);
}

/** Load timings, fonts and layout problems, read from the page. */
export interface Measures {
  timings: { ttfb: number; domContentLoaded: number; load: number; fcp: number | null; lcp: number | null; cls: number };
  transfer: { requests: number; bytes: number; scripts: number; fonts: string[] };
  overflowX: boolean;
  strayScroll: string[];
}

export async function measure(page: Page): Promise<Measures> {
  return page.evaluate(async () => {
    const navigation = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
    const fcp = performance.getEntriesByName("first-contentful-paint")[0]?.startTime ?? null;
    const buffered = (type: string) =>
      new Promise<PerformanceEntry[]>((resolve) => {
        const entries: PerformanceEntry[] = [];
        try {
          const observer = new PerformanceObserver((list) => entries.push(...list.getEntries()));
          observer.observe({ type, buffered: true });
          setTimeout(() => {
            observer.disconnect();
            resolve(entries);
          }, 100);
        } catch {
          resolve(entries);
        }
      });
    const lcp = (await buffered("largest-contentful-paint")).at(-1)?.startTime ?? null;
    const cls = (await buffered("layout-shift"))
      .map((entry) => entry as PerformanceEntry & { value: number; hadRecentInput: boolean })
      .filter((entry) => !entry.hadRecentInput)
      .reduce((sum, entry) => sum + entry.value, 0);
    const resources = performance.getEntriesByType("resource") as PerformanceResourceTiming[];
    const stray = [...document.querySelectorAll("body *")]
      .filter((element) => {
        const style = getComputedStyle(element);
        return (
          ["auto", "scroll"].includes(style.overflowY) &&
          style.maxHeight === "none" &&
          element.scrollHeight > element.clientHeight + 1
        );
      })
      .map((element) => `${element.tagName.toLowerCase()}.${[...element.classList].join(".")}`);
    const round = (value: number) => Math.round(value);
    return {
      timings: {
        ttfb: round(navigation?.responseStart ?? 0),
        domContentLoaded: round(navigation?.domContentLoadedEventEnd ?? 0),
        load: round(navigation?.loadEventEnd ?? 0),
        fcp: fcp === null ? null : round(fcp),
        lcp: lcp === null ? null : round(lcp),
        cls: Math.round(cls * 1000) / 1000,
      },
      transfer: {
        requests: resources.length + 1,
        bytes: resources.reduce((sum, entry) => sum + entry.transferSize, navigation?.transferSize ?? 0),
        scripts: resources.filter((entry) => entry.initiatorType === "script").length,
        fonts: resources.filter((entry) => /\.woff2?$/.test(new URL(entry.name).pathname)).map((entry) => new URL(entry.name).pathname),
      },
      overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      strayScroll: stray,
    };
  });
}

/** The first screen, the whole page and the page as viewport-high tiles. */
export async function screenshots(page: Page, stem: string): Promise<{ first: string; full: string; tiles: string[] }> {
  const size = page.viewportSize() ?? { width: 1440, height: 900 };
  const first = write(`${stem}.first.png`, await page.screenshot());
  const full = write(`${stem}.full.png`, await page.screenshot({ fullPage: true }));
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  const tiles: string[] = [];
  for (let index = 0; index * size.height < height && index < MAX_TILES; index += 1) {
    const y = index * size.height;
    const clip = { x: 0, y, width: size.width, height: Math.min(size.height, height - y) };
    tiles.push(write(`${stem}.tile-${String(index + 1).padStart(2, "0")}.png`, await page.screenshot({ fullPage: true, clip })));
  }
  return { first, full, tiles };
}

/** One capture's record, as index.json lists it. */
export interface CaptureRecord {
  kind: "page" | "task";
  id: string;
  path: string;
  label: string;
  viewport: string;
  theme: string;
  status: number | null;
  files: string[];
  measures: Measures | null;
  violations: Watch["violations"];
  errors: string[];
}

export function writeRecord(record: CaptureRecord): void {
  write(`records/${record.kind}-${record.id}-${record.viewport}-${record.theme}.json`, `${JSON.stringify(record, null, 2)}\n`);
}
