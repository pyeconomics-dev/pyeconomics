// web/src/lib/pages.ts
// Every page the site generates from its data, with the title and description
// its social image is drawn from (src/pages/og/[...slug].ts), and the path of
// each page's social image. The pages themselves are the routes under
// src/pages/; tests/site/ holds this list equal to what the build wrote.
import { LEGAL_INDEX, LEGAL_PAGES } from "@/lib/legal";
import { DOMAINS, describe, domainPath, modelPath, type Domain } from "@/lib/models";
import { DATA_PATH, conceptPath } from "@/lib/paths";
import { conceptData, domains, problemData, registryData, type ConceptEntry } from "@/lib/site-data";

/** One generated page. */
export interface SitePage {
  path: string;
  title: string;
  description: string;
}

/** The home page's title and description, shared with its route. */
export const HOME = {
  title: "pyeconomics",
  description:
    "Open-source economics and finance models with cited formulas and tested values, and economic data from its originators.",
};

/** The models index's title and description. */
export const MODELS_INDEX = {
  title: "Models",
  description:
    "Every pyeconomics model, filtered by domain, syllabus topic, evidence, cost class, data needs and tag.",
};

/** The search page's title and description. */
export const SEARCH = {
  title: "Search",
  description: "Search every pyeconomics model, domain and problem type, in your browser.",
};

/** The coverage matrix's title and description. */
export const COVERAGE = {
  title: "Coverage",
  description:
    "What the pyeconomics catalog covers: each syllabus topic area and the models that implement it, and each domain.",
};

/** The data explorer's title and description (Phase 5 Step 9). */
export const DATA_INDEX = {
  title: "Data",
  description:
    "The economic series pyeconomics models read: search the catalog, see each series' sources and licence, and chart and download those this site serves.",
};

/** The newsletter page's title and description (Phase 5 Step 15). */
export const NEWSLETTER = {
  title: "Newsletter",
  description: "New pyeconomics models, data sources and releases, by email a few times a year; confirmed by email, no tracking.",
};

/** The Pro preview's title and description (Phase 5 Step 15). */
export const PRO = {
  title: "Pro preview",
  description:
    "A preview of a possible paid pyeconomics Pro tier, with planned features and indicative prices. Pro does not exist yet and nothing is sold.",
};

/** A concept page's description: its definition, its unit and frequency. */
export function conceptDescription(concept: ConceptEntry): string {
  const unit = concept.unit ?? concept.unit_kind;
  const facts = [unit, concept.frequency.replaceAll("_", " ")].filter(Boolean).join(", ");
  return `${concept.definition}${facts ? ` (${facts})` : ""}`;
}

/** The problem types index's title and description. */
export const PROBLEMS_INDEX = {
  title: "Problem types",
  description:
    "Every problem type a pyeconomics surface reports, with its HTTP status, exit code, meaning and what to do.",
};

/** A domain index's description; a planned section says when its models arrive. */
export function domainDescription(domain: Domain, count: number): string {
  if (count === 0 && domain.planned) {
    return `${domain.title}: a planned pyeconomics section, whose models arrive in ${domain.planned}.`;
  }
  return `${domain.title}: ${String(count)} pyeconomics ${count === 1 ? "model" : "models"}, each with its formula, variables, evidence and citations.`;
}

/** Every page the site generates, home first. */
export function sitePages(): SitePage[] {
  const pages: SitePage[] = [{ path: "/", ...HOME }, { path: "/models/", ...MODELS_INDEX }];
  const counts = new Map(domains());
  for (const domain of DOMAINS) {
    pages.push({
      path: domainPath(domain.id),
      title: domain.title,
      description: domainDescription(domain, counts.get(domain.id) ?? 0),
    });
  }
  for (const model of registryData.models) {
    pages.push({ path: modelPath(model.id), title: model.title, description: describe(model) });
  }
  pages.push({ path: DATA_PATH, ...DATA_INDEX });
  for (const concept of conceptData) {
    pages.push({ path: conceptPath(concept.id), title: concept.title, description: conceptDescription(concept) });
  }
  pages.push({ path: "/search/", ...SEARCH }, { path: "/coverage/", ...COVERAGE });
  pages.push({ path: "/newsletter/", ...NEWSLETTER }, { path: "/pro/", ...PRO });
  for (const page of [LEGAL_INDEX, ...LEGAL_PAGES]) {
    pages.push({ path: page.path, title: page.title, description: page.description });
  }
  pages.push({ path: "/problems/", ...PROBLEMS_INDEX });
  for (const problem of problemData) {
    pages.push({ path: `/problems/${problem.slug}/`, title: problem.title, description: problem.meaning });
  }
  return pages;
}

/** The social image of the page at `path`: `/` is `/og/index.png`. */
export function ogImagePath(path: string): string {
  const trimmed = path.replace(/^\/|\/$/g, "");
  return `/og/${trimmed === "" ? "index" : trimmed}.png`;
}
