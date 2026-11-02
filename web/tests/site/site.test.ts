// web/tests/site/site.test.ts
// The built site (dist/, after `npm run build`): one page per registered model
// at its decision-2 URL with every required section and its formulas as
// MathML; one page per row of the error table; a canonical link, Open Graph
// tags, a 1200x630 social image and parseable schema.org JSON-LD on every
// page; every internal link resolving; no markup from card text; and the
// sitemap and robots.txt naming every page.
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { attributes, startTags } from "../../scripts/headers.ts";
import { ORIGIN, modelPath } from "@/lib/paths";
import { ogImagePath } from "@/lib/pages";
import { problemData, registryData } from "@/lib/site-data";

const DIST = fileURLToPath(new URL("../../dist/", import.meta.url));

/**
 * Internal links to pages a later step builds, each with that step. Step 16
 * writes the legal pages and /sources/, and removes its rows here.
 */
const PLANNED: ReadonlyMap<string, string> = new Map([
  ["/legal/disclaimers/", "Phase 5 Step 16"],
  ["/sources/", "Phase 5 Step 16"],
]);

/** The model page sections, in order; `data` only for a model with bindings. */
const SECTIONS = [
  "summary",
  "formula",
  "variables",
  "worked-example",
  "assumptions",
  "limitations",
  "evidence",
  "data",
  "citations",
  "changelog",
  "use-it-elsewhere",
];

function walk(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? walk(path) : [relative(DIST, path).split(sep).join("/")];
  });
}

const FILES = existsSync(DIST) ? walk(DIST) : [];
const PAGES = FILES.filter((file) => file.endsWith("index.html")).map(
  (file) => `/${file.slice(0, -"index.html".length)}`,
);

function html(path: string): string {
  return readFileSync(join(DIST, path, "index.html"), "utf8");
}

/** Each start tag of a page, the JSON-LD block's text left out. */
function tags(page: string): string[] {
  return startTags(page.replace(/<!--[\s\S]*?-->/g, "").replace(/(<script[^>]*>)[\s\S]*?<\/script>/g, "$1"));
}

function meta(page: string, key: string): string | undefined {
  for (const tag of tags(page)) {
    const found = attributes(tag);
    if (tag.startsWith("<meta") && (found.get("property") === key || found.get("name") === key)) {
      return found.get("content");
    }
  }
  return undefined;
}

function jsonLd(page: string): Record<string, unknown>[] {
  return [...page.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map(
    (match) => JSON.parse(match[1] ?? "") as Record<string, unknown>,
  );
}

/** Whether a same-origin path answers: a file, a page, or the 404 page's file. */
function resolves(path: string): boolean {
  const clean = decodeURI(path.split("#")[0]?.split("?")[0] ?? "");
  if (clean === "") return true;
  const file = clean.replace(/^\//, "");
  if (FILES.includes(file)) return true;
  return FILES.includes(`${file.replace(/\/?$/, "/")}index.html`.replace(/^\//, ""));
}

describe("the build", () => {
  it("exists: run `npm run build` first", () => {
    expect(FILES.length, "dist/ is empty").toBeGreaterThan(0);
  });

  it("writes one page per registered model at its decision-2 URL", () => {
    const models = PAGES.filter((path) => /^\/models\/[^/]+\/[^/]+\/$/.test(path));
    expect(models.length).toBe(registryData.models.length);
    expect(models.sort()).toEqual(registryData.models.map((model) => modelPath(model.id)).sort());
  });

  it("writes one page per row of the error table", () => {
    const problems = PAGES.filter((path) => /^\/problems\/[^/]+\/$/.test(path)).map((path) => path.split("/")[2]);
    expect(problems.sort()).toEqual(problemData.map((problem) => problem.slug).sort());
  });

  it("writes the models index, every domain index and the problems index", () => {
    const domains = new Set(registryData.models.map((model) => model.domain.replaceAll("_", "-")));
    for (const path of ["/", "/models/", "/problems/", ...[...domains].map((d) => `/models/${d}/`)]) {
      expect(PAGES, path).toContain(path);
    }
  });
});

describe("every model page", () => {
  for (const model of registryData.models) {
    it(`${model.id} has every section, in order, and its formulas as MathML`, () => {
      const page = html(modelPath(model.id));
      const sections = [...page.matchAll(/data-section="([a-z-]+)"/g)].map((match) => match[1]);
      const bound = Array.isArray(model.bindings) && model.bindings.length > 0;
      expect(sections).toEqual(SECTIONS.filter((section) => bound || section !== "data"));
      const formulas = page.match(/<span class="katex"><math xmlns="http:\/\/www\.w3\.org\/1998\/Math\/MathML" display="block">/g) ?? [];
      expect(formulas.length).toBe(model.formula.length);
      expect(page).not.toMatch(/katex-error|ParseError|katex-html/);
    });
  }
});

describe("every page", () => {
  it("has a canonical link, Open Graph and Twitter tags, and a social image", () => {
    for (const path of PAGES) {
      const page = html(path);
      const canonical = tags(page)
        .filter((tag) => tag.startsWith("<link") && attributes(tag).get("rel") === "canonical")
        .map((tag) => attributes(tag).get("href"));
      expect(canonical, path).toEqual([`${ORIGIN}${path}`]);
      expect(meta(page, "og:url"), path).toBe(`${ORIGIN}${path}`);
      expect(meta(page, "og:title"), path).toBeTruthy();
      expect(meta(page, "og:description"), path).toBeTruthy();
      expect(meta(page, "twitter:card"), path).toBe("summary_large_image");
      const image = meta(page, "og:image");
      expect(image, path).toBe(`${ORIGIN}${ogImagePath(path)}`);
      expect(meta(page, "twitter:image"), path).toBe(image);
      const png = readFileSync(join(DIST, ogImagePath(path)));
      expect(png.subarray(1, 4).toString("ascii"), path).toBe("PNG");
      expect([png.readUInt32BE(16), png.readUInt32BE(20)], path).toEqual([1200, 630]);
    }
  });

  it("carries JSON-LD that parses: a free WebPage with a BreadcrumbList", () => {
    for (const path of PAGES.filter((p) => p !== "/")) {
      const [block, ...rest] = jsonLd(html(path));
      expect(rest, path).toEqual([]);
      expect(block?.["@context"], path).toBe("https://schema.org");
      expect(block?.["@type"], path).toBe("WebPage");
      expect(block?.url, path).toBe(`${ORIGIN}${path}`);
      expect(block?.isAccessibleForFree, path).toBe(true);
      const crumbs = (block?.breadcrumb as { itemListElement: { item: string }[] }).itemListElement;
      expect(crumbs.at(-1)?.item, path).toBe(`${ORIGIN}${path}`);
    }
    for (const model of registryData.models) {
      const [block] = jsonLd(html(modelPath(model.id)));
      expect((block?.about as { identifier: string }).identifier).toBe(model.id);
      expect((block?.citation as unknown[]).length).toBe((model.references as unknown[]).length);
    }
  });

  it("links only to paths that resolve, or to a page a later step builds", () => {
    const broken: string[] = [];
    for (const path of PAGES) {
      for (const tag of tags(html(path))) {
        const found = attributes(tag);
        for (const name of ["href", "src"]) {
          const value = found.get(name);
          if (!value?.startsWith("/") || value.startsWith("//")) continue;
          if (!resolves(value) && !PLANNED.has(value)) broken.push(`${path} -> ${value}`);
        }
      }
    }
    expect(broken).toEqual([]);
    for (const planned of PLANNED.keys()) expect(resolves(planned), `${planned} now builds: remove it from PLANNED`).toBe(false);
  });

  it("holds no markup from card text: no script but its JSON-LD, no handler, style or frame", () => {
    for (const path of [...PAGES, "/404.html"]) {
      const page = path.endsWith(".html") ? readFileSync(join(DIST, path), "utf8") : html(path);
      for (const tag of tags(page)) {
        const name = /^<([a-zA-Z][a-zA-Z0-9-]*)/.exec(tag)?.[1]?.toLowerCase() ?? "";
        expect(["iframe", "object", "embed", "style", "form", "base"], `${path}: ${tag}`).not.toContain(name);
        if (name === "script") expect(attributes(tag).get("type"), `${path}: ${tag}`).toBe("application/ld+json");
        if (name === "img") expect(attributes(tag).get("src"), `${path}: ${tag}`).toBe("/favicon.svg");
        for (const attribute of attributes(tag).keys()) {
          expect(attribute, `${path}: ${tag}`).not.toMatch(/^on|^style$|^srcdoc$/);
        }
      }
    }
  });

  it("keeps the 404 page out of the index", () => {
    const page = readFileSync(join(DIST, "404.html"), "utf8");
    expect(meta(page, "robots")).toBe("noindex");
    expect(page).not.toContain('rel="canonical"');
  });
});

describe("indexing", () => {
  it("lists every page in the sitemap on the production origin", () => {
    expect(readFileSync(join(DIST, "sitemap-index.xml"), "utf8")).toContain(`<loc>${ORIGIN}/sitemap-0.xml</loc>`);
    const listed = FILES.filter((file) => /^sitemap-\d+\.xml$/.test(file)).flatMap((file) =>
      [...readFileSync(join(DIST, file), "utf8").matchAll(/<loc>([^<]*)<\/loc>/g)].map((match) => match[1]),
    );
    expect(listed.sort()).toEqual(PAGES.map((path) => `${ORIGIN}${path}`).sort());
  });

  it("writes robots.txt naming the sitemap, and _redirects", () => {
    const robots = readFileSync(join(DIST, "robots.txt"), "utf8");
    expect(robots).toMatch(/^User-agent: \*\n(Allow|Disallow): \/\n/);
    expect(robots).toContain(`Sitemap: ${ORIGIN}/sitemap-index.xml`);
    expect(FILES).toContain("_redirects");
  });
});
