// web/scripts/search-index.ts
// The post-build search step (Phase 5 Step 7; ADR-0013 decision 10). After
// `astro build`, scripts/headers.ts and scripts/indexing.ts, it runs Pagefind
// over dist/ and writes the index and Pagefind's search bundle into
// dist/pagefind/, which the search islands load from the site's own origin
// (src/lib/search.ts). Pagefind indexes only the pages whose main landmark
// carries data-pagefind-body (Base.astro's `searchable`: the model, domain and
// problem pages), so the 404 page, the home page, /search/ and the redirects
// (_redirects, which are not pages) stay out. Pagefind's prebuilt UI bundles,
// which the site does not use, are removed, so only the API, its worker, its
// WebAssembly and the index ship.
//
// It fails the build, naming each problem, on:
// - an error Pagefind reports;
// - an indexed page count (pagefind-entry.json's) other than the number of
//   pages marked searchable;
// - a model page that is not marked searchable, or a 404 page that is;
// - a dist/pagefind/ that already exists (it comes from here, never public/).
import { existsSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

import { modelPath } from "../src/lib/paths.ts";

const WEB = fileURLToPath(new URL("..", import.meta.url));

/** Where the bundle goes, under dist/. */
export const BUNDLE_DIRECTORY = "pagefind";

/** The marker a searchable page's main landmark carries. */
export const MARKER = "data-pagefind-body";

/** Pagefind's prebuilt UI files, which the site does not load. */
export const UNUSED = [
  "pagefind-ui.js",
  "pagefind-ui.css",
  "pagefind-modular-ui.js",
  "pagefind-modular-ui.css",
  "pagefind-component-ui.js",
  "pagefind-component-ui.css",
  "pagefind-highlight.js",
] as const;

/** The pages a build marks searchable, as paths under dist/. */
export function searchablePages(files: readonly string[], read: (file: string) => string): string[] {
  return files.filter((file) => file.endsWith(".html") && read(file).includes(MARKER)).sort();
}

/** What is wrong with the pages a build marks searchable. */
export function checkSearchable(
  files: readonly string[],
  searchable: readonly string[],
  modelIds: readonly string[],
): string[] {
  const problems: string[] = [];
  const marked = new Set(searchable);
  for (const id of modelIds) {
    const file = `${modelPath(id).slice(1)}index.html`;
    if (!files.includes(file)) problems.push(`${file}: the model page ${id} was not built`);
    else if (!marked.has(file)) problems.push(`${file}: the model page ${id} is not marked ${MARKER}`);
  }
  if (marked.has("404.html")) problems.push(`404.html is marked ${MARKER}; the 404 page is never searched`);
  return problems;
}

/**
 * The pages an index holds, from Pagefind's pagefind-entry.json (the count
 * addDirectory returns is every HTML file it read, marked or not).
 */
export function indexedPages(entry: string): number {
  const languages = (JSON.parse(entry) as { languages?: Record<string, { page_count?: number }> }).languages ?? {};
  return Object.values(languages).reduce((sum, language) => sum + (language.page_count ?? 0), 0);
}

function walk(root: string, directory = root): string[] {
  // The build output directory only: every path comes from readdirSync.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? walk(root, path) : [relative(root, path).split(sep).join("/")];
  });
}

async function main(): Promise<number> {
  const dist = join(WEB, "dist");
  const bundle = join(dist, BUNDLE_DIRECTORY);
  const problems: string[] = [];
  // Fixed paths under the build output directory.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  if (!existsSync(dist)) {
    process.stderr.write("search-index: no dist/ to index; run `npm run build`\n");
    return 1;
  }
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- the bundle's fixed path
  if (existsSync(bundle)) problems.push(`dist/${BUNDLE_DIRECTORY}/ already exists: the index comes from here, never public/`);
  const files = walk(dist);
  // A file walk() found under the build output.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  const searchable = searchablePages(files, (file) => readFileSync(join(dist, file), "utf8"));
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- the generated registry, a fixed path
  const registry = JSON.parse(readFileSync(join(WEB, "src", "data", "generated", "registry.json"), "utf8")) as {
    models: { id: string }[];
  };
  problems.push(
    ...checkSearchable(
      files,
      searchable,
      registry.models.map((model) => model.id),
    ),
  );
  if (problems.length === 0) {
    const pagefind = await import("pagefind");
    const { errors, index } = await pagefind.createIndex({ forceLanguage: "en" });
    problems.push(...errors);
    if (index) {
      problems.push(...(await index.addDirectory({ path: dist })).errors);
      if (problems.length === 0) problems.push(...(await index.writeFiles({ outputPath: bundle })).errors);
    }
    await pagefind.close();
  }
  if (problems.length === 0) {
    // The entry file Pagefind just wrote, at its fixed name.
    // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
    const indexed = indexedPages(readFileSync(join(bundle, "pagefind-entry.json"), "utf8"));
    if (indexed !== searchable.length) {
      problems.push(`Pagefind indexed ${indexed} pages; ${searchable.length} are marked ${MARKER}`);
    }
  }
  if (problems.length > 0) {
    process.stderr.write(`search-index: the search index cannot be built:\n${problems.map((p) => `  ${p}`).join("\n")}\n`);
    return 1;
  }
  // The bundle directory this step just wrote, and fixed file names in it.
  for (const name of UNUSED) rmSync(join(bundle, name), { force: true });
  process.stdout.write(`search-index: ${searchable.length} pages indexed into dist/${BUNDLE_DIRECTORY}/\n`);
  return 0;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  process.exit(await main());
}
