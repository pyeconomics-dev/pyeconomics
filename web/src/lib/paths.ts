// web/src/lib/paths.ts
// The site's addresses (ADR-0013 decision 2): the production origin, and each
// domain's and model's page, derived from the permanent model ids. It imports
// nothing, so the post-build scripts (scripts/indexing.ts) run it in Node as
// the pages use it in Astro.

/** The production origin: canonical links, the sitemap and social images. */
export const ORIGIN = "https://pyeconomics.dev";

const ID = /^([a-z][a-z0-9_]*)\.([a-z][a-z0-9_]*)$/;
const PATH = /^\/models\/([a-z][a-z0-9-]*)\/([a-z][a-z0-9-]*)\/$/;

/** A domain's path segment: every underscore a hyphen. */
export function domainSegment(domain: string): string {
  return domain.replaceAll("_", "-");
}

/** A domain's index page. */
export function domainPath(domain: string): string {
  return `/models/${domainSegment(domain)}/`;
}

/** A domain's name for a reader: `fixed_income` is "Fixed income". */
export function domainTitle(domain: string): string {
  const words = domain.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/**
 * A model's page, from its id `<domain>.<name>` with every underscore a
 * hyphen (decision 2). Ids hold no hyphen, so the mapping is a bijection.
 */
export function modelPath(id: string): string {
  const match = ID.exec(id);
  if (!match) throw new Error(`${id} is not a model id of the form <domain>.<name>`);
  return `/models/${domainSegment(match[1] ?? "")}/${(match[2] ?? "").replaceAll("_", "-")}/`;
}

/** The model id a model page's path names, or null for any other path. */
export function idOfPath(path: string): string | null {
  const match = PATH.exec(path);
  if (!match) return null;
  return `${(match[1] ?? "").replaceAll("-", "_")}.${(match[2] ?? "").replaceAll("-", "_")}`;
}
