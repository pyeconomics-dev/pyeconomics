// web/src/lib/site-data.ts
// The site's build data, read from the files scripts/web/export_site_data.py
// writes into src/data/generated/ (ADR-0013 decision 2). Pages read the
// registry, the error table, the sources and the concepts only through this
// module, at build time; nothing here reaches the browser unless an island
// imports it. The files are imported as text and parsed here, so the
// type checker never infers a type from megabytes of JSON.
import concepts from "@/data/generated/concepts.json?raw";
import problems from "@/data/generated/problems.json?raw";
import registry from "@/data/generated/registry.json?raw";
import sources from "@/data/generated/sources.json?raw";

/** The registry format this site reads (`REGISTRY_FORMAT`). */
export const REGISTRY_FORMAT = 1;
/** The format of problems.json, sources.json and concepts.json. */
export const SITE_DATA_FORMAT = 1;

/** One model, as registry.json describes it; later steps read more keys. */
export interface ModelEntry {
  id: string;
  title: string;
  summary: string;
  domain: string;
  formula: string[];
  [key: string]: unknown;
}

export interface Registry {
  format: number;
  pyeconomics: string;
  models: ModelEntry[];
}

export interface ProblemEntry {
  slug: string;
  title: string;
  status: number;
  exit_code: number;
  type: string;
  error: string;
}

export interface SourceEntry {
  id: string;
  name: string;
  licence: string;
  hosted: boolean;
  terms_url: string;
  terms_checked: string;
  attribution: string;
  notice: string | null;
  llm_use: string;
  storage: string;
  key_variable: string | null;
  key_required: boolean;
  extra: string | null;
}

export interface CandidateEntry {
  provider: string;
  series: string;
  tier: string;
  licence: string | null;
  hosted: boolean;
  vintages: boolean;
  transforms: string[];
  derived_from: string[];
}

export interface ConceptEntry {
  id: string;
  title: string;
  definition: string;
  section: string;
  shape: string;
  unit_kind: string | null;
  unit: string | null;
  frequency: string;
  seasonal_adjustment: string;
  candidates: CandidateEntry[];
  hosted: boolean;
}

function parse<T extends { format: number }>(text: string, name: string, format: number): T {
  const document = JSON.parse(text) as T;
  if (document.format !== format) {
    throw new Error(
      `${name} has format ${String(document.format)}, but this site reads format ${String(format)}: ` +
        "run `npm run data` with the matching pyeconomics.",
    );
  }
  return document;
}

/** Every model, sorted by id. */
export const registryData = parse<Registry>(registry, "registry.json", REGISTRY_FORMAT);

/** The error table, one entry per slug. */
export const problemData = parse<{ format: number; problems: ProblemEntry[] }>(
  problems,
  "problems.json",
  SITE_DATA_FORMAT,
).problems;

/** Every provider, sorted by id. */
export const sourceData = parse<{ format: number; sources: SourceEntry[] }>(
  sources,
  "sources.json",
  SITE_DATA_FORMAT,
).sources;

/** Every catalog concept, sorted by id. */
export const conceptData = parse<{ format: number; concepts: ConceptEntry[] }>(
  concepts,
  "concepts.json",
  SITE_DATA_FORMAT,
).concepts;

/** The pyeconomics version the data was exported from. */
export const version = registryData.pyeconomics;

/** The model domains, sorted, each with its number of models. */
export function domains(models: readonly ModelEntry[] = registryData.models): [string, number][] {
  const counts = new Map<string, number>();
  for (const model of models) {
    counts.set(model.domain, (counts.get(model.domain) ?? 0) + 1);
  }
  return [...counts.entries()].sort(([a], [b]) => a.localeCompare(b));
}
