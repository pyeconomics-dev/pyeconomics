// web/tests/site/site.test.ts
// The built site (dist/, after `npm run build`): one page per registered model
// at its decision-2 URL with every required section and its formulas as
// MathML; one page per row of the error table; a canonical link, Open Graph
// tags, a 1200x630 social image and parseable schema.org JSON-LD on every
// page; every internal link resolving; no markup from card text; and the
// sitemap and robots.txt naming every page. Step 7's navigation: the header's
// fifteen domain sections and breadcrumbs on every page, the planned
// sections' empty states, the coverage matrix's counts held to the registry
// and the seed, the search index, no `cfa` in any of the site's URLs, and the
// CFA® mark used as an adjective with ® on first use. Step 9's data explorer:
// /data/ listing every concept, one page per concept with its sources, the
// models that read it and its explorer island, and the library-only notice
// on each model whose data the hosted site may not serve. Step 11: each model
// page's link to its documentation page. Step 15: the sign-up forms' action,
// method and fields, the Pro preview's disclosure and prices with no payment
// field, every click an element records on the analytics allowlist, and no
// tracker in a build that is not production's. Step 16's legal and trust
// pages: all six and security.txt built, each in every page's footer and
// marked for search; /sources/ listing every provider with its class and
// notices; FRED's notice only where /sources/ marks it local; the
// hypothetical-results legend on exactly the models the tags mark; the New
// York Fed's and the OECD's conditions passed through; the privacy policy
// holding every data flow and processor; the licence page every shipped
// package; and every open counsel question recorded in the counsel packet.
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { attributes, checkPage, startTags } from "../../scripts/headers.ts";
import { DOMAINS, ORIGIN, conceptPath, domainPath, modelPath } from "@/lib/paths";
import { dataProfiles, docsUrl, unservedSources } from "@/lib/models";
import { TRACKER_PATH } from "@/lib/analytics";
import { checkEvent } from "@/lib/events";
import { ogImagePath } from "@/lib/pages";
import { CFTC_STATEMENT, DATA_FLOWS, HYPOTHETICAL_LEGEND, LEGAL_INDEX, LEGAL_PAGES, simulates } from "@/lib/legal";
import { shippedLicences } from "@/lib/licences";
import { PRO_DISCLOSURE, PRO_TIERS } from "@/lib/pro";
import { parseModels } from "@/lib/registry-schema";
import { SECURITY_TXT_PATH, VULNERABILITY_REPORTING, parseSecurityTxt, securityTxtProblems } from "@/lib/security-txt";
import { PRIVACY_POLICY, SIGNUP_ACTION } from "@/lib/signup";
import { conceptData, problemData, registryData, sourceData, syllabusData } from "@/lib/site-data";

const DIST = fileURLToPath(new URL("../../dist/", import.meta.url));

/**
 * Internal links to pages a later step builds, each with that step, which
 * removes its row when the page exists. Empty since Step 16 built the legal
 * pages and /sources/.
 */
const PLANNED: ReadonlyMap<string, string> = new Map();

/** The model page sections, in order; `data` only for a model with bindings. */
const SECTIONS = [
  "summary",
  "formula",
  "variables",
  "calculator",
  "worked-example",
  "assumptions",
  "limitations",
  "evidence",
  "syllabus",
  "data",
  "citations",
  "changelog",
  "related",
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

  it("writes the models index, all fifteen domain pages, search, coverage and the problems index", () => {
    expect(DOMAINS).toHaveLength(15);
    for (const path of ["/", "/models/", "/search/", "/coverage/", "/problems/", ...DOMAINS.map((d) => domainPath(d.id))]) {
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

    it(`${model.id} carries one calculator island, hydrated when visible, and Plotly's style marker`, () => {
      const page = html(modelPath(model.id));
      const islands = tags(page).filter(
        (tag) => tag.startsWith("<astro-island") && /\/Calculator\./.test(attributes(tag).get("component-url") ?? ""),
      );
      expect(islands).toHaveLength(1);
      const island = attributes(islands[0] ?? "");
      expect(island.get("client")).toBe("visible");
      expect(island.get("component-url")).toMatch(/^\/_astro\/Calculator\.[\w-]+\.js$/);
      expect(island.get("props")).toContain(model.id);
      expect(page).toContain('<div id="plotly.js-style-global" class="no-inline-styles" hidden="">');
    });

    it(`${model.id} links its documentation page, which links it back`, () => {
      // The other half is tests/docs/test_cross_links.py.
      expect(html(modelPath(model.id))).toContain(`<a href="${docsUrl(model.id)}">`);
    });
  }
});

describe("the data explorer", () => {
  it("writes /data/ with every concept, and one page per concept at its conceptPath", () => {
    const index = html("/data/");
    for (const concept of conceptData) expect(index, concept.id).toContain(`data-concept="${concept.id}"`);
    const built = PAGES.filter((path) => path.startsWith("/data/") && path !== "/data/");
    expect(built.sort()).toEqual(conceptData.map((concept) => conceptPath(concept.id)).sort());
  });

  for (const concept of conceptData) {
    it(`${concept.id} lists its candidates and carries its explorer, hydrated when visible`, () => {
      const page = html(conceptPath(concept.id));
      for (const candidate of concept.candidates) expect(page).toContain(`data-candidate="${candidate.provider}"`);
      expect(page).toContain(`data-snapshot="${concept.snapshot ? "served" : "local"}"`);
      const islands = tags(page).filter(
        (tag) => tag.startsWith("<astro-island") && /\/SeriesExplorer\./.test(attributes(tag).get("component-url") ?? ""),
      );
      expect(islands).toHaveLength(1);
      const island = attributes(islands[0] ?? "");
      expect(island.get("client")).toBe("visible");
      expect(island.get("props")).toContain(concept.id);
      expect(page).toContain('<div id="plotly.js-style-global" class="no-inline-styles" hidden="">');
      expect(page).toContain("data-pagefind-body");
    });
  }

  it("links each model's bound concepts to their pages, and says which sources the hosted site may not serve", () => {
    for (const model of registryData.models) {
      const page = html(modelPath(model.id));
      const bindings = (model.bindings ?? []) as { concept: string }[];
      for (const binding of bindings) expect(page, model.id).toContain(`href="${conceptPath(binding.concept)}"`);
      const unserved = unservedSources(dataProfiles(bindings as never, conceptData, sourceData));
      expect(page.includes("data-library-only"), model.id).toBe(unserved.length > 0);
    }
    expect(html(modelPath("equity.cape"))).toContain("data-library-only");
  });
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

  it("holds no markup from card text: no script but its JSON-LD and the islands', no handler, style or frame", () => {
    for (const path of [...PAGES, "/404.html"]) {
      const page = path.endsWith(".html") ? readFileSync(join(DIST, path), "utf8") : html(path);
      // Every page has the header's search island: Astro's runtime, inline and
      // hashed in the page's policy (checkPage, the post-build check, finds no
      // problem), and its one style element. The only forms are the search
      // forms, the /models/ filters, a data concept's series reader and the
      // sign-up forms, which post to the email processor (Step 15); the only
      // other script is the Pro preview's, a same-origin module.
      expect(checkPage(page).problems, path).toEqual([]);
      for (const tag of tags(page)) {
        const name = /^<([a-zA-Z][a-zA-Z0-9-]*)/.exec(tag)?.[1]?.toLowerCase() ?? "";
        const runtime = tag === "<script>" || tag === "<style>";
        const form = attributes(tag);
        const known =
          name === "form" &&
          (form.get("role") === "search" ||
            ["Filter models", "Read the series"].includes(form.get("aria-label") ?? "") ||
            (form.get("action") === SIGNUP_ACTION && form.get("method") === "post"));
        const proScript =
          path === "/pro/" && name === "script" && form.get("type") === "module" && /^\/_astro\/[\w.-]+\.js$/.test(form.get("src") ?? "");
        if (!runtime && !known) expect(["iframe", "object", "embed", "style", "form", "base"], `${path}: ${tag}`).not.toContain(name);
        if (name === "script" && !runtime && !proScript) expect(attributes(tag).get("type"), `${path}: ${tag}`).toBe("application/ld+json");
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

/** A page's text as a reader sees it: no head, script, style, tag or attribute. */
function text(page: string): string {
  return page
    .replace(/<head[\s\S]*?<\/head>/, "")
    .replace(/<script[\s\S]*?<\/script>/g, "")
    .replace(/<style[\s\S]*?<\/style>/g, "")
    .replace(/<[^>]*>/g, " ")
    .replaceAll("&#174;", "®")
    .replaceAll("&reg;", "®")
    .replace(/\s+/g, " ");
}

/** Every page's file, the 404 page's included. */
const DOCUMENTS = [...PAGES.map((path) => `${path.slice(1)}index.html`), "404.html"];

describe("navigation", () => {
  it("puts the fifteen domain sections in the header of every page, in order, with breadcrumbs", () => {
    const expected = DOMAINS.map((domain) => domainPath(domain.id));
    for (const file of DOCUMENTS) {
      const page = readFileSync(join(DIST, file), "utf8");
      for (const list of ["data-domains-row", "data-domains-menu"]) {
        const start = page.indexOf(list);
        expect(start, `${file}: ${list}`).toBeGreaterThan(0);
        const block = page.slice(start, page.indexOf("</ul>", start));
        const links = [...block.matchAll(/href="([^"]+)"/g)].map((match) => match[1]);
        expect(links, `${file}: ${list}`).toEqual(expected);
      }
      expect(page, file).toContain('<nav aria-label="Breadcrumb"');
    }
  });

  it("lists each populated domain's models, and gives micro and alternatives a Phase 7 empty state", () => {
    for (const domain of DOMAINS) {
      const page = html(domainPath(domain.id));
      const models = registryData.models.filter((model) => model.domain === domain.id).map((model) => model.id);
      const listed = [...page.matchAll(/data-model="([^"]+)"/g)].map((match) => match[1]);
      expect(listed.sort(), domain.id).toEqual(models.sort());
      if (domain.planned) {
        expect(models, domain.id).toEqual([]);
        expect(page).toContain(`data-empty-domain="${domain.id}"`);
        expect(text(page)).toContain(`Its first models arrive in ${domain.planned}`);
        expect(page).toContain('href="/coverage/"');
      }
    }
    expect(DOMAINS.filter((domain) => domain.planned).map((domain) => domain.id)).toEqual(["micro", "alternatives"]);
  });

  it("renders every model in the /models/ list before any filter runs", () => {
    const listed = [...html("/models/").matchAll(/data-model="([^"]+)"/g)].map((match) => match[1]);
    expect(listed.sort()).toEqual(registryData.models.map((model) => model.id).sort());
  });

  it("publishes a coverage matrix whose counts are the registry's and the seed's", () => {
    const page = html("/coverage/");
    const seed = syllabusData[0];
    const models = new Map(Object.entries(seed?.models ?? {}));
    for (const topic of seed?.topics ?? []) {
      const count = [...models.values()].filter((topics) => topics.includes(topic.id)).length;
      expect(page, topic.id).toContain(`data-topic="${topic.id}" data-count="${String(count)}"`);
    }
    const covered = new Set([...models.values()].flat()).size;
    expect(page).toContain(`data-coverage-covered="${String(covered)}" data-coverage-total="${String(seed?.topics.length)}"`);
    for (const domain of DOMAINS) {
      const count = registryData.models.filter((model) => model.domain === domain.id).length;
      expect(page, domain.id).toContain(`data-domain="${domain.id}" data-count="${String(count)}"`);
    }
    expect(text(page)).toContain("Planned: Phase 7");
  });

  it("ships Pagefind's index, its API and worker, and none of its UI bundles", () => {
    const entry = JSON.parse(readFileSync(join(DIST, "pagefind", "pagefind-entry.json"), "utf8")) as {
      languages: Record<string, { page_count: number }>;
    };
    const searchable = DOCUMENTS.filter((file) => readFileSync(join(DIST, file), "utf8").includes("data-pagefind-body"));
    expect(Object.values(entry.languages).reduce((sum, language) => sum + language.page_count, 0)).toBe(searchable.length);
    expect(searchable).not.toContain("404.html");
    for (const model of registryData.models) expect(searchable).toContain(`${modelPath(model.id).slice(1)}index.html`);
    for (const file of ["pagefind/pagefind.js", "pagefind/pagefind-worker.js"]) expect(FILES).toContain(file);
    expect(FILES.filter((file) => /^pagefind\/pagefind-(ui|modular-ui|component-ui|highlight)/.test(file))).toEqual([]);
  });
});

describe("CFA Institute's marks", () => {
  it("never puts cfa in a path or query value of the site's own URLs", () => {
    const found: string[] = [];
    const check = (where: string, url: string) => {
      const own = url.startsWith("/") ? !url.startsWith("//") : url === ORIGIN || url.startsWith(`${ORIGIN}/`);
      if (!own) return;
      const parsed = new URL(url, ORIGIN);
      const values = [...parsed.searchParams.values()];
      if (/cfa/i.test(decodeURIComponent(parsed.pathname)) || values.some((value) => /cfa/i.test(value))) {
        found.push(`${where}: ${url}`);
      }
    };
    for (const file of DOCUMENTS) {
      const page = readFileSync(join(DIST, file), "utf8");
      for (const tag of tags(page)) {
        const values = attributes(tag);
        for (const name of ["href", "src", "action", "content"]) {
          const value = values.get(name);
          if (value) check(file, value);
        }
      }
      // The islands' props, which carry each result's path.
      for (const match of page.matchAll(/&quot;(\/[^&]*)&quot;/g)) check(`${file} (props)`, match[1] ?? "");
    }
    for (const file of FILES.filter((name) => /^sitemap-\d+\.xml$/.test(name))) {
      for (const match of readFileSync(join(DIST, file), "utf8").matchAll(/<loc>([^<]*)<\/loc>/g)) check(file, match[1] ?? "");
    }
    for (const line of readFileSync(join(DIST, "_redirects"), "utf8").split("\n").filter(Boolean)) {
      for (const part of line.split(" ").slice(0, 2)) check("_redirects", part);
    }
    expect(found).toEqual([]);
  });

  it("uses the mark as an adjective, with ® on first use, beside the non-affiliation notice", () => {
    const ALLOWED = /^CFA(® Program|® and Chartered Financial Analyst®| Program| Institute)/;
    for (const file of DOCUMENTS) {
      // The maintainer's designation after his name ("Sign as 'Nathan Ramos,
      // CFA'", ROADMAP §5), which the licence page's NOTICE carries, is not
      // the mark used as an adjective and takes no ®.
      const words = text(readFileSync(join(DIST, file), "utf8")).replaceAll("Nathan Ramos, CFA", "Nathan Ramos");
      const uses = [...words.matchAll(/CFA/g)].map((match) => words.slice(match.index, match.index + 40));
      for (const use of uses) expect(use, file).toMatch(ALLOWED);
      const marks = uses.filter((use) => !use.startsWith("CFA Institute"));
      expect(marks[0]?.startsWith("CFA®"), file).toBe(true);
      expect(words, file).toContain("pyeconomics is not affiliated with, endorsed by, or a Prep Provider of CFA Institute.");
    }
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

/** Each form of a page: its start tag's attributes, its fields' attributes and its markup. */
function forms(page: string): { form: Map<string, string>; fields: Map<string, string>[]; body: string }[] {
  return [...page.matchAll(/(<form\b[^>]*>)([\s\S]*?)<\/form>/g)].map((match) => ({
    form: attributes(match[1] ?? ""),
    fields: tags(match[2] ?? "")
      .filter((tag) => /^<(input|select|textarea|button)\b/i.test(tag))
      .map((tag) => attributes(tag)),
    body: match[2] ?? "",
  }));
}

describe("growth signals (Phase 5 Step 15)", () => {
  const signups = (page: string) => forms(page).filter(({ form }) => form.get("action") === SIGNUP_ACTION);

  it("posts every sign-up form straight to the processor, with the address and fixed fields only", () => {
    let seen = 0;
    for (const path of PAGES) {
      for (const { form, fields, body } of signups(html(path))) {
        seen += 1;
        expect(form.get("method"), path).toBe("post");
        expect(form.has("target"), path).toBe(false);
        const list = form.get("data-signup");
        const named = fields.filter((field) => field.has("name"));
        const names = [...new Set(named.map((field) => field.get("name")))].sort();
        const expected = ["email", "embed", `metadata__${String(list)}`, `metadata__${String(list)}_source`, ...(list === "waitlist" ? ["metadata__tier"] : [])];
        expect(names, path).toEqual(expected.sort());
        expect(named.find((field) => field.get("name") === "email")?.get("type"), path).toBe("email");
        // Each list's own keys, so a second sign-up never overwrites the first.
        expect(named.find((field) => field.get("name") === `metadata__${String(list)}`)?.get("value"), path).toBe("yes");
        expect(named.find((field) => field.get("name") === "embed")?.get("value"), path).toBe("1");
        for (const field of named.filter((entry) => entry.get("name") === "metadata__tier")) {
          expect(field.get("type"), path).toBe("radio");
          expect(["personal", "commercial", "team"], path).toContain(field.get("value"));
        }
        expect(body, path).toContain(`href="${PRIVACY_POLICY}"`);
        expect(text(body), path).toContain("confirm by the email");
      }
    }
    // The footer's form on every page but the two with their own, and theirs.
    expect(seen).toBe(PAGES.length);
  });

  it("puts no field anywhere that could take a password, a card or an account", () => {
    for (const path of PAGES) {
      for (const tag of tags(html(path))) {
        const found = attributes(tag);
        expect(found.get("type"), `${path}: ${tag}`).not.toBe("password");
        expect(found.get("autocomplete") ?? "", `${path}: ${tag}`).not.toMatch(/^cc-|password|username/);
        if (found.get("type") === "email") expect(found.get("name"), path).toBe("email");
      }
    }
  });

  it("leads /pro/ with the statement that nothing is sold, and shows the planned prices", () => {
    const page = html("/pro/");
    const note = /<div[^>]*data-disclosure="pro"[^>]*>([\s\S]*?)<\/div>/.exec(page)?.[1] ?? "";
    expect(text(note)).toContain(PRO_DISCLOSURE);
    expect(text(page).indexOf(PRO_DISCLOSURE)).toBeLessThan(text(page).indexOf("Indicative prices"));
    for (const tier of PRO_TIERS) expect(text(page)).toContain(`$${String(tier.price)}`);
    expect(signups(page).map(({ form }) => form.get("data-signup"))).toEqual(["waitlist"]);
    expect(page).not.toMatch(/card number|cvc|billing/i);
  });

  it("records only allowlisted clicks: every data-umami-event attribute passes the allowlist", () => {
    let clicks = 0;
    for (const path of DOCUMENTS) {
      for (const tag of tags(readFileSync(join(DIST, path), "utf8"))) {
        const found = attributes(tag);
        const event = found.get("data-umami-event");
        const properties = Object.fromEntries(
          [...found].filter(([key]) => key.startsWith("data-umami-event-")).map(([key, value]) => [key.slice("data-umami-event-".length), value]),
        );
        if (event === undefined) {
          expect(Object.keys(properties), `${path}: ${tag}`).toEqual([]);
          continue;
        }
        clicks += 1;
        expect(checkEvent(event, properties), `${path}: ${tag}`).not.toBeNull();
      }
    }
    expect(clicks).toBeGreaterThan(PAGES.length);
  });

  it("carries no tracker in a build that is not production's", () => {
    expect(existsSync(join(DIST, TRACKER_PATH))).toBe(false);
    for (const path of DOCUMENTS) expect(readFileSync(join(DIST, path), "utf8"), path).not.toContain("data-website-id");
  });

  it("links Discussions, the newsletter and the Pro preview from every page's footer", () => {
    for (const path of PAGES) {
      const footer = /<footer[\s\S]*?<\/footer>/.exec(html(path))?.[0] ?? "";
      for (const href of ["https://github.com/pyeconomics-dev/pyeconomics/discussions", "/newsletter/", "/pro/"]) {
        expect(footer, `${path}: ${href}`).toContain(`href="${href}"`);
      }
    }
  });
});

describe("legal and trust (Phase 5 Step 16)", () => {
  const LEGAL = [LEGAL_INDEX, ...LEGAL_PAGES];
  const FRED_NOTICE = "This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.";
  const COUNSEL = readFileSync(join(DIST, "..", "..", "docs", "operations", "counsel-review.md"), "utf8").replace(/\s+/g, " ");

  it("writes the legal pages, /sources/ and a security.txt that parses with Contact and Expires", () => {
    for (const page of LEGAL) expect(PAGES, page.path).toContain(page.path);
    const security = readFileSync(join(DIST, SECURITY_TXT_PATH), "utf8");
    expect(parseSecurityTxt(security).get("contact")).toEqual([VULNERABILITY_REPORTING]);
    expect(securityTxtProblems(security, new Date())).toEqual([]);
  });

  it("links every legal page from every page's footer, and marks each for search", () => {
    for (const path of PAGES) {
      const footer = /<footer[\s\S]*?<\/footer>/.exec(html(path))?.[0] ?? "";
      for (const page of LEGAL_PAGES) expect(footer, `${path}: ${page.path}`).toContain(`href="${page.path}"`);
    }
    for (const page of LEGAL) {
      const built = html(page.path);
      expect(built, page.path).toContain("data-pagefind-body");
      expect(built, page.path).toContain(`data-pagefind-meta="kind:${page.path === "/sources/" ? "Source" : "Legal"}"`);
    }
  });

  it("lists every provider on /sources/ with its class, attribution and notice", () => {
    const words = text(html("/sources/")).replaceAll("&quot;", '"').replaceAll("&#39;", "'").replaceAll("&amp;", "&");
    const page = html("/sources/");
    for (const source of sourceData) {
      expect(page, source.id).toContain(`data-source="${source.id}" data-licence="${source.licence}"`);
      expect(words, source.id).toContain(source.attribution.replace(/\s+/g, " "));
      if (source.notice) expect(words, source.id).toContain(source.notice.replace(/\s+/g, " "));
    }
  });

  it("shows FRED's notice only where /sources/ marks it as the local surfaces' notice", () => {
    const local = /<(dd|td)[^>]*data-local-only[^>]*>[\s\S]*?<\/\1>/g;
    expect(text(html("/sources/"))).toContain(FRED_NOTICE);
    for (const file of DOCUMENTS) {
      const page = readFileSync(join(DIST, file), "utf8").replace(local, "");
      expect(text(page), file).not.toContain("FRED® API but is not endorsed");
    }
  });

  it("puts the hypothetical-results legend beside the results of exactly the models whose tags mark them", () => {
    for (const model of parseModels(registryData)) {
      const page = html(modelPath(model.id));
      const places = [...page.matchAll(/data-legend-place="([a-z-]+)"/g)].map((match) => match[1]);
      const expected = simulates(model) ? ["calculator", ...(model.example_result ? ["worked-example"] : [])] : [];
      expect(places, model.id).toEqual(expected);
      if (simulates(model)) expect(text(page), model.id).toContain(HYPOTHETICAL_LEGEND);
    }
    const disclaimers = html("/legal/disclaimers/");
    const listed = [...disclaimers.matchAll(/data-legend-model="([a-z_.]+)"/g)].map((match) => match[1]).sort();
    expect(listed).toEqual(
      parseModels(registryData)
        .filter(simulates)
        .map((model) => model.id)
        .sort(),
    );
    expect(text(disclaimers)).toContain(CFTC_STATEMENT);
  });

  it("passes the New York Fed's and the OECD's conditions through, and links every served source's terms", () => {
    const page = html("/legal/terms/");
    const words = text(page);
    expect(page).toContain('data-pass-through="nyfed"');
    expect(page).toContain('data-pass-through="oecd"');
    expect(words).toContain("You may not impose more restrictive terms or conditions on the Content.");
    expect(words).toContain("DTCC Solutions LLC");
    expect(words).toContain("you agree to include the same acknowledgment requirement in any sub-licenses that you grant");
    for (const source of sourceData.filter((entry) => entry.snapshot_series > 0)) {
      expect(page, source.id).toContain(`href="${source.terms_url}"`);
    }
  });

  it("generates the privacy policy from every data flow and processor, with the promises the tests prove", () => {
    const page = html("/legal/privacy/");
    const flows = [...page.matchAll(/data-flow="([a-z-]+)"/g)].map((match) => match[1]);
    expect(flows).toEqual(DATA_FLOWS.flows.map((flow) => flow.id));
    const processors = [...page.matchAll(/data-processor-entry="([a-z-]+)"/g)].map((match) => match[1]);
    expect(processors).toEqual(DATA_FLOWS.processors.map((processor) => processor.id));
    const words = text(page);
    for (const promise of ["POST", "never uploaded", "request logs", "excluded", "No cookies"]) expect(words).toContain(promise);
  });

  it("lists every shipped package and the NOTICE on the licence page", () => {
    const page = html("/legal/licence/");
    const listed = [...page.matchAll(/data-package="([^"]+)"/g)].length;
    expect(listed).toBe(shippedLicences(join(DIST, ".."), false).length);
    expect(text(page)).toContain("This product is licensed under the Apache License, Version 2.0");
  });

  it("records every open counsel question in docs/operations/counsel-review.md", () => {
    let found = 0;
    for (const file of DOCUMENTS) {
      const page = readFileSync(join(DIST, file), "utf8");
      for (const match of page.matchAll(/data-counsel="">[\s\S]*?<\/span>([\s\S]*?)<\/p>/g)) {
        const question = (match[1] ?? "")
          .replaceAll("&#39;", "'")
          .replaceAll("&quot;", '"')
          .replaceAll("&amp;", "&")
          .replace(/\s+/g, " ")
          .trim();
        expect(COUNSEL, `${file}: ${question}`).toContain(question);
        found += 1;
      }
    }
    expect(found).toBeGreaterThan(0);
  });
});
