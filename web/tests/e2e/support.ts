// web/tests/e2e/support.ts
// What every end-to-end test shares: the pages the build wrote, read from
// dist/, and a fixture that records every Content Security Policy violation
// and console error a page raises. The listener is installed through the
// DevTools protocol before any page script runs, which the policy cannot
// block, and a test fails if anything was recorded.
import { readFileSync, readdirSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

import { test as base, expect } from "@playwright/test";

export const DIST = fileURLToPath(new URL("../../dist/", import.meta.url));

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

export const test = base.extend<{ watch: Watch }>({
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

export { expect };
