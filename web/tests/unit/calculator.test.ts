// web/tests/unit/calculator.test.ts
// What a calculator derives from its schema and page data
// (src/lib/calculator.ts), how it enters arrays (src/lib/lists.ts) and how it
// reads a result (src/lib/results.ts).
import { describe, expect, it } from "vitest";

import {
  boundFields,
  calculations,
  calculatorProps,
  fieldHelp,
  outputTable,
  problemSlug,
  propertiesFor,
  runInputs,
  tidyErrors,
  uiSchemaFor,
} from "@/lib/calculator";
import { formatList, listShape, parseList } from "@/lib/lists";
import { asOfText, formatValue, pageCount, pageOf, parseResult, sourceRecords } from "@/lib/results";
import type { Model } from "@/lib/registry-schema";
import { conceptData, problemData, registryData, sourceData, surfaceData } from "@/lib/site-data";

function entry(id: string) {
  const model = registryData.models.find((candidate) => candidate.id === id);
  const surface = surfaceData.find((candidate) => candidate.id === id);
  if (!model || !surface) throw new Error(id);
  // registry.json's entries are the content collection's models (ModelSchema).
  return { model: model as unknown as Model, surface };
}

describe("the form's uiSchema", () => {
  const family = entry("fixed_income.duration").model.input_schema as Record<string, unknown>;

  it("gives a family a calculation selector with each calculation's words, and hides the constant", () => {
    expect(calculations(family).map((c) => c.value)).toEqual(["macaulay_modified", "effective", "key_rate", "dv01"]);
    const ui = uiSchemaFor(family) as { oneOf: Record<string, Record<string, unknown>>[] };
    expect(ui.oneOf[0]?.["ui:title"]).toBe("Macaulay and modified duration (macaulay_modified)");
    expect(ui.oneOf[0]?.calculation).toEqual({ "ui:widget": "hidden" });
    expect(ui.oneOf[0]?.coupon_rate).toEqual({ "ui:help": "Unit: rate; [0, 1]" });
    expect(ui.oneOf[0]?.day_count).toMatchObject({ "ui:title": "Day count" });
    expect(ui.oneOf[1]?.curve_tenors).toMatchObject({ "ui:widget": "list" });
  });

  it("names a nullable field's two options and keeps its help beside it", () => {
    const ui = uiSchemaFor(family) as { oneOf: Record<string, Record<string, unknown>>[] };
    expect(ui.oneOf[0]?.issue_date).toEqual({
      anyOf: [{ "ui:title": "A value" }, { "ui:title": "None (null)" }],
      "ui:help": "Unit: date",
    });
  });

  it("hides the fields live data fills, and nothing else", () => {
    const schema = entry("macro.policy_rule").model.input_schema as Record<string, unknown>;
    const ui = uiSchemaFor(schema, ["inflation"]) as { oneOf: Record<string, Record<string, unknown>>[] };
    expect(ui.oneOf.every((member) => !("inflation" in member) || member.inflation?.["ui:widget"] === "hidden")).toBe(true);
    expect(ui.oneOf[0]?.inflation_target?.["ui:widget"]).toBeUndefined();
  });

  it("shows no unit for a choice or a flag", () => {
    expect(fieldHelp({ type: "boolean" })).toBe("");
    expect(fieldHelp({ type: "string", enum: ["a"] })).toBe("");
    expect(fieldHelp({ type: "number", "x-unit": "money", minimum: 0 })).toBe("Unit: money; [0, inf]");
  });
});

describe("live data", () => {
  it("binds only the chosen calculation's fields, each with whether hosted mode serves it", () => {
    const { model, surface } = entry("macro.policy_rule");
    const schema = model.input_schema as Record<string, unknown>;
    const profile = surface.profiles.find((p) => p.profile === "default");
    const fields = boundFields(schema, profile, "taylor_1993");
    expect(fields.length).toBeGreaterThan(0);
    expect(fields.every((field) => propertiesFor(schema, "taylor_1993").includes(field.field))).toBe(true);
    expect(boundFields(schema, undefined, "taylor_1993")).toEqual([]);
  });

  it("says which fields hosted mode cannot serve", () => {
    const { model, surface } = entry("equity.cape");
    const unserved = boundFields(model.input_schema as Record<string, unknown>, surface.profiles[0], undefined).filter(
      (field) => !field.hosted,
    );
    expect(unserved.map((field) => field.field)).toContain("price");
  });

  it("posts the form's values less the fields the data fills", () => {
    expect(runInputs({ a: 1, b: undefined, c: 2 }, ["c"])).toEqual({ a: 1 });
    expect(runInputs(undefined)).toEqual({});
  });
});

describe("the page's calculator props", () => {
  it("are small: outputs, charts, profiles, the providers' names and the local command", () => {
    const { model, surface } = entry("macro.policy_rule");
    const props = calculatorProps(model, surface, problemData, sourceData, conceptData);
    expect(props.modelId).toBe("macro.policy_rule");
    expect(props.localCommand).toBe("pyeconomics models run macro.policy_rule --inputs FILE");
    expect(props.localSlugs).toEqual(expect.arrayContaining(["input-too-large", "budget-exceeded"]));
    expect(props.sourceNames.bea).toBeDefined();
    expect(Object.keys(props.sourceNames).length).toBeLessThan(sourceData.length);
    expect(props.profiles).toBe(surface.profiles);
    expect(outputTable(props.outputs, "taylor_1993")?.calculation).toBe("taylor_1993");
  });
});

describe("errors and problems", () => {
  it("drop a nullable field's anyOf noise when the field has a real error", () => {
    const errors = [
      { name: "format", property: ".d" },
      { name: "type", property: ".d", params: { type: "null" } },
      { name: "anyOf", property: ".d" },
      { name: "anyOf", property: ".e" },
    ];
    expect(tidyErrors(errors)).toEqual([errors[0], errors[3]]);
  });

  it("read a problem's slug from its type, on this site only", () => {
    expect(problemSlug("https://pyeconomics.dev/problems/invalid-input")).toBe("invalid-input");
    expect(problemSlug("https://evil.example/problems/x")).toBeNull();
    expect(problemSlug(undefined)).toBeNull();
  });
});

describe("lists", () => {
  it("read and write numbers, text and matrices", () => {
    const numbers = listShape({ type: "array", items: { type: "number" } });
    expect(parseList("1, 2;3\n4  5", numbers)).toEqual([1, 2, 3, 4, 5]);
    expect(parseList("1, x", numbers)).toEqual([1, "x"]);
    expect(formatList([1, 2.5], numbers)).toBe("1, 2.5");
    const dates = listShape({ type: "array", items: { type: "string", format: "date" } });
    expect(parseList("2026-01-02\n\n 2026-02-03 ", dates)).toEqual(["2026-01-02", "2026-02-03"]);
    const matrix = listShape({ type: "array", items: { type: "array", items: { type: "number" } } });
    expect(parseList("1, 0\n0, 1\n", matrix)).toEqual([[1, 0], [0, 1]]);
    expect(formatList([[1, 0], [0, 1]], matrix)).toBe("1, 0\n0, 1");
    const flags = listShape({ type: "array", items: { type: "boolean" } });
    expect(parseList("true false", flags)).toEqual([true, false]);
    expect(formatList(null, flags)).toBe("");
  });
});

describe("results", () => {
  const bytes = new TextEncoder().encode(
    JSON.stringify({
      model_id: "a.b",
      model_version: 1,
      inputs: {},
      outputs: { x: null, y: [1, 2] },
      warnings: [],
      manifest: {
        data_sources: [{ provider: "p", series_id: "s", licence: "hosted-safe", attribution: "A", realtime: { realtime_start: "2026-01-02" } }],
      },
    }),
  );

  it("parse the bytes received, and refuse what is not a result", () => {
    const result = parseResult(bytes);
    expect(result.outputs.y).toEqual([1, 2]);
    expect(sourceRecords(result)).toHaveLength(1);
    expect(asOfText(sourceRecords(result)[0] ?? { provider: "", series_id: "", licence: "", attribution: "" })).toBe(
      "as published on 2026-01-02",
    );
    expect(() => parseResult(new TextEncoder().encode('{"type":"x"}'))).toThrow(/not a result/);
  });

  it("show values as JSON writes them and page long arrays", () => {
    expect(formatValue(null)).toBe("undefined (null)");
    expect(formatValue(0.1)).toBe("0.1");
    expect(pageCount(51)).toBe(3);
    expect(pageOf([...Array(51).keys()], 2)).toEqual({ start: 50, items: [50] });
    expect(pageOf([1, 2], 9).start).toBe(0);
  });
});
