// web/tests/e2e/catalog.ts
// The registry and the syllabus seed as the end-to-end tests read them: from
// the site data the build used (src/data/generated/), so an expected count is
// always the data's, never a number written into a test.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const GENERATED = fileURLToPath(new URL("../../src/data/generated/", import.meta.url));

/** What the tests read of a model. */
export interface CatalogModel {
  id: string;
  title: string;
  domain: string;
  evidence: string | null;
  cost: string | null;
  tags: string[];
  bindings: unknown[];
}

/** Every registered model, sorted by id. */
export const MODELS: readonly CatalogModel[] = (
  JSON.parse(readFileSync(`${GENERATED}registry.json`, "utf8")) as { models: CatalogModel[] }
).models;

/** The seed: per model id, its topic ids. */
export const SEED: ReadonlyMap<string, readonly string[]> = new Map(
  Object.entries(
    (JSON.parse(readFileSync(`${GENERATED}syllabi.json`, "utf8")) as { syllabi: { models: Record<string, string[]> }[] })
      .syllabi[0]?.models ?? {},
  ),
);
