// web/tests/e2e/support.ts
// What every end-to-end test shares: the pages the build wrote, read from
// dist/, and a fixture that records every Content Security Policy violation
// and console error a page raises. The listener is installed through the
// DevTools protocol before any page script runs, which the policy cannot
// block, and a test fails if anything was recorded. The `api` fixture sends a
// page's /v1/ requests and GET /version, which `wrangler dev`'s edge Worker
// cannot forward (it has no origin), to the local API on API_PORT
// (tests/web/e2e_api.py) and hands the page its answer unchanged, so the
// browser still sees one origin. The `network` fixture records every request
// the page makes, to any origin, with its body (the privacy test's log).
// `useColorScheme` switches a loaded page's colour scheme for axe and waits
// for the CSS transitions the switch starts.
import { readFileSync, readdirSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

import { test as base, expect, type Page } from "@playwright/test";

export const DIST = fileURLToPath(new URL("../../dist/", import.meta.url));

/** The port of the API the calculators' requests are forwarded to. */
export const API_PORT = 8799;
const API_ORIGIN = `http://127.0.0.1:${String(API_PORT)}`;

/** The policy dist/_headers sends on every path. */
export function headerPolicy(): string {
  const line = readFileSync(join(DIST, "_headers"), "utf8")
    .split("\n")
    .find((text) => text.trimStart().startsWith("Content-Security-Policy:"));
  if (!line) throw new Error("dist/_headers has no Content-Security-Policy; run `npm run build`");
  return line.split(": ").slice(1).join(": ").trim();
}

function walk(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? walk(path) : [relative(DIST, path).split(sep).join("/")];
  });
}

/** Every page the build wrote, as the path a visitor asks for. */
export function pages(): string[] {
  return walk(DIST)
    .filter((file) => file.endsWith("index.html"))
    .map((file) => `/${file.slice(0, -"index.html".length)}`)
    .sort();
}

/** A violation the page reported, as the browser describes it. */
export interface Violation {
  directive: string;
  blocked: string;
  sample: string;
}

interface Watch {
  violations: Violation[];
  errors: string[];
}

/** The API requests a page made, as the forwarding fixture saw them. */
export interface ApiLog {
  requests: { method: string; url: string; contentType: string | null; body: string | null }[];
}

/** Every request a page made, to any origin, as the browser sent it. */
export interface NetworkLog {
  requests: { method: string; url: string; body: Buffer | null }[];
}

export const test = base.extend<{ watch: Watch; api: ApiLog; network: NetworkLog }>({
  network: async ({ page }, use) => {
    const log: NetworkLog = { requests: [] };
    page.on("request", (request) => {
      log.requests.push({ method: request.method(), url: request.url(), body: request.postDataBuffer() });
    });
    await use(log);
  },
  api: async ({ page }, use) => {
    const log: ApiLog = { requests: [] };
    // The data explorer asks the server's mode (GET /version), which wrangler
    // dev cannot answer either; it is forwarded, and not logged as a run.
    await page.route(
      (url) => url.pathname === "/version",
      async (route) => {
        const response = await route.fetch({ url: `${API_ORIGIN}/version` });
        await route.fulfill({ response });
      },
    );
    await page.route("**/v1/**", async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      log.requests.push({
        method: request.method(),
        url: `${url.pathname}${url.search}`,
        contentType: request.headers()["content-type"] ?? null,
        body: request.postData(),
      });
      const response = await route.fetch({ url: `${API_ORIGIN}${url.pathname}${url.search}` });
      await route.fulfill({ response });
    });
    await use(log);
  },
  watch: [
    async ({ page }, use) => {
      const watch: Watch = { violations: [], errors: [] };
      await page.exposeFunction("__reportViolation", (violation: Violation) => {
        watch.violations.push(violation);
      });
      await page.addInitScript(() => {
        document.addEventListener("securitypolicyviolation", (event) => {
          const report = (window as unknown as { __reportViolation: (v: unknown) => void })
            .__reportViolation;
          report({
            directive: event.effectiveDirective,
            blocked: event.blockedURI,
            sample: event.sample,
          });
        });
      });
      page.on("console", (message) => {
        if (message.type() === "error") watch.errors.push(message.text());
      });
      page.on("pageerror", (error) => watch.errors.push(error.message));
      await use(watch);
    },
    { auto: true },
  ],
});

/**
 * Switch a loaded page to a colour scheme and wait until every CSS transition
 * the switch started has finished. A button's `transition-all` otherwise shows
 * axe a colour half-way between the two schemes on a slow runner: the footer's
 * sign-up button failed color-contrast that way in CI, in light and in dark
 * (PR #318). Only transitions are awaited: a looping animation never finishes.
 */
export async function useColorScheme(page: Page, colorScheme: "light" | "dark"): Promise<void> {
  await page.emulateMedia({ colorScheme });
  await page.evaluate(() =>
    Promise.all(
      document
        .getAnimations()
        .filter((animation) => animation instanceof CSSTransition)
        .map((animation) => animation.finished),
    ),
  );
}

export { expect };
