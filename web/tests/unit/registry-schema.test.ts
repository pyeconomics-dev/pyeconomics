// web/tests/unit/registry-schema.test.ts
// The schema the models collection validates with mirrors REGISTRY_SCHEMA:
// its keys are exactly an entry's keys (REGISTRY_SCHEMA requires every key and
// allows no other, and tests/surfaces checks the export against it), every
// exported model passes, and an entry the pages cannot render fails, naming
// its model and the key.
import { describe, expect, it } from "vitest";

import { ModelSchema, parseModels } from "@/lib/registry-schema";
import { registryData } from "@/lib/site-data";

describe("ModelSchema", () => {
  it("names exactly the keys of every registry.json entry", () => {
    const keys = Object.keys(ModelSchema.shape).sort();
    for (const model of registryData.models) {
      expect(Object.keys(model).sort(), model.id).toEqual(keys);
    }
  });

  it("accepts every exported model", () => {
    const models = parseModels(registryData);
    expect(models.map((model) => model.id)).toEqual(registryData.models.map((model) => model.id));
  });

  it("fails on an entry the pages cannot render, naming the model and the key", () => {
    const [first] = registryData.models;
    const broken = { ...first, formula: "E = mc^2" };
    expect(() => parseModels({ models: [broken] })).toThrow(`model ${String(first?.id)} cannot be rendered: formula: `);
    const missing = Object.fromEntries(Object.entries(first ?? {}).filter(([key]) => key !== "summary"));
    expect(() => parseModels({ models: [missing] })).toThrow(/summary: /);
    expect(() => parseModels({ models: [{}] })).toThrow(/model #0 cannot be rendered/);
  });

  it("refuses a document with no models", () => {
    expect(() => parseModels({})).toThrow();
  });
});
