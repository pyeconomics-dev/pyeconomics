// web/tests/unit/catalog.test.ts
// The catalog's navigation held to the registry and the syllabus seed
// (src/lib/catalog.ts): every facet option counts exactly the models the
// registry and syllabi/ give it, every query value is neutral, related models
// are deterministic and share something, and the coverage matrix's counts are
// the seed's.
import { describe, expect, it } from "vitest";

import { catalogOrder, coverage, facets, filterModels, relatedModels, topicsOf } from "@/lib/catalog";
import { applyFilters, optionCounts, slug, type FilterKey } from "@/lib/filters";
import { DOMAINS, domainSegment } from "@/lib/paths";
import { parseModels } from "@/lib/registry-schema";
import { registryData, syllabusData } from "@/lib/site-data";

const MODELS = parseModels(registryData);
const SYLLABUS = syllabusData[0];
const SEED = new Map(Object.entries(SYLLABUS?.models ?? {}));

describe("the seed", () => {
  it("maps every registered model, and only registered models", () => {
    expect(syllabusData).toHaveLength(1);
    expect([...SEED.keys()].sort()).toEqual(MODELS.map((model) => model.id).sort());
  });

  it("holds neutral ids and short names only", () => {
    for (const syllabus of syllabusData) {
      expect(syllabus.id).not.toMatch(/cfa/i);
      for (const topic of syllabus.topics) {
        expect(topic.id).not.toMatch(/cfa/i);
        expect(topic.title.length).toBeLessThanOrEqual(40);
        expect(topic.url.startsWith(syllabus.site)).toBe(true);
      }
    }
  });

  it("gives each model its topics in the file's order", () => {
    const topics = topicsOf("asset_pricing.factor_regression", syllabusData).map(({ topic }) => topic.id);
    expect(topics).toEqual(["l1-equities", "l1-portfolio-construction", "l2-quantitative-methods", "l2-portfolio-construction"]);
    expect(topicsOf("no.such_model", syllabusData)).toEqual([]);
  });
});

describe("the filters", () => {
  const listed = filterModels(MODELS, syllabusData);
  const offered = facets(MODELS, syllabusData);

  it("list every model once, in the sections' order", () => {
    expect(listed.map((model) => model.id)).toEqual(catalogOrder(MODELS).map((model) => model.id));
    expect(new Set(listed.map((model) => model.id)).size).toBe(MODELS.length);
    const ranks = listed.map((model) => DOMAINS.findIndex((domain) => domainSegment(domain.id) === model.values.get("domain")?.[0]));
    expect(ranks).toEqual([...ranks].sort((a, b) => a - b));
  });

  it("count each option exactly as the registry and the seed do", () => {
    const expected = (key: FilterKey, value: string): number =>
      MODELS.filter((model) => {
        const topics = (SEED.get(model.id) ?? []).filter((id) => SYLLABUS?.topics.some((topic) => topic.id === id));
        switch (key) {
          case "domain":
            return domainSegment(model.domain) === value;
          case "level":
            return topics.some((id) => SYLLABUS?.topics.find((topic) => topic.id === id)?.level === Number(value));
          case "topic":
            return topics.includes(value);
          case "evidence":
            return model.evidence === value;
          case "cost":
            return model.cost === value;
          case "data":
            return (model.bindings.length > 0 ? "bound" : "free") === value;
          default:
            return model.tags.some((tag) => slug(tag) === value);
        }
      }).length;
    for (const facet of offered) {
      const counts = optionCounts(listed, new Map(), facet.key);
      expect(facet.options.length, facet.key).toBeGreaterThan(0);
      for (const option of facet.options) {
        const count = expected(facet.key, option.value);
        expect(count, `${facet.key}=${option.value}`).toBeGreaterThan(0);
        expect(counts.get(option.value), `${facet.key}=${option.value}`).toBe(count);
        expect(applyFilters(listed, new Map([[facet.key, option.value]]))).toHaveLength(count);
      }
    }
  });

  it("offer every populated domain and every mapped topic, and only neutral values", () => {
    const options = new Map(offered.map((facet) => [facet.key, facet.options.map((option) => option.value)]));
    expect(options.get("domain")).toEqual(
      DOMAINS.filter((domain) => MODELS.some((model) => model.domain === domain.id)).map((domain) => domainSegment(domain.id)),
    );
    const mapped = new Set([...SEED.values()].flat());
    expect(options.get("topic")).toEqual(SYLLABUS?.topics.filter((topic) => mapped.has(topic.id)).map((topic) => topic.id));
    expect(options.get("level")).toEqual(["1", "2", "3"]);
    expect(options.get("data")).toEqual(["free", "bound"]);
    for (const values of options.values()) {
      for (const value of values) {
        expect(value).toMatch(/^[a-z0-9-]+$/);
        expect(value).not.toMatch(/^-|-$|--/);
        expect(value).not.toMatch(/cfa/i);
      }
    }
  });

  it("refuse a second syllabus until a syllabus filter exists", () => {
    const second = { ...syllabusData[0], id: "other-2027" } as (typeof syllabusData)[number];
    expect(() => facets(MODELS, [...syllabusData, second])).toThrow(/syllabus filter/);
  });
});

describe("related models", () => {
  it("are at most four, never the model itself, each sharing something, in a fixed order", () => {
    for (const model of MODELS) {
      const related = relatedModels(model, MODELS, syllabusData);
      expect(related.length).toBeLessThanOrEqual(4);
      expect(related.map((other) => other.id)).not.toContain(model.id);
      expect(relatedModels(model, [...MODELS].reverse(), syllabusData).map((other) => other.id)).toEqual(
        related.map((other) => other.id),
      );
      const topics = new Set(SEED.get(model.id));
      for (const other of related) {
        const shares =
          (SEED.get(other.id) ?? []).some((id) => topics.has(id)) ||
          other.tags.some((tag) => model.tags.map(slug).includes(slug(tag))) ||
          other.domain === model.domain ||
          other.references.some((reference) =>
            model.references.some(
              (mine) =>
                (mine.doi !== null && mine.doi.toLowerCase() === reference.doi?.toLowerCase()) ||
                (mine.url !== null && mine.url === reference.url) ||
                mine.citation === reference.citation,
            ),
          );
        expect(shares, `${model.id} -> ${other.id}`).toBe(true);
      }
    }
  });

  it("rank shared topics first", () => {
    const related = relatedModels(
      MODELS.find((model) => model.id === "fixed_income.duration") ?? (MODELS[0] as (typeof MODELS)[number]),
      MODELS,
      syllabusData,
    ).map((other) => other.id);
    // Both Fixed Income topics of duration are shared by credit_spread and curve_bootstrap.
    expect(related.slice(0, 2).sort()).toEqual(["fixed_income.credit_spread", "fixed_income.curve_bootstrap"]);
  });
});

describe("the coverage matrix", () => {
  const matrix = coverage(MODELS, syllabusData);

  it("lists every topic with the models the seed maps to it", () => {
    const entry = matrix.syllabi[0];
    expect(entry?.total).toBe(SYLLABUS?.topics.length);
    for (const level of entry?.levels ?? []) {
      for (const row of level.topics) {
        const expected = [...SEED].filter(([, topics]) => topics.includes(row.topic.id)).map(([id]) => id).sort();
        expect(row.models.map((model) => model.id).sort(), row.topic.id).toEqual(expected);
      }
    }
    const covered = (entry?.levels ?? []).flatMap((level) => level.topics).filter((row) => row.models.length > 0);
    expect(entry?.covered).toBe(covered.length);
    expect(entry?.covered).toBe(new Set([...SEED.values()].flat()).size);
    expect(entry?.mapped).toBe(MODELS.length);
  });

  it("counts every domain's models, the planned ones at zero", () => {
    expect(matrix.domains.map((entry) => entry.domain.id)).toEqual(DOMAINS.map((domain) => domain.id));
    for (const entry of matrix.domains) {
      expect(entry.count).toBe(MODELS.filter((model) => model.domain === entry.domain.id).length);
      expect(entry.count === 0).toBe(entry.domain.planned !== null);
    }
    expect(matrix.domains.reduce((sum, entry) => sum + entry.count, 0)).toBe(MODELS.length);
  });
});
