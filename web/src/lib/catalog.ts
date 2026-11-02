// web/src/lib/catalog.ts
// What the catalog's navigation is built from, at build time, out of the
// registry and syllabi/ (Phase 5 Step 7; ADR-0013 decisions 10 and 12): each
// model's syllabus topics, its filter values and the facets /models/ offers,
// its related models, and the coverage matrix /coverage/ publishes. Pure
// functions over the site data: nothing here reads a file or reaches the
// browser (the filter island receives FilterModel and Facet values as props).
import { slug, type Facet, type FilterKey, type FilterModel, type FilterOption } from "@/lib/filters";
import { DOMAINS, domainSegment, domainTitle, modelPath, type Domain } from "@/lib/paths";
import { COST, EVIDENCE, type Model } from "@/lib/registry-schema";
import type { SyllabusEntry, SyllabusLevel, SyllabusTopic } from "@/lib/site-data";

/** What the catalog reads of a model. */
export type CatalogModel = Pick<
  Model,
  "id" | "title" | "summary" | "domain" | "evidence" | "cost" | "tags" | "bindings" | "references"
>;

/** One syllabus topic a model implements. */
export interface ModelTopic {
  syllabus: SyllabusEntry;
  level: SyllabusLevel;
  topic: SyllabusTopic;
}

/** A model's topics in every syllabus, each syllabus's in its file's order. */
export function topicsOf(id: string, syllabi: readonly SyllabusEntry[]): ModelTopic[] {
  return syllabi.flatMap((syllabus) => {
    const named = new Set(new Map(Object.entries(syllabus.models)).get(id) ?? []);
    return syllabus.topics
      .filter((topic) => named.has(topic.id))
      .map((topic) => ({ syllabus, level: levelOf(syllabus, topic.level), topic }));
  });
}

/** A syllabus's level; a topic naming an undeclared level is an error (the loader refuses one). */
export function levelOf(syllabus: SyllabusEntry, level: number): SyllabusLevel {
  const found = syllabus.levels.find((entry) => entry.level === level);
  if (!found) throw new Error(`${syllabus.id} has no level ${String(level)}`);
  return found;
}

/** Whether a model reads data through bindings or needs none. */
export function dataNeeds(model: Pick<Model, "bindings">): "free" | "bound" {
  return model.bindings.length > 0 ? "bound" : "free";
}

/** How a result and the data filter word a model's data needs. */
export function dataLabel(needs: "free" | "bound"): string {
  return needs === "bound" ? "Reads data" : "Data-free";
}

function capitalized(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

/** A domain's position in ROADMAP §4 7.2's order. */
function domainRank(domain: string): number {
  return DOMAINS.findIndex((entry) => entry.id === domain);
}

/** Models in the sections' order, then by title, then by id. */
export function catalogOrder<T extends Pick<Model, "id" | "title" | "domain">>(models: readonly T[]): T[] {
  return [...models].sort(
    (a, b) =>
      domainRank(a.domain) - domainRank(b.domain) || a.title.localeCompare(b.title) || a.id.localeCompare(b.id),
  );
}

/**
 * The query values of the syllabus filters. One syllabus is seeded, so a
 * level's value is its number and a topic's is its id; a second syllabus
 * needs a syllabus filter first, and until it has one the build refuses it.
 */
function onlySyllabus(syllabi: readonly SyllabusEntry[]): SyllabusEntry | null {
  if (syllabi.length > 1) {
    throw new Error("the /models/ filters read one syllabus: add a syllabus filter before a second one (src/lib/catalog.ts)");
  }
  return syllabi[0] ?? null;
}

/** Each model's filter values and the words its result shows, in catalog order. */
export function filterModels(models: readonly CatalogModel[], syllabi: readonly SyllabusEntry[]): FilterModel[] {
  onlySyllabus(syllabi);
  return catalogOrder(models).map((model) => {
    const topics = topicsOf(model.id, syllabi);
    const data = dataNeeds(model);
    return {
      id: model.id,
      title: model.title,
      summary: model.summary,
      path: modelPath(model.id),
      domainTitle: domainTitle(model.domain),
      evidenceLabel: model.evidence ? capitalized(model.evidence) : "Not declared",
      costLabel: model.cost ? capitalized(model.cost) : "Not declared",
      dataLabel: dataLabel(data),
      values: new Map<FilterKey, string[]>([
        ["domain", [domainSegment(model.domain)]],
        ["level", [...new Set(topics.map(({ topic }) => String(topic.level)))]],
        ["topic", topics.map(({ topic }) => topic.id)],
        ["evidence", model.evidence ? [model.evidence] : []],
        ["cost", model.cost ? [model.cost] : []],
        ["data", [data]],
        ["tag", [...new Set(model.tags.map(slug))]],
      ]),
    };
  });
}

/**
 * The facets /models/ offers, each option one at least one model holds, in a
 * reader's order: domains in the sections' order, levels and topics in the
 * syllabus's, evidence and cost in their declared order, tags by name.
 */
export function facets(models: readonly CatalogModel[], syllabi: readonly SyllabusEntry[]): Facet[] {
  const syllabus = onlySyllabus(syllabi);
  const held = (key: FilterKey): Set<string> =>
    new Set(filterModels(models, syllabi).flatMap((model) => model.values.get(key) ?? []));
  const keep = (key: FilterKey, options: FilterOption[]): FilterOption[] => {
    const values = held(key);
    return options.filter((option) => values.has(option.value));
  };
  const tags = new Map<string, string>();
  for (const model of models) for (const tag of model.tags) if (!tags.has(slug(tag))) tags.set(slug(tag), tag);
  const levels = syllabus?.levels ?? [];
  const topics = syllabus?.topics ?? [];
  return [
    {
      key: "domain",
      label: "Domain",
      options: keep(
        "domain",
        DOMAINS.map((domain) => ({ value: domainSegment(domain.id), label: domain.title })),
      ),
    },
    {
      key: "level",
      label: "Syllabus level",
      options: keep(
        "level",
        levels.map((level) => ({ value: String(level.level), label: level.title })),
      ),
    },
    {
      key: "topic",
      label: "Syllabus topic",
      options: keep(
        "topic",
        topics.map((topic) => ({
          value: topic.id,
          label: `${syllabus ? levelOf(syllabus, topic.level).title : ""} · ${topic.title}`,
        })),
      ),
    },
    {
      key: "evidence",
      label: "Evidence status",
      options: keep(
        "evidence",
        EVIDENCE.map((value) => ({ value, label: capitalized(value) })),
      ),
    },
    {
      key: "cost",
      label: "Cost class",
      options: keep(
        "cost",
        COST.map((value) => ({ value, label: capitalized(value) })),
      ),
    },
    {
      key: "data",
      label: "Data needs",
      options: keep(
        "data",
        (["free", "bound"] as const).map((value) => ({ value, label: dataLabel(value) })),
      ),
    },
    {
      key: "tag",
      label: "Tag",
      options: [...tags]
        .map(([value, label]) => ({ value, label }))
        .sort((a, b) => a.label.localeCompare(b.label) || a.value.localeCompare(b.value)),
    },
  ];
}

/** A citation's identity: its DOI, else its URL, else its text. */
function referenceKey(reference: CatalogModel["references"][number]): string {
  return reference.doi ? `doi:${reference.doi.toLowerCase()}` : (reference.url ?? reference.citation);
}

function shared<T>(a: readonly T[], b: ReadonlySet<T>): number {
  return new Set(a.filter((item) => b.has(item))).size;
}

/**
 * Up to `limit` related models, ranked by shared syllabus topics, then shared
 * tags, then shared citations, then the same domain, then id: a deterministic
 * order. A model that shares nothing is never related.
 */
export function relatedModels<T extends CatalogModel>(
  model: CatalogModel,
  models: readonly T[],
  syllabi: readonly SyllabusEntry[],
  limit = 4,
): T[] {
  const topics = new Set(topicsOf(model.id, syllabi).map(({ syllabus, topic }) => `${syllabus.id}/${topic.id}`));
  const tags = new Set(model.tags.map(slug));
  const references = new Set(model.references.map(referenceKey));
  const scored = models
    .filter((other) => other.id !== model.id)
    .map((other) => ({
      other,
      score: [
        shared(
          topicsOf(other.id, syllabi).map(({ syllabus, topic }) => `${syllabus.id}/${topic.id}`),
          topics,
        ),
        shared(other.tags.map(slug), tags),
        shared(other.references.map(referenceKey), references),
        other.domain === model.domain ? 1 : 0,
      ],
    }))
    .filter(({ score }) => score.some((part) => part > 0));
  scored.sort((a, b) => {
    for (let index = 0; index < a.score.length; index += 1) {
      const difference = (b.score.at(index) ?? 0) - (a.score.at(index) ?? 0);
      if (difference !== 0) return difference;
    }
    return a.other.id.localeCompare(b.other.id);
  });
  return scored.slice(0, limit).map(({ other }) => other);
}

/** A model as the coverage matrix links it. */
export interface CoverageModel {
  id: string;
  title: string;
  path: string;
}

/** One topic of the matrix and the models that implement it (none: Phase 7's). */
export interface CoverageTopic {
  topic: SyllabusTopic;
  models: CoverageModel[];
}

/** One level of one syllabus. */
export interface CoverageLevel {
  level: SyllabusLevel;
  topics: CoverageTopic[];
}

/** One syllabus's matrix and its totals. */
export interface CoverageSyllabus {
  syllabus: SyllabusEntry;
  levels: CoverageLevel[];
  covered: number;
  total: number;
  /** Models the syllabus maps to at least one topic. */
  mapped: number;
}

/** One domain section and how many models it holds; a planned one holds none yet. */
export interface CoverageDomain {
  domain: Domain;
  count: number;
}

/** The coverage matrix: each syllabus's topics by level, and the domain sections. */
export interface Coverage {
  syllabi: CoverageSyllabus[];
  domains: CoverageDomain[];
  models: number;
}

/**
 * The coverage matrix (ADR-0013 decision 12) of the registry against the
 * syllabi: every topic with the models that implement it, by title. Every
 * registered model meets the definition of done, so each is verified; a topic
 * no model covers is planned for Phase 7.
 */
export function coverage(models: readonly CatalogModel[], syllabi: readonly SyllabusEntry[]): Coverage {
  const byId = new Map(models.map((model) => [model.id, model]));
  const covered = syllabi.map((syllabus) => {
    const levels = syllabus.levels.map((level) => ({
      level,
      topics: syllabus.topics
        .filter((topic) => topic.level === level.level)
        .map((topic) => ({
          topic,
          models: Object.entries(syllabus.models)
            .filter(([, topics]) => topics.includes(topic.id))
            .map(([id]) => byId.get(id))
            .filter((model): model is CatalogModel => model !== undefined)
            .map((model) => ({ id: model.id, title: model.title, path: modelPath(model.id) }))
            .sort((a, b) => a.title.localeCompare(b.title) || a.id.localeCompare(b.id)),
        })),
    }));
    const topics = levels.flatMap((level) => level.topics);
    return {
      syllabus,
      levels,
      covered: topics.filter((topic) => topic.models.length > 0).length,
      total: topics.length,
      mapped: Object.keys(syllabus.models).filter((id) => byId.has(id)).length,
    };
  });
  return {
    syllabi: covered,
    domains: DOMAINS.map((domain) => ({
      domain,
      count: models.filter((model) => model.domain === domain.id).length,
    })),
    models: models.length,
  };
}
