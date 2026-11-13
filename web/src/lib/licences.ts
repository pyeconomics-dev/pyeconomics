// web/src/lib/licences.ts
// The third-party licences of what ships to browsers, for /legal/licence/
// (Phase 5 Step 16; ROADMAP §4 5.7). The bundles keep few licence comments, and
// the pyeconomics-app wheel redistributes the built site, so this page is the
// notice for both. It is read at build time from the production dependency
// tree, the one scripts/checks/web_licences.py holds to the allowlist: every
// package web/package-lock.json does not mark `dev`, plus the build tools whose
// own code reaches pages (BUILD_OUTPUT, held equal to web_licences.py's by
// tests/web/test_explorer_constants.py) and, in a build that serves it, the
// vendored analytics tracker. Each entry carries the licence file its package
// ships, verbatim; a package that ships none is listed with its declared
// licence and says so.
//
// Build time only: it reads node_modules/ with node:fs, from the web project's
// directory (the build's and the tests' working directory), so no page imports
// it into a client bundle.

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

/** Build tools whose own code reaches pages, and what of it does (web_licences.py BUILD_OUTPUT). */
export const BUILD_OUTPUT = ["astro", "@astrojs/react", "plotly.js"] as const;

/** What each build tool contributes to pages. */
const BUILD_OUTPUT_NOTES: ReadonlyMap<string, string> = new Map([
  ["astro", "the island runtime Astro inlines into pages"],
  ["@astrojs/react", "the React client renderer in the client bundle"],
  ["plotly.js", "its prebuilt dist/plotly-basic.min.js and dist/plotly.css"],
]);

/** One shipped package and its licence. */
export interface ShippedLicence {
  name: string;
  version: string;
  /** The SPDX expression its lockfile entry declares. */
  licence: string;
  /** The package's repository or home page, when it names one on https. */
  url: string | null;
  /** Its licence file, verbatim, or null when the package ships none. */
  text: string | null;
  /** Why it ships: a dependency, build output, or the vendored tracker. */
  why: string;
}

interface LockEntry {
  version?: string;
  license?: string;
  dev?: boolean;
  link?: boolean;
}

/** The package a lockfile path installs: `node_modules/a/node_modules/@s/b` is `@s/b`. */
export function packageName(path: string): string {
  return path.slice(path.lastIndexOf("node_modules/") + "node_modules/".length);
}

const LICENCE_FILE = /^(licen[cs]e|copying)(\.(md|txt|markdown))?$/i;

function readText(path: string): string {
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- a file listed under node_modules/
  return readFileSync(path, "utf8").replaceAll("\r\n", "\n").trim();
}

/**
 * The first licence file in a directory, verbatim, or null. A package that
 * ships its licences as a directory (pagefind's LICENSE/ holds its own and
 * ripgrep's) gives every file in it, each under its name.
 */
export function licenceText(directory: string): string | null {
  // A directory under node_modules/, from the lockfile's own paths.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  if (!existsSync(directory)) return null;
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  const found = readdirSync(directory, { withFileTypes: true })
    .filter((entry) => LICENCE_FILE.test(entry.name) && (entry.isFile() || entry.isDirectory()))
    .sort((a, b) => a.name.localeCompare(b.name))
    .at(0);
  if (found === undefined) return null;
  const path = join(directory, found.name);
  if (found.isFile()) return readText(path);
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- the licence directory just found
  const files = readdirSync(path, { withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => entry.name)
    .sort();
  return files.length === 0 ? null : files.map((name) => `${name}\n\n${readText(join(path, name))}`).join("\n\n");
}

/** A package.json's repository or home page, if it is an https URL. */
export function packageUrl(manifest: { repository?: unknown; homepage?: unknown }): string | null {
  const repository = manifest.repository;
  const raw =
    typeof repository === "string"
      ? repository
      : typeof repository === "object" && repository !== null && "url" in repository
        ? String((repository as { url: unknown }).url)
        : typeof manifest.homepage === "string"
          ? manifest.homepage
          : "";
  const cleaned = raw.replace(/^git\+/, "").replace(/\.git$/, "").replace(/^git:\/\//, "https://");
  if (/^github:/.test(cleaned)) return `https://github.com/${cleaned.slice("github:".length)}`;
  if (/^[\w.-]+\/[\w.-]+$/.test(cleaned)) return `https://github.com/${cleaned}`;
  return /^https:\/\/[^\s"<>]+$/.test(cleaned) ? cleaned : null;
}

/** Read one installed package's entry. */
function installed(root: string, path: string, entry: LockEntry, why: string): ShippedLicence {
  const directory = join(root, path);
  const manifestPath = join(directory, "package.json");
  let manifest: { repository?: unknown; homepage?: unknown } = {};
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- a lockfile path under node_modules/
  if (existsSync(manifestPath)) {
    // eslint-disable-next-line security/detect-non-literal-fs-filename -- the same path
    manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as { repository?: unknown; homepage?: unknown };
  }
  return {
    name: packageName(path),
    version: entry.version ?? "",
    licence: entry.license ?? "",
    url: packageUrl(manifest),
    text: licenceText(directory),
    why,
  };
}

/**
 * Every package whose code reaches browsers, sorted by name then version.
 *
 * `root` is the web project's directory; `tracker` adds the vendored Umami
 * tracker, which only a production build given its website id serves.
 */
export function shippedLicences(root: string = process.cwd(), tracker = false): ShippedLicence[] {
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- the web project's lockfile
  const lock = JSON.parse(readFileSync(join(root, "package-lock.json"), "utf8")) as {
    packages: Record<string, LockEntry>;
  };
  const entries: ShippedLicence[] = [];
  const packages = new Map(Object.entries(lock.packages));
  for (const [path, entry] of packages) {
    if (path === "" || entry.dev === true || entry.link === true) continue;
    entries.push(installed(root, path, entry, "a production dependency"));
  }
  for (const name of BUILD_OUTPUT) {
    const path = `node_modules/${name}`;
    const entry = packages.get(path);
    if (entry === undefined) throw new Error(`package-lock.json has no ${path}`);
    entries.push(installed(root, path, entry, `build output: ${BUILD_OUTPUT_NOTES.get(name) ?? ""}`));
  }
  if (tracker) {
    entries.push({
      name: "umami (tracker script.js)",
      version: "v3.4.1",
      licence: "MIT",
      url: "https://github.com/umami-software/umami",
      text: licenceText(join(root, "vendor", "umami")),
      why: "the cookie-less analytics tracker, vendored byte for byte",
    });
  }
  return entries.sort((a, b) => a.name.localeCompare(b.name) || a.version.localeCompare(b.version));
}

/** A file at the repository's root (LICENSE, NOTICE), verbatim, from the web project's directory. */
export function repositoryFile(name: "LICENSE" | "NOTICE", root: string = process.cwd()): string {
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- one of two fixed names beside web/
  return readFileSync(join(root, "..", name), "utf8").replaceAll("\r\n", "\n").trim();
}

/** The licences shipped, with how many packages use each, most used first. */
export function licenceCounts(entries: readonly ShippedLicence[]): [string, number][] {
  const counts = new Map<string, number>();
  for (const entry of entries) counts.set(entry.licence, (counts.get(entry.licence) ?? 0) + 1);
  return [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}
