// web/scripts/headers.ts
// The post-build headers step (ADR-0013 decision 9). Astro writes each page's
// policy, with the hashes of what it inlined, into a <meta> element; only a
// header can carry frame-ancestors, and the Cloudflare adapter sends none, so
// this step reads every page's policy and writes their union into
// dist/_headers, with the other security headers and a year's immutable
// caching for /_astro/*.
//
// It fails the build, naming each problem, on:
// - 'unsafe-inline', 'unsafe-eval' or any source csp.config.ts does not allow;
// - a page with no policy, more than one, or a directive missing or changed;
// - an inline script or style whose hash the page's policy lacks, an inline
//   style attribute, an event-handler attribute or a javascript: URL;
// - a script or stylesheet from another origin;
// - a _headers line over 2,000 characters or more than 100 rules
//   (Cloudflare's limits);
// - any server-rendered route in the build output, or a _headers file that
//   came from public/ instead of from here.
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

import {
  ALLOWED,
  DIRECTIVES,
  FORBIDDEN,
  HASHED,
  HEADER_ONLY,
  IMMUTABLE,
  SECURITY_HEADERS,
} from "../csp.config.ts";

/** Cloudflare's limits on a _headers file (ADR-0013 decision 9). */
export const MAX_LINE = 2000;
export const MAX_RULES = 100;

/** Build output that only a server-rendered route produces. */
export const SERVER_OUTPUT = ["_worker.js", "_routes.json", "server", "chunks", "entry.mjs"];

/** Script types a browser executes, which the policy must therefore hash. */
const EXECUTED = new Set([
  "",
  "module",
  "text/javascript",
  "application/javascript",
  "importmap",
  "speculationrules",
]);

const HASH = /^'sha256-[A-Za-z0-9+/]{43}='$/;

const BASE = new Map(Object.entries(DIRECTIVES));
const PERMITTED = new Map(Object.entries(ALLOWED));

/** A policy: each directive's sources, in the order they were written. */
export type Policy = Map<string, string[]>;

/** Parse a policy's text; a repeated directive is an error. */
export function parsePolicy(text: string): Policy {
  const policy: Policy = new Map();
  for (const part of text.split(";")) {
    const [name, ...sources] = part.trim().split(/\s+/);
    if (!name) continue;
    const key = name.toLowerCase();
    if (policy.has(key)) throw new Error(`the policy repeats ${key}`);
    policy.set(key, sources);
  }
  return policy;
}

/** Write a policy back as header text. */
export function formatPolicy(policy: Policy): string {
  return [...policy].map(([name, sources]) => [name, ...sources].join(" ")).join("; ");
}

/** The base64 SHA-256 of an inline element's text, as a CSP source. */
export function hashSource(text: string): string {
  return `'sha256-${createHash("sha256").update(text, "utf8").digest("base64")}'`;
}

function decode(value: string): string {
  return value
    .replaceAll("&quot;", '"')
    .replaceAll("&#39;", "'")
    .replaceAll("&#x27;", "'")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&amp;", "&");
}

const SPACE = /\s/;
const NAME_END = /[\s=/>]/;

/**
 * Read a tag's attributes as the HTML tokenizer does: names lowercased,
 * values unquoted and decoded. A scanner, not a regular expression, so no
 * input can make it backtrack.
 */
export function attributes(tag: string): Map<string, string> {
  const found = new Map<string, string>();
  let at = tag.search(/[\s/>]/);
  if (at < 0) return found;
  const skip = (pattern: RegExp): void => {
    while (at < tag.length && pattern.test(tag.charAt(at))) at += 1;
  };
  while (at < tag.length) {
    skip(/[\s/]/);
    if (at >= tag.length || tag.charAt(at) === ">") break;
    const start = at;
    at += 1;
    while (at < tag.length && !NAME_END.test(tag.charAt(at))) at += 1;
    const name = tag.slice(start, at).toLowerCase();
    skip(SPACE);
    let value = "";
    if (tag.charAt(at) === "=") {
      at += 1;
      skip(SPACE);
      const quote = tag.charAt(at);
      if (quote === '"' || quote === "'") {
        const end = tag.indexOf(quote, at + 1);
        const close = end < 0 ? tag.length : end;
        value = tag.slice(at + 1, close);
        at = close + 1;
      } else {
        const begin = at;
        while (at < tag.length && !/[\s>]/.test(tag.charAt(at))) at += 1;
        value = tag.slice(begin, at);
      }
    }
    if (!found.has(name)) found.set(name, decode(value));
  }
  return found;
}

function sameOrigin(url: string): boolean {
  return url.startsWith("/") && !url.startsWith("//");
}

/**
 * Check one policy against csp.config.ts: every directive present (beside
 * `omit`), nothing forbidden, and no source decision 9 does not allow.
 * Returns the problems found and the hashes each hashed directive holds.
 */
export function checkPolicy(
  policy: Policy,
  { omit = new Set<string>() }: { omit?: ReadonlySet<string> } = {},
): { problems: string[]; hashes: Map<string, string[]> } {
  const problems: string[] = [];
  const hashes = new Map<string, string[]>();
  for (const name of BASE.keys()) {
    if (!omit.has(name) && !policy.has(name)) problems.push(`${name} is missing`);
  }
  for (const [name, sources] of policy) {
    const allowed = PERMITTED.get(name);
    if (allowed === undefined || omit.has(name)) {
      problems.push(`${name} is not a directive of decision 9's policy`);
      continue;
    }
    const found: string[] = [];
    for (const source of sources) {
      if (FORBIDDEN.includes(source.toLowerCase())) {
        problems.push(`${name} holds ${source}`);
      } else if (HASHED.has(name) && HASH.test(source)) {
        found.push(source);
      } else if (!allowed.includes(source)) {
        problems.push(`${name} holds ${source}, which decision 9 does not allow`);
      }
    }
    for (const base of BASE.get(name) ?? []) {
      if (!sources.includes(base)) problems.push(`${name} lacks ${base}`);
    }
    if (HASHED.has(name)) hashes.set(name, found);
  }
  return { problems, hashes };
}

/** What one page asks of the policy, and what is wrong with it. */
export interface PageReport {
  problems: string[];
  hashes: Map<string, string[]>;
}

/** Check one built page: its own policy and everything it inlines. */
export function checkPage(html: string): PageReport {
  const problems: string[] = [];
  // Comments are never rendered, and script and style bodies are not markup.
  const markup = html.replace(/<!--[\s\S]*?-->/g, "");
  const scripts = [...markup.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)];
  const styles = [...markup.matchAll(/<style\b([^>]*)>([\s\S]*?)<\/style\s*>/gi)];
  const tags = markup
    .replace(/<script\b[^>]*>[\s\S]*?<\/script\s*>/gi, "<script>")
    .replace(/<style\b[^>]*>[\s\S]*?<\/style\s*>/gi, "<style>")
    .match(/<[a-zA-Z][^>]*>/g) ?? [];

  const metas = tags
    .map((tag) => attributes(tag))
    .filter((attrs) => attrs.get("http-equiv")?.toLowerCase() === "content-security-policy");
  let hashes = new Map<string, string[]>();
  if (metas.length !== 1) {
    problems.push(`the page has ${metas.length} <meta> policies, not one`);
  } else {
    const result = checkPolicy(parsePolicy(metas[0]?.get("content") ?? ""), { omit: HEADER_ONLY });
    problems.push(...result.problems.map((problem) => `its <meta> policy: ${problem}`));
    hashes = result.hashes;
  }

  for (const [, attrs, body = ""] of scripts) {
    const found = attributes(`<script ${attrs ?? ""}>`);
    const src = found.get("src");
    if (src !== undefined) {
      if (!sameOrigin(src)) problems.push(`a script loads from ${src}, another origin`);
      continue;
    }
    if (!EXECUTED.has((found.get("type") ?? "").toLowerCase())) continue;
    if (!hashes.get("script-src")?.includes(hashSource(body))) {
      problems.push(`an inline script (${hashSource(body)}) is not hashed in script-src`);
    }
  }
  for (const [, , body = ""] of styles) {
    if (!hashes.get("style-src")?.includes(hashSource(body))) {
      problems.push(`an inline style (${hashSource(body)}) is not hashed in style-src`);
    }
  }
  for (const tag of tags) {
    const found = attributes(tag);
    for (const [name, value] of found) {
      if (name === "style") problems.push(`an inline style attribute: ${tag.slice(0, 80)}`);
      if (/^on[a-z]+$/.test(name)) problems.push(`an event-handler attribute (${name})`);
      if (/^\s*javascript:/i.test(value)) problems.push(`a javascript: URL in ${name}`);
    }
    const rel = found.get("rel")?.toLowerCase().split(/\s+/) ?? [];
    const href = found.get("href");
    if (
      tag.toLowerCase().startsWith("<link") &&
      href !== undefined &&
      (rel.includes("stylesheet") || rel.includes("modulepreload") || rel.includes("preload")) &&
      !sameOrigin(href)
    ) {
      problems.push(`a ${rel.join(" ")} link loads from ${href}, another origin`);
    }
  }
  return { problems, hashes };
}

/** The header policy: decision 9's directives with every page's hashes. */
export function headerPolicy(hashes: ReadonlyMap<string, ReadonlySet<string>>): Policy {
  const policy: Policy = new Map();
  for (const [name, sources] of BASE) {
    policy.set(name, [...sources, ...[...(hashes.get(name) ?? [])].sort()]);
  }
  return policy;
}

/** The _headers file: the policy and security headers on every path, and caching. */
export function renderHeaders(policy: Policy): string {
  const lines = ["/*", `  Content-Security-Policy: ${formatPolicy(policy)}`];
  for (const [name, value] of Object.entries(SECURITY_HEADERS)) lines.push(`  ${name}: ${value}`);
  lines.push("/_astro/*", `  Cache-Control: ${IMMUTABLE}`);
  return `${lines.join("\n")}\n`;
}

/** Check a _headers file against Cloudflare's limits. */
export function checkHeaders(text: string): string[] {
  const problems: string[] = [];
  const lines = text.split("\n");
  lines.forEach((line, index) => {
    if (line.length > MAX_LINE) {
      problems.push(`_headers line ${index + 1} has ${line.length} characters, over ${MAX_LINE}`);
    }
  });
  const rules = lines.filter((line) => line.length > 0 && !/^\s/.test(line) && !line.startsWith("#"));
  if (rules.length > MAX_RULES) problems.push(`_headers has ${rules.length} rules, over ${MAX_RULES}`);
  return problems;
}

function walk(root: string, directory = root): string[] {
  // The build output directory only: every path comes from readdirSync.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? walk(root, path) : [relative(root, path).split(sep).join("/")];
  });
}

/** The outcome of checking a build. */
export interface BuildReport {
  problems: string[];
  pages: number;
  headers: string;
}

/** Check a build output directory and return the _headers text it needs. */
export function checkBuild(dist: string): BuildReport {
  const problems: string[] = [];
  const files = walk(dist);
  for (const name of SERVER_OUTPUT) {
    if (files.some((file) => file === name || file.startsWith(`${name}/`))) {
      problems.push(`${name} in the build output: a server-rendered route; the site is static only`);
    }
  }
  if (files.includes("_headers")) {
    problems.push("dist/_headers already exists: headers come from csp.config.ts, never public/");
  }
  const pages = files.filter((file) => file.endsWith(".html"));
  if (pages.length === 0) problems.push("the build wrote no page");
  const union = new Map<string, Set<string>>([...HASHED].map((name) => [name, new Set<string>()]));
  for (const page of pages) {
    // A path walk() found under the build output.
    // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
    const report = checkPage(readFileSync(join(dist, page), "utf8"));
    problems.push(...report.problems.map((problem) => `${page}: ${problem}`));
    for (const [name, hashes] of report.hashes) {
      for (const hash of hashes) union.get(name)?.add(hash);
    }
  }
  const policy = headerPolicy(union);
  const header = checkPolicy(policy);
  problems.push(...header.problems.map((problem) => `the header policy: ${problem}`));
  const headers = renderHeaders(policy);
  problems.push(...checkHeaders(headers));
  return { problems, pages: pages.length, headers };
}

function main(): number {
  const dist = fileURLToPath(new URL("../dist", import.meta.url));
  // The build output directory, a fixed path.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  if (!existsSync(dist)) {
    process.stderr.write("headers: no dist/ to check; run `npm run build`\n");
    return 1;
  }
  const report = checkBuild(dist);
  if (report.problems.length > 0) {
    process.stderr.write(
      `headers: the build breaks decision 9's policy (ADR-0013):\n${report.problems
        .map((problem) => `  ${problem}`)
        .join("\n")}\n`,
    );
    return 1;
  }
  // The build output directory, a fixed path.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  writeFileSync(join(dist, "_headers"), report.headers);
  const longest = Math.max(...report.headers.split("\n").map((line) => line.length));
  process.stdout.write(
    `headers: ${report.pages} pages checked; dist/_headers written (longest line ${longest} of ${MAX_LINE})\n`,
  );
  return 0;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  process.exit(main());
}
