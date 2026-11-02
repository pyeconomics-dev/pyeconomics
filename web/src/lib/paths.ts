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

/** One of the site's model sections. */
export interface Domain {
  /** The registry's domain: a model id's first part. */
  id: string;
  /** The section's name for a reader. */
  title: string;
  /** The phase that brings a planned section its first models, or null. */
  planned: string | null;
}

/**
 * The fifteen domain sections, in ROADMAP §4 7.2's order (ADR-0013 decision
 * 10). `micro` and `alternatives` are planned: their pages say which phase
 * brings their models and link the coverage matrix. A model whose domain is
 * not listed fails the build (domainTitle()), so a new domain joins here.
 */
export const DOMAINS: readonly Domain[] = [
  { id: "foundations", title: "Foundations", planned: null },
  { id: "econometrics", title: "Econometrics", planned: null },
  { id: "macro", title: "Macroeconomics", planned: null },
  { id: "international", title: "International", planned: null },
  { id: "micro", title: "Microeconomics", planned: "Phase 7" },
  { id: "accounting", title: "Accounting", planned: null },
  { id: "corporate", title: "Corporate finance", planned: null },
  { id: "equity", title: "Equity", planned: null },
  { id: "fixed_income", title: "Fixed income", planned: null },
  { id: "derivatives", title: "Derivatives", planned: null },
  { id: "alternatives", title: "Alternatives", planned: "Phase 7" },
  { id: "portfolio", title: "Portfolio", planned: null },
  { id: "asset_pricing", title: "Asset pricing", planned: null },
  { id: "risk", title: "Risk", planned: null },
  { id: "performance", title: "Performance", planned: null },
];

/** The section of a registry domain; an unlisted domain is an error. */
export function domainOf(domain: string): Domain {
  const found = DOMAINS.find((entry) => entry.id === domain);
  if (!found) {
    throw new Error(`${domain} is not one of the domains in src/lib/paths.ts DOMAINS (ROADMAP §4 7.2): add it there`);
  }
  return found;
}

/** A domain's name for a reader: `fixed_income` is "Fixed income". */
export function domainTitle(domain: string): string {
  return domainOf(domain).title;
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
