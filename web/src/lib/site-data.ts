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
import surfaces from "@/data/generated/surfaces.json?raw";
import syllabi from "@/data/generated/syllabi.json?raw";
import type { HostedProfile } from "@/lib/calculator";

/** The registry format this site reads (`REGISTRY_FORMAT`). */
export const REGISTRY_FORMAT = 1;
/** The format of problems.json, sources.json, concepts.json, surfaces.json and syllabi.json. */
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
  /** What the problem means (surfaces/problem_guide.py). */
  meaning: string;
  /** What to do about it. */
  action: string;
  /** The local-mode command, where the problem points to local mode. */
  local_command: string | null;
}

/** Where a model is reached beside its page. */
export interface SurfaceEntry {
  id: string;
  /** The REST API's run route. */
  rest: string;
  methods: string[];
  /** The MCP tool of its own, for a headline model. */
  mcp_tool: string | null;
  /** The command that runs it. */
  cli: string;
  /** Each data profile's bound fields and whether hosted mode can serve them. */
  profiles: HostedProfile[];
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
  /** Whether hosted mode may use one of its candidates. */
  hosted: boolean;
  /** Whether the hosted site serves it from the snapshot (data/snapshots/set.py). */
  snapshot: boolean;
  /** The parameters a read needs, such as an SEP meeting, each with an example. */
  parameters: { name: string; example: string }[];
  /** Whether a read needs both a start and an end date. */
  needs_window: boolean;
  /** The command that reads it locally (surfaces/budgets.py local_data_command). */
  local_command: string;
}

/** One level of a syllabus. */
export interface SyllabusLevel {
  level: number;
  title: string;
  url: string;
}

/** One topic area of one level: a neutral id, its title and its issuer's page. */
export interface SyllabusTopic {
  id: string;
  level: number;
  title: string;
  url: string;
}

/** One syllabus crosswalk from syllabi/ (ADR-0013 decision 12). */
export interface SyllabusEntry {
  /** A neutral id: no mark. */
  id: string;
  /** The displayed name, with the issuer's mark as an adjective. */
  title: string;
  issuer: string;
  site: string;
  url: string;
  checked: string;
  levels: SyllabusLevel[];
  topics: SyllabusTopic[];
  /** Per model id, the topic ids it implements. */
  models: Record<string, string[]>;
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

const problemDocument = parse<{
  format: number;
  problems: ProblemEntry[];
  exit_codes: Record<string, string>;
}>(problems, "problems.json", SITE_DATA_FORMAT);

/** The error table, one entry per slug. */
export const problemData = problemDocument.problems;

/** What each command-line exit code means, by code. */
export const exitCodes: ReadonlyMap<number, string> = new Map(
  Object.entries(problemDocument.exit_codes).map(([code, meaning]) => [Number(code), meaning]),
);

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

/** Where each model is reached beside its page, sorted by id. */
export const surfaceData = parse<{ format: number; models: SurfaceEntry[] }>(
  surfaces,
  "surfaces.json",
  SITE_DATA_FORMAT,
).models;

/** Every syllabus crosswalk, sorted by id. */
export const syllabusData = parse<{ format: number; syllabi: SyllabusEntry[] }>(
  syllabi,
  "syllabi.json",
  SITE_DATA_FORMAT,
).syllabi;

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
