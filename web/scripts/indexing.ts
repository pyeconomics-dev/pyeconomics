// web/scripts/indexing.ts
// The post-build indexing step (Phase 5 Step 5; ADR-0013 decisions 2 and 4).
// After `astro build` and scripts/headers.ts, it writes into dist/:
// - robots.txt, naming the sitemap, and refusing every path (`Disallow: /`) in
//   a build that must not be indexed: every staging build and a production
//   build of a pre-release (headers.ts indexable(), which also sends
//   X-Robots-Tag: noindex through _headers);
// - _redirects, sending each model alias's page to its model's page (301), so
//   a retired id's URL keeps answering.
//
// It fails the build, naming each problem, on:
// - a path web/released-pages.json lists that neither builds nor redirects:
//   a page that has shipped never disappears (the pages' equivalent of the
//   released-id ledger);
// - a page the sitemap does not list, or a sitemap entry off the production
//   origin;
// - a robots.txt or _redirects file that came from public/ instead of here.
import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

import { ORIGIN, modelPath } from "../src/lib/paths.ts";
import { buildVersion, indexable, siteFlavour } from "./headers.ts";

const WEB = fileURLToPath(new URL("..", import.meta.url));

/** The sitemap @astrojs/sitemap writes, which robots.txt names. */
export const SITEMAP = `${ORIGIN}/sitemap-index.xml`;

/** robots.txt: every path allowed, or every path refused; the sitemap either way. */
export function robotsTxt(index: boolean): string {
  return `User-agent: *\n${index ? "Allow" : "Disallow"}: /\n\nSitemap: ${SITEMAP}\n`;
}

/** The models and aliases the redirects are written from (registry.json). */
export interface AliasSource {
  id: string;
  aliases: readonly { id: string }[];
}

/** One permanent redirect: a path that answers 301 with another. */
export interface Redirect {
  from: string;
  to: string;
}

/**
 * Every alias's page, with and without its trailing slash, to its model's
 * page. An alias that is also a model's id, or two models claiming one alias,
 * is an error: the registry refuses both, and so does the build.
 */
export function aliasRedirects(models: readonly AliasSource[]): Redirect[] {
  const pages = new Set(models.map((model) => modelPath(model.id)));
  const seen = new Map<string, string>();
  const redirects: Redirect[] = [];
  for (const model of models) {
    const to = modelPath(model.id);
    for (const alias of model.aliases) {
      const from = modelPath(alias.id);
      if (pages.has(from)) throw new Error(`alias ${alias.id} of ${model.id} is a model's page`);
      const claimed = seen.get(from);
      if (claimed !== undefined) throw new Error(`alias ${alias.id} names both ${claimed} and ${model.id}`);
      seen.set(from, model.id);
      redirects.push({ from, to }, { from: from.slice(0, -1), to });
    }
  }
  return redirects.sort((a, b) => a.from.localeCompare(b.from));
}

/** The _redirects file Workers static assets read. */
export function renderRedirects(redirects: readonly Redirect[]): string {
  return redirects.map(({ from, to }) => `${from} ${to} 301\n`).join("");
}

/** web/released-pages.json: every page path a release has served, sorted. */
export interface Ledger {
  format: 1;
  pages: string[];
}

/** Read and check the ledger's shape: format 1, sorted, unique page paths. */
export function parseLedger(text: string): Ledger {
  const ledger = JSON.parse(text) as Partial<Ledger>;
  if (ledger.format !== 1 || !Array.isArray(ledger.pages)) {
    throw new Error("released-pages.json must be {\"format\": 1, \"pages\": [...]}");
  }
  for (const page of ledger.pages) {
    const segments = typeof page === "string" ? page.split("/") : [];
    const isPage =
      segments.length >= 2 &&
      segments[0] === "" &&
      segments.at(-1) === "" &&
      segments.slice(1, -1).every((segment) => /^[a-z0-9-]+$/.test(segment));
    if (!isPage) {
      throw new Error(`released-pages.json lists ${JSON.stringify(page)}, not a page path with a trailing slash`);
    }
  }
  const sorted = [...new Set(ledger.pages)].sort();
  if (sorted.join("\n") !== ledger.pages.join("\n")) {
    throw new Error("released-pages.json must list each page once, sorted");
  }
  return ledger as Ledger;
}

/** Every page path the build wrote (`<path>/index.html`), sorted. */
export function builtPages(files: readonly string[]): string[] {
  return files
    .filter((file) => file === "index.html" || file.endsWith("/index.html"))
    .map((file) => `/${file.slice(0, -"index.html".length)}`)
    .sort();
}

/** The ledger's paths that neither build nor redirect. */
export function missingReleased(ledger: Ledger, pages: readonly string[], redirects: readonly Redirect[]): string[] {
  const answered = new Set([...pages, ...redirects.map((redirect) => redirect.from)]);
  return ledger.pages.filter((page) => !answered.has(page));
}

/** The page paths a sitemap's <loc> entries name, and the entries off the origin. */
export function sitemapPaths(xml: string): { paths: string[]; foreign: string[] } {
  const locations = [...xml.matchAll(/<loc>([^<]*)<\/loc>/g)].map((match) => match[1] ?? "");
  const paths: string[] = [];
  const foreign: string[] = [];
  for (const location of locations) {
    if (location.startsWith(`${ORIGIN}/`)) paths.push(location.slice(ORIGIN.length));
    else foreign.push(location);
  }
  return { paths, foreign };
}

function walk(root: string, directory = root): string[] {
  // The build output directory only: every path comes from readdirSync.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? walk(root, path) : [relative(root, path).split(sep).join("/")];
  });
}

/** What the indexing step writes into a build, and what is wrong with it. */
export interface IndexingReport {
  problems: string[];
  files: Record<string, string>;
}

/** Check a build and return robots.txt and _redirects for it. */
export function checkIndexing(
  dist: string,
  { index, models, ledger }: { index: boolean; models: readonly AliasSource[]; ledger: Ledger },
): IndexingReport {
  const problems: string[] = [];
  const files = walk(dist);
  for (const name of ["robots.txt", "_redirects"]) {
    if (files.includes(name)) problems.push(`dist/${name} already exists: it comes from scripts/indexing.ts, never public/`);
  }
  const pages = builtPages(files);
  let redirects: Redirect[] = [];
  try {
    redirects = aliasRedirects(models);
  } catch (error) {
    problems.push((error as Error).message);
  }
  for (const page of missingReleased(ledger, pages, redirects)) {
    problems.push(`${page} is in released-pages.json but neither builds nor redirects: a shipped page never disappears`);
  }
  const sitemaps = files.filter((file) => /^sitemap-\d+\.xml$/.test(file));
  if (!files.includes("sitemap-index.xml") || sitemaps.length === 0) {
    problems.push("the build wrote no sitemap");
  } else {
    const listed = new Set<string>();
    for (const sitemap of sitemaps) {
      // A file walk() found under the build output.
      // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
      const { paths, foreign } = sitemapPaths(readFileSync(join(dist, sitemap), "utf8"));
      for (const path of paths) listed.add(path);
      for (const location of foreign) problems.push(`${sitemap} lists ${location}, off ${ORIGIN}`);
    }
    for (const page of pages) {
      if (!listed.has(page)) problems.push(`the sitemap does not list ${page}`);
    }
  }
  return { problems, files: { "robots.txt": robotsTxt(index), _redirects: renderRedirects(redirects) } };
}

function main(): number {
  const dist = join(WEB, "dist");
  // The build output directory, a fixed path.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  if (!existsSync(dist)) {
    process.stderr.write("indexing: no dist/ to check; run `npm run build`\n");
    return 1;
  }
  let report: IndexingReport;
  let index: boolean;
  try {
    index = indexable(siteFlavour(), buildVersion());
    // Fixed paths under web/: the generated registry and the ledger.
    // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
    const registry = JSON.parse(readFileSync(join(WEB, "src", "data", "generated", "registry.json"), "utf8")) as {
      models: AliasSource[];
    };
    // eslint-disable-next-line security/detect-non-literal-fs-filename -- the ledger, a fixed path
    const ledger = parseLedger(readFileSync(join(WEB, "released-pages.json"), "utf8"));
    report = checkIndexing(dist, { index, models: registry.models, ledger });
  } catch (error) {
    process.stderr.write(`indexing: ${(error as Error).message}\n`);
    return 1;
  }
  if (report.problems.length > 0) {
    process.stderr.write(`indexing: the build cannot be indexed as built:\n${report.problems.map((p) => `  ${p}`).join("\n")}\n`);
    return 1;
  }
  for (const [name, text] of Object.entries(report.files)) {
    // A fixed name under the build output directory.
    // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
    writeFileSync(join(dist, name), text);
  }
  const redirects = report.files._redirects?.split("\n").filter(Boolean).length ?? 0;
  process.stdout.write(
    `indexing: robots.txt ${index ? "allows" : "refuses"} indexing; ${redirects} alias redirects; the ledger and the sitemap hold\n`,
  );
  return 0;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  process.exit(main());
}
