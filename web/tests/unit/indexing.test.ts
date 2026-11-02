// web/tests/unit/indexing.test.ts
// The post-build indexing step (scripts/indexing.ts) for both kinds of build:
// one that may be indexed (a local build, a final release's production build)
// allows every path, and one that must not be (staging, a pre-release's
// production build) refuses every path; both name the sitemap. Alias pages
// redirect to their model's page, a released page that neither builds nor
// redirects fails, and so does a page missing from the sitemap.
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";

import { describe, expect, it } from "vitest";

import { indexable, renderHeaders, headerPolicy } from "../../scripts/headers.ts";
import {
  SITEMAP,
  aliasRedirects,
  builtPages,
  checkIndexing,
  missingReleased,
  parseLedger,
  renderRedirects,
  robotsTxt,
  sitemapPaths,
} from "../../scripts/indexing.ts";

const MODELS = [
  { id: "fixed_income.bond_pricing", aliases: [{ id: "fixed_income.bond_price" }] },
  { id: "macro.policy_rule", aliases: [] },
];

function sitemap(paths: string[]): string {
  return `<urlset>${paths.map((path) => `<url><loc>https://pyeconomics.dev${path}</loc></url>`).join("")}</urlset>`;
}

function build(files: Record<string, string>): string {
  const root = mkdtempSync(join(tmpdir(), "pyeconomics-indexing-"));
  for (const [path, text] of Object.entries(files)) {
    mkdirSync(dirname(join(root, path)), { recursive: true });
    writeFileSync(join(root, path), text);
  }
  return root;
}

const PAGES = ["/", "/models/", "/models/fixed-income/bond-pricing/"];
const SITE = {
  "index.html": "",
  "models/index.html": "",
  "models/fixed-income/bond-pricing/index.html": "",
  "404.html": "",
  "sitemap-index.xml": "<sitemapindex/>",
  "sitemap-0.xml": sitemap(PAGES),
};
const EMPTY = { format: 1 as const, pages: [] };

describe("robots.txt", () => {
  it.each([
    ["a local build", indexable("local", "1.0.0rc1.dev1"), "Allow: /"],
    ["a final release's production build", indexable("production", "1.0.0"), "Allow: /"],
    ["a staging build", indexable("staging", "1.0.0"), "Disallow: /"],
    ["a pre-release's production build", indexable("production", "1.0.0rc1"), "Disallow: /"],
  ])("for %s says %s and names the sitemap", (_name, index, rule) => {
    const text = robotsTxt(index);
    expect(text).toBe(`User-agent: *\n${rule}\n\nSitemap: ${SITEMAP}\n`);
    expect(SITEMAP).toBe("https://pyeconomics.dev/sitemap-index.xml");
    expect(renderHeaders(headerPolicy(new Map()), index).includes("X-Robots-Tag: noindex")).toBe(!index);
  });
});

describe("aliasRedirects", () => {
  it("sends an alias's page, with and without its slash, to its model's page", () => {
    const redirects = aliasRedirects(MODELS);
    expect(redirects).toEqual([
      { from: "/models/fixed-income/bond-price", to: "/models/fixed-income/bond-pricing/" },
      { from: "/models/fixed-income/bond-price/", to: "/models/fixed-income/bond-pricing/" },
    ]);
    expect(renderRedirects(redirects)).toBe(
      "/models/fixed-income/bond-price /models/fixed-income/bond-pricing/ 301\n" +
        "/models/fixed-income/bond-price/ /models/fixed-income/bond-pricing/ 301\n",
    );
    expect(renderRedirects(aliasRedirects([{ id: "macro.policy_rule", aliases: [] }]))).toBe("");
  });

  it("refuses an alias that is a model's page or names two models", () => {
    expect(() => aliasRedirects([...MODELS, { id: "macro.taylor", aliases: [{ id: "macro.policy_rule" }] }])).toThrow(
      /is a model's page/,
    );
    expect(() =>
      aliasRedirects([...MODELS, { id: "fixed_income.price", aliases: [{ id: "fixed_income.bond_price" }] }]),
    ).toThrow(/names both/);
  });
});

describe("the released-page ledger", () => {
  it("reads a sorted list of page paths", () => {
    expect(parseLedger('{"format": 1, "pages": ["/", "/models/"]}').pages).toEqual(["/", "/models/"]);
    expect(() => parseLedger('{"pages": []}')).toThrow(/format/);
    expect(() => parseLedger('{"format": 1, "pages": ["/models"]}')).toThrow(/trailing slash/);
    expect(() => parseLedger('{"format": 1, "pages": ["/models/", "/"]}')).toThrow(/sorted/);
    expect(() => parseLedger('{"format": 1, "pages": ["/", "/"]}')).toThrow(/once/);
  });

  it("fails on a released page that neither builds nor redirects", () => {
    const ledger = { format: 1 as const, pages: ["/models/fixed-income/bond-price/", "/models/gone/", "/"] };
    expect(missingReleased(ledger, PAGES, aliasRedirects(MODELS))).toEqual(["/models/gone/"]);
    const report = checkIndexing(build(SITE), { index: true, models: MODELS, ledger });
    expect(report.problems).toEqual([
      "/models/gone/ is in released-pages.json but neither builds nor redirects: a shipped page never disappears",
    ]);
  });

  it("holds web/released-pages.json to its shape", async () => {
    const { readFileSync } = await import("node:fs");
    const text = readFileSync(new URL("../../released-pages.json", import.meta.url), "utf8");
    expect(parseLedger(text).format).toBe(1);
  });
});

describe("checkIndexing", () => {
  it("writes robots.txt and _redirects for a build whose pages the sitemap lists", () => {
    const report = checkIndexing(build(SITE), { index: false, models: MODELS, ledger: EMPTY });
    expect(report.problems).toEqual([]);
    expect(report.files["robots.txt"]).toContain("Disallow: /");
    expect(report.files._redirects).toContain(" 301\n");
  });

  it("fails on a page the sitemap misses, an entry off the origin and no sitemap at all", () => {
    const partial = { ...SITE, "sitemap-0.xml": `${sitemap(PAGES.slice(1))}<loc>https://example.org/x/</loc>` };
    expect(checkIndexing(build(partial), { index: true, models: MODELS, ledger: EMPTY }).problems).toEqual([
      "sitemap-0.xml lists https://example.org/x/, off https://pyeconomics.dev",
      "the sitemap does not list /",
    ]);
    const none = Object.fromEntries(Object.entries(SITE).filter(([name]) => name !== "sitemap-0.xml"));
    expect(checkIndexing(build(none), { index: true, models: MODELS, ledger: EMPTY }).problems).toEqual([
      "the build wrote no sitemap",
    ]);
  });

  it("refuses robots.txt or _redirects copied from public/", () => {
    const copied = { ...SITE, "robots.txt": "", _redirects: "" };
    expect(checkIndexing(build(copied), { index: true, models: MODELS, ledger: EMPTY }).problems).toEqual([
      "dist/robots.txt already exists: it comes from scripts/indexing.ts, never public/",
      "dist/_redirects already exists: it comes from scripts/indexing.ts, never public/",
    ]);
  });

  it("names a bad alias instead of writing redirects", () => {
    const models = [...MODELS, { id: "macro.taylor", aliases: [{ id: "macro.policy_rule" }] }];
    expect(checkIndexing(build(SITE), { index: true, models, ledger: EMPTY }).problems).toEqual([
      "alias macro.policy_rule of macro.taylor is a model's page",
    ]);
  });

  it("lists built pages and reads sitemap paths", () => {
    expect(builtPages(["index.html", "a/index.html", "404.html", "og/index.png"])).toEqual(["/", "/a/"]);
    expect(sitemapPaths(sitemap(["/", "/a/"]))).toEqual({ paths: ["/", "/a/"], foreign: [] });
  });
});
