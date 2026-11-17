// web/tests/unit/build-tools.test.ts
// The build's own tools: the bundle recorder (scripts/shipped-packages.ts)
// names the npm package of every bundled module, and the Lighthouse runner
// (scripts/lighthouse.ts) takes the median of its runs over the sample pages
// the build wrote.
import { mkdirSync, mkdtempSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { CATEGORIES, SAMPLE, built, cpuSlowdown, median, unattributed, unmeasured } from "../../scripts/lighthouse.ts";
import { packageOf, packagesOf } from "../../scripts/shipped-packages.ts";
import { SAMPLE as VISUAL_SAMPLE, baselineNames } from "../visual/sample.ts";

describe("packageOf", () => {
  it.each([
    ["/w/node_modules/react-dom/cjs/react-dom.production.js", "react-dom"],
    ["C:\\w\\node_modules\\@astrojs\\react\\dist\\client.js", "@astrojs/react"],
    ["/w/node_modules/a/node_modules/@scope/b/index.js?commonjs-proxy", "@scope/b"],
    ["\0/w/node_modules/scheduler/index.js", "scheduler"],
  ])("names the package of %s", (id, name) => {
    expect(packageOf(id)).toBe(name);
  });

  it("names nothing for the site's own modules or a virtual one", () => {
    expect(packageOf("/w/web/src/components/ui/button.tsx")).toBeNull();
    expect(packageOf("\0astro:renderers")).toBeNull();
  });

  it("lists each package once, sorted", () => {
    expect(
      packagesOf([
        "/w/node_modules/react/index.js",
        "/w/web/src/lib/utils.ts",
        "/w/node_modules/react/cjs/react.production.js",
        "/w/node_modules/@astrojs/react/dist/client.js",
      ]),
    ).toEqual(["@astrojs/react", "react"]);
  });
});

describe("the Lighthouse runner", () => {
  it("takes the median of three runs", () => {
    expect(median([0.91, 0.5, 1])).toBe(0.91);
    expect(() => median([])).toThrow(/no scores/);
  });

  it("keeps a trace only for a run with a long task no script accounts for", () => {
    expect(unattributed({ items: [{ url: "Unattributable", duration: 600 }] })).toBe(true);
    expect(unattributed({ items: [{ url: "Unattributable", duration: 120 }] })).toBe(false);
    expect(unattributed({ items: [{ url: "http://127.0.0.1:8788/", duration: 600 }] })).toBe(false);
    expect(unattributed(undefined)).toBe(false);
  });

  it("slows the CPU in step with the host, so the simulated phone stays the same", () => {
    expect(cpuSlowdown(2000)).toBe(4);
    expect(cpuSlowdown(1000)).toBe(2);
    expect(cpuSlowdown(2500)).toBe(5);
    expect(cpuSlowdown(100)).toBe(1);
  });

  it("tells a run that measured nothing from a low score", () => {
    const scored = Object.fromEntries(CATEGORIES.map((category) => [category, { score: 0.1 }]));
    expect(unmeasured({ categories: scored })).toBeNull();
    expect(unmeasured({ categories: { ...scored, performance: { score: 0 } } })).toBeNull();
    expect(unmeasured({ categories: scored, runtimeError: { code: "NO_NAVSTART" } })).toBe("NO_NAVSTART");
    expect(unmeasured({ categories: { ...scored, performance: { score: null } } })).toBe("no score for performance");
    expect(unmeasured({ categories: {} })).toMatch(/^no score for performance, accessibility/);
  });

  it("measures decision 19's thirteen pages and Step 15's two in all four categories", () => {
    expect(SAMPLE).toHaveLength(15);
    expect(SAMPLE.slice(-2)).toEqual(["/pro/", "/newsletter/"]);
    expect(SAMPLE[0]).toBe("/");
    expect(CATEGORIES).toEqual(["performance", "accessibility", "best-practices", "seo"]);
  });

  it("skips the sample pages the build has not written yet", () => {
    const dist = mkdtempSync(join(tmpdir(), "pyeconomics-lighthouse-"));
    writeFileSync(join(dist, "index.html"), "<!doctype html>");
    mkdirSync(join(dist, "data"));
    writeFileSync(join(dist, "data", "index.html"), "<!doctype html>");
    expect(built(dist)).toEqual(["/", "/data/"]);
  });
});

// Phase 5 Step 18: round 0 of the dogfooding protocol found a copy that failed
// without a word. One control copies (CopyButton.tsx), it says what happened,
// and tests/e2e/copy.spec.ts refuses the clipboard on every one in a page; so
// nothing else under src/ may write to the clipboard and skip that check.
describe("the clipboard", () => {
  const SOURCE = fileURLToPath(new URL("../../src/", import.meta.url));
  const files = (directory: string): string[] =>
    readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
      const path = join(directory, entry.name);
      return entry.isDirectory() ? files(path) : [path];
    });

  it("is written to only by the one copy control", () => {
    const writers = files(SOURCE)
      .filter((path) => /\.(?:astro|ts|tsx)$/.test(path))
      .filter((path) => /navigator\s*\.\s*clipboard|execCommand\(\s*["']copy/.test(readFileSync(path, "utf8")))
      .map((path) => path.slice(SOURCE.length).split("\\").join("/"));
    expect(writers).toEqual(["components/calculator/CopyButton.tsx"]);
  });
});

// Phase 5 Step 18's round 2: a control that is off until its island loads is
// drawn at half strength, and a transition on every property made it fade back
// in over 150 milliseconds once it was on. axe, reading the page in that
// moment, saw an enabled button at a contrast of 2.6. No control's opacity
// transitions, so one is either off or fully drawn.
describe("a control leaving its disabled state", () => {
  const SOURCE = fileURLToPath(new URL("../../src/", import.meta.url));
  const files = (directory: string): string[] =>
    readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
      const path = join(directory, entry.name);
      return entry.isDirectory() ? files(path) : [path];
    });

  it("does not fade: nothing transitions every property or its opacity beside a disabled look", () => {
    const fading = files(SOURCE)
      .filter((path) => /\.(?:astro|ts|tsx)$/.test(path))
      .filter((path) => {
        const text = readFileSync(path, "utf8");
        return /disabled:opacity-/.test(text) && /\btransition-all\b|\btransition-opacity\b|\btransition(?=[\s"'`])/.test(text);
      })
      .map((path) => path.slice(SOURCE.length).split("\\").join("/"));
    expect(fading).toEqual([]);
  });
});

// Phase 5 Step 18: the visual baselines photograph decision 19's sample, the
// pages Lighthouse measures before the two Step 15 added.
describe("the visual baselines' sample", () => {
  it("is decision 19's thirteen pages, each at two widths in both themes", () => {
    const added = new Set(["/pro/", "/newsletter/"]);
    expect(VISUAL_SAMPLE.map((page) => page.path)).toEqual(SAMPLE.filter((path) => !added.has(path)));
    expect(VISUAL_SAMPLE).toHaveLength(13);
    const names = baselineNames();
    expect(names).toHaveLength(52);
    expect(new Set(names).size).toBe(52);
    expect(names).toContain("home-390-light.png");
    expect(names).toContain("problem-1440-dark.png");
  });
});
