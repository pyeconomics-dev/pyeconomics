// web/tests/unit/build-tools.test.ts
// The build's own tools: the bundle recorder (scripts/shipped-packages.ts)
// names the npm package of every bundled module, and the Lighthouse runner
// (scripts/lighthouse.ts) takes the median of its runs over the sample pages
// the build wrote.
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { CATEGORIES, SAMPLE, built, median, schedule, unattributed } from "../../scripts/lighthouse.ts";
import { packageOf, packagesOf } from "../../scripts/shipped-packages.ts";

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

  it("runs the sample in rounds, so a page's runs are spread over the whole measurement", () => {
    expect(schedule(["/", "/a/"], 3).map(({ path, run }) => `${path}${String(run)}`)).toEqual([
      "/1",
      "/a/1",
      "/2",
      "/a/2",
      "/3",
      "/a/3",
    ]);
  });

  it("measures decision 19's thirteen pages in all four categories", () => {
    expect(SAMPLE).toHaveLength(13);
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
