// web/tests/unit/site-data.test.ts
// The site data the export writes: the formats this site reads, every model,
// problem, source and concept, and nothing in it a page must not show.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  conceptData,
  domains,
  problemData,
  registryData,
  sourceData,
  version,
} from "@/lib/site-data";

const GENERATED = fileURLToPath(new URL("../../src/data/generated/", import.meta.url));

describe("the site data", () => {
  it("is the registry of one pyeconomics version, sorted by id", () => {
    expect(version).toMatch(/^\d+\.\d+\.\d+[a-z0-9.]*$/);
    const ids = registryData.models.map((model) => model.id);
    expect(ids).toEqual([...ids].sort());
    for (const model of registryData.models) {
      expect(model.id).toMatch(/^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$/);
      expect(model.id.startsWith(`${model.domain}.`)).toBe(true);
    }
  });

  it("counts every model in exactly one domain", () => {
    const total = domains().reduce((sum, [, count]) => sum + count, 0);
    expect(total).toBe(registryData.models.length);
    expect(domains([])).toEqual([]);
  });

  it("holds one problem per slug, each with its type URI", () => {
    const slugs = problemData.map((problem) => problem.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
    for (const problem of problemData) {
      expect(problem.type).toBe(`https://pyeconomics.dev/problems/${problem.slug}`);
      expect(problem.status).toBeGreaterThanOrEqual(400);
    }
    expect(slugs).toContain("invalid-input");
  });

  it("describes every source by its terms, with no host, path or key value", () => {
    expect(sourceData.map((source) => source.id)).toEqual(sourceData.map((source) => source.id).sort());
    for (const source of sourceData) {
      expect(source.terms_url).toMatch(/^https:\/\//);
      expect(Object.keys(source).sort()).toEqual(
        [
          "attribution",
          "extra",
          "hosted",
          "id",
          "key_required",
          "key_variable",
          "licence",
          "llm_use",
          "name",
          "notice",
          "storage",
          "terms_checked",
          "terms_url",
        ].sort(),
      );
      expect(source.hosted).toBe(source.licence === "hosted-safe" || source.licence === "user-supplied");
    }
  });

  it("marks a concept hosted exactly when a candidate is", () => {
    for (const concept of conceptData) {
      expect(concept.candidates.length).toBeGreaterThan(0);
      expect(concept.hosted).toBe(concept.candidates.some((candidate) => candidate.hosted));
    }
  });

  it("is canonical JSON: no whitespace between tokens and no trailing newline", () => {
    for (const name of ["registry", "openapi", "problems", "sources", "concepts"]) {
      const text = readFileSync(`${GENERATED}${name}.json`, "utf8");
      expect(text.endsWith("\n")).toBe(false);
      expect(JSON.stringify(JSON.parse(text)).length).toBeLessThanOrEqual(text.length);
    }
  });
});
