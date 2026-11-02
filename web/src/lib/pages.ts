// web/src/lib/pages.ts
// Every page the site generates from its data, with the title and description
// its social image is drawn from (src/pages/og/[...slug].ts), and the path of
// each page's social image. The pages themselves are the routes under
// src/pages/; tests/site/ holds this list equal to what the build wrote.
import { describe, domainPath, domainTitle, modelPath } from "@/lib/models";
import { domains, problemData, registryData } from "@/lib/site-data";

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
  description: "Every pyeconomics model by domain, each with its formula, variables, evidence and citations.",
};

/** The problem types index's title and description. */
export const PROBLEMS_INDEX = {
  title: "Problem types",
  description:
    "Every problem type a pyeconomics surface reports, with its HTTP status, exit code, meaning and what to do.",
};

/** A domain index's description. */
export function domainDescription(domain: string, count: number): string {
  return `${domainTitle(domain)}: ${count} pyeconomics ${count === 1 ? "model" : "models"}, each with its formula, variables, evidence and citations.`;
}

/** Every page the site generates, home first. */
export function sitePages(): SitePage[] {
  const pages: SitePage[] = [{ path: "/", ...HOME }, { path: "/models/", ...MODELS_INDEX }];
  for (const [domain, count] of domains()) {
    pages.push({ path: domainPath(domain), title: domainTitle(domain), description: domainDescription(domain, count) });
  }
  for (const model of registryData.models) {
    pages.push({ path: modelPath(model.id), title: model.title, description: describe(model) });
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
