// web/tests/unit/calculator.test.ts
// What a calculator derives from its schema and page data
// (src/lib/calculator.ts), how it enters arrays (src/lib/lists.ts) and how it
// reads a result (src/lib/results.ts).
import { describe, expect, it } from "vitest";

import {
  OPTION_NAMES,
  boundFields,
  calculations,
  calculatorProps,
  exampleLabel,
  fieldHelp,
  fieldOrder,
  fieldTitle,
  formRoom,
  optionLabel,
  outputTable,
  problemSlug,
  propertiesFor,
  runInputs,
  boundsInWords,
  plainErrors,
  tidyErrors,
  uiSchemaFor,
} from "@/lib/calculator";
import { formatList, listShape, parseList } from "@/lib/lists";
import {
  asOfText,
  displayValue,
  formatValue,
  manifestFacts,
  pageCount,
  pageOf,
  parseResult,
  runSummary,
  sourceRecords,
} from "@/lib/results";
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
    expect(ui.oneOf[0]?.["ui:title"]).toBe("Macaulay and modified duration");
    expect(ui.oneOf[0]?.calculation).toEqual({ "ui:widget": "hidden" });
    expect(ui.oneOf[0]?.coupon_rate).toEqual({
      "ui:title": "Coupon rate",
      "ui:help": "Rate, as a decimal (0.05 is 5%); from 0 to 1",
    });
    expect(ui.oneOf[0]?.day_count).toMatchObject({ "ui:title": "Day count" });
    expect(ui.oneOf[1]?.curve_tenors).toMatchObject({ "ui:widget": "list" });
  });

  it("names a nullable field's two options and keeps its help beside it", () => {
    const ui = uiSchemaFor(family) as { oneOf: Record<string, Record<string, unknown>>[] };
    expect(ui.oneOf[0]?.issue_date).toEqual({
      "ui:title": "Issue date",
      anyOf: [{ "ui:title": "Enter a value" }, { "ui:title": "Leave it out" }],
    });
  });

  it("writes names as words: fields, examples and options, each option's id beside a name that does not spell it", () => {
    expect(fieldTitle("yield_to_maturity")).toBe("Yield to maturity");
    expect(fieldTitle("ebit")).toBe("EBIT");
    expect(fieldTitle("formula_capm")).toBe("Formula CAPM");
    expect(exampleLabel({ name: "monthly_annuity" })).toBe("Monthly annuity");
    expect(optionLabel("act_act_icma")).toBe("Actual/Actual ICMA (act_act_icma)");
    expect(optionLabel("semiannual")).toBe("Semiannual");
    expect(optionLabel("taylor_1993")).toBe("Taylor (1993)");
    expect(optionLabel("newey_west")).toBe("Newey-West");
    // A one- or two-letter code is explained by its field, not renamed.
    expect(optionLabel("ct")).toBe("ct");
    const ui = uiSchemaFor(family) as { oneOf: Record<string, Record<string, unknown>>[] };
    expect(ui.oneOf[0]?.day_count?.["ui:enumNames"]).toMatchObject({ act_act_icma: "Actual/Actual ICMA (act_act_icma)" });
  });

  it("names only options some model offers", () => {
    const offered = new Set<string>();
    const walk = (node: unknown): void => {
      if (Array.isArray(node)) {
        node.forEach(walk);
        return;
      }
      if (typeof node !== "object" || node === null) return;
      const { enum: values } = node as { enum?: unknown };
      if (Array.isArray(values)) for (const value of values) offered.add(String(value));
      Object.values(node).forEach(walk);
    };
    for (const model of registryData.models) walk(model.input_schema);
    expect([...OPTION_NAMES.keys()].filter((name) => !offered.has(name))).toEqual([]);
  });

  it("orders a form's fields as the model declares them, those a run needs first", () => {
    const node = {
      properties: { a: {}, b: {}, c: {}, d: {} },
      required: ["d", "b"],
    };
    expect(fieldOrder(node, ["d", "c", "b", "a", "gone"])).toEqual(["d", "b", "c", "a"]);
    // A field the card does not list keeps its place after the listed ones.
    expect(fieldOrder(node, ["c"])).toEqual(["b", "d", "c", "a"]);
    const { model, surface } = entry("fixed_income.bond_pricing");
    const order = calculatorProps(model, surface, problemData, sourceData, conceptData).inputOrder;
    const ui = uiSchemaFor(model.input_schema as Record<string, unknown>, [], order) as { oneOf: Record<string, unknown>[] };
    expect((ui.oneOf[0]?.["ui:order"] as string[]).slice(0, 4)).toEqual([
      "settlement",
      "maturity",
      "coupon_rate",
      "yield_to_maturity",
    ]);
  });

  it("estimates the room each model's form takes, at least most of a screen and never absurd", () => {
    for (const candidate of registryData.models) {
      const { model, surface } = entry(candidate.id);
      const room = formRoom(model, surface.profiles.length);
      expect(room.narrow, candidate.id).toBeGreaterThanOrEqual(600);
      expect(room.wide, candidate.id).toBeGreaterThanOrEqual(600);
      expect(room.narrow, candidate.id).toBeLessThan(6000);
      expect(room.wide, candidate.id).toBeLessThanOrEqual(room.narrow + 400);
    }
  });

  it("hides the fields live data fills, and nothing else", () => {
    const schema = entry("macro.policy_rule").model.input_schema as Record<string, unknown>;
    const ui = uiSchemaFor(schema, ["inflation"]) as { oneOf: Record<string, Record<string, unknown>>[] };
    expect(ui.oneOf.every((member) => !("inflation" in member) || member.inflation?.["ui:widget"] === "hidden")).toBe(true);
    expect(ui.oneOf[0]?.inflation_target?.["ui:widget"]).toBeUndefined();
  });

  it("shows no unit for a choice, a flag or a date", () => {
    expect(fieldHelp({ type: "boolean" })).toBe("");
    expect(fieldHelp({ type: "string", enum: ["a"] })).toBe("");
    expect(fieldHelp({ type: "string", format: "date", "x-unit": "date" })).toBe("");
    expect(fieldHelp({ type: "number", "x-unit": "money", minimum: 0 })).toBe("Unit: money; 0 or more");
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

describe("plain words for the form (Phase 5 Step 17)", () => {
  it("writes bounds as a reader would", () => {
    expect(boundsInWords("[0, 1]")).toBe("from 0 to 1");
    expect(boundsInWords("[0.01, 1e+09]")).toBe("from 0.01 to 1,000,000,000");
    expect(boundsInWords("[0, inf]")).toBe("0 or more");
    expect(boundsInWords("(0, inf]")).toBe("more than 0");
    expect(boundsInWords("[-inf, 1]")).toBe("1 or less");
    expect(boundsInWords("(0, 1)")).toBe("more than 0 and less than 1");
    expect(boundsInWords("[-inf, inf]")).toBe("");
    expect(boundsInWords("odd")).toBe("odd");
  });

  it("puts the field's label first and the limit in words", () => {
    const label = (name: string) => (name === "fixed_costs" ? "Fixed costs" : name === "periods" ? "Periods" : name);
    const [missing, low, kind] = plainErrors(
      [
        { name: "required", property: ".fixed_costs", message: "must have required property 'Fixed Costs'", stack: "x", params: { missingProperty: "fixed_costs" } },
        { name: "minimum", property: ".periods", message: "must be >= 0", stack: ".periods must be >= 0", params: { limit: 0 } },
        { name: "type", property: ".periods", message: "must be number", stack: "y", params: { type: "number" } },
      ],
      label,
    );
    expect(missing?.stack).toBe("Fixed costs is required");
    expect(low?.stack).toBe("Periods must be 0 or more");
    expect(low?.message).toBe("must be 0 or more");
    expect(kind?.stack).toBe("Periods must be a number");
  });
});

describe("the outputs table's values (Phase 5 Step 17)", () => {
  it("drops binary rounding's digits and shows a decimal's percent", () => {
    expect(displayValue(0.10014999999999999, "rate")).toBe("0.10015 (10.015%)");
    expect(displayValue(8.161447949150189, "years")).toBe("8.161447949");
    expect(displayValue(95.67052332936917, "money")).toBe("95.67052333");
    expect(displayValue(1.5, "ratio")).toBe("1.5");
    expect(displayValue(null)).toBe(formatValue(null));
    expect(displayValue("text")).toBe("text");
  });
});

describe("a result's summary and manifest", () => {
  const result = parseResult(
    new TextEncoder().encode(
      JSON.stringify({
        model_id: "a.b",
        model_version: 3,
        inputs: {},
        outputs: { calculation: "x", rate: 0.05, price: 99 },
        warnings: [{ code: "w", message: "m" }],
        manifest: {
          package_version: "1.0.0",
          inputs_sha256: "aa",
          result_sha256: "bb",
          schema_version: 2,
          seed: null,
          data_sources: [
            { provider: "bls", series_id: "S1", licence: "hosted-safe", attribution: "A", observation_end: "2026-08-31" },
            { provider: "bea", series_id: "S2", licence: "hosted-safe", attribution: "B", observation_end: "2026-09-30" },
          ],
        },
      }),
    ),
  );

  it("says what a run gave and how far its data runs", () => {
    expect(runSummary(result)).toBe(
      "The run finished: 2 outputs, 1 warning. It read 2 data series, with observations to 2026-09-30: each is listed under Sources.",
    );
    expect(runSummary({ ...result, warnings: [], manifest: {} })).toBe("The run finished: 2 outputs, no warnings.");
  });

  it("lists the manifest's facts a reader checks a result by, and only those it holds", () => {
    expect(manifestFacts(result)).toEqual([
      { label: "Model", value: "a.b, version 3" },
      { label: "pyeconomics version", value: "1.0.0" },
      { label: "Inputs SHA-256", value: "aa" },
      { label: "Result SHA-256", value: "bb" },
      { label: "Manifest schema", value: "2" },
    ]);
  });
});
