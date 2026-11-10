// web/tests/unit/models.test.ts
// What a model page derives from its registry entry: its URL (a bijection with
// the id), its variables tables (equal, row for row, to the card's own, which
// core/cards.py writes), the evidence words the card uses, its bound fields
// joined to the catalog, its citations' links and its description.
import { describe, expect, it } from "vitest";

import {
  COST_MEANING,
  EVIDENCE_MEANING,
  cardOrder,
  dataProfiles,
  describe as describeModel,
  docsUrl,
  domainPath,
  domainTitle,
  formatG,
  idOfPath,
  modelPath,
  referenceLink,
  variables,
  type VariableTable,
} from "@/lib/models";
import { COST, EVIDENCE, parseModels } from "@/lib/registry-schema";
import { conceptData, registryData, sourceData } from "@/lib/site-data";

const models = parseModels(registryData);

/** The card's variables tables for one heading ("Inputs" or "Outputs"). */
function cardTables(card: string, heading: "Inputs" | "Outputs"): VariableTable[] {
  const start = card.indexOf(`\n### ${heading}\n`);
  const end = card.indexOf(heading === "Inputs" ? "\n### Outputs\n" : "\n## ", start + 1);
  const section = card.slice(start, end);
  const tables: VariableTable[] = [];
  let current: VariableTable | null = null;
  for (const line of section.split("\n")) {
    const calculation = /^#### Calculation `([^`]+)`$/.exec(line);
    if (calculation) {
      current = { calculation: calculation[1] ?? null, rows: [] };
      tables.push(current);
    } else if (line.startsWith("| `")) {
      if (!current) {
        current = { calculation: null, rows: [] };
        tables.push(current);
      }
      const cells = line
        .slice(2, -2)
        .split(/ (?<!\\)\| /)
        .map((cell) => cell.replaceAll("\\|", "|"));
      const [name = "", unit = "", bounds = "", description = ""] = cells;
      current.rows.push({ name: name.slice(1, -1), unit, bounds, description });
    }
  }
  return tables;
}

/** A table as the card writes it: whitespace collapsed in every cell. */
function asCard(tables: VariableTable[]): VariableTable[] {
  const squash = (text: string): string => text.split(/\s+/).filter(Boolean).join(" ");
  return tables.map((table) => ({
    calculation: table.calculation,
    rows: table.rows.map((row) => ({
      name: row.name,
      unit: squash(row.unit),
      bounds: squash(row.bounds),
      description: squash(row.description),
    })),
  }));
}

describe("model URLs", () => {
  it("map every id to its decision-2 page and back", () => {
    const paths = models.map((model) => modelPath(model.id));
    expect(new Set(paths).size).toBe(models.length);
    for (const model of models) {
      expect(idOfPath(modelPath(model.id))).toBe(model.id);
      expect(modelPath(model.id).startsWith(domainPath(model.domain))).toBe(true);
    }
    expect(modelPath("fixed_income.bond_pricing")).toBe("/models/fixed-income/bond-pricing/");
    expect(idOfPath("/models/fixed-income/bond-pricing/")).toBe("fixed_income.bond_pricing");
  });

  it("refuse what is not a model id or a model page", () => {
    expect(() => modelPath("fixed_income")).toThrow(/not a model id/);
    expect(() => modelPath("a.b.c")).toThrow(/not a model id/);
    expect(idOfPath("/models/fixed-income/")).toBeNull();
    expect(idOfPath("/problems/invalid-input/")).toBeNull();
  });

  it("name domains for a reader and link the documentation", () => {
    expect(domainTitle("fixed_income")).toBe("Fixed income");
    expect(docsUrl("fixed_income.duration")).toBe(
      "https://docs.pyeconomics.dev/en/main/reference/models/fixed_income/duration.html",
    );
  });
});

describe("formatG", () => {
  it.each([
    [0, "0"],
    [1, "1"],
    [200, "200"],
    [0.01, "0.01"],
    [10000, "10000"],
    [123456.7, "123457"],
    [999999.5, "1e+06"],
    [1e9, "1e+09"],
    [1e15, "1e+15"],
    [1e-6, "1e-06"],
    [0.0001, "0.0001"],
    [0.00001, "1e-05"],
    [-0.99, "-0.99"],
    [-1e15, "-1e+15"],
    [2.05, "2.05"],
  ])("writes %d as Python's %%g does: %s", (value, text) => {
    expect(formatG(value)).toBe(text);
  });
});

describe("variables", () => {
  it.each(models.map((model) => [model.id, model] as const))(
    "equal the card's tables for %s",
    (_id, model) => {
      const inputs = variables(model.input_schema, cardOrder(model.card, "Inputs"));
      const outputs = variables(model.output_schema, cardOrder(model.card, "Outputs"));
      expect(asCard(inputs)).toEqual(cardTables(model.card, "Inputs"));
      expect(asCard(outputs)).toEqual(cardTables(model.card, "Outputs"));
    },
  );
});

describe("cardOrder", () => {
  it("reads each table's names in the card's order, and nothing from a card without them", () => {
    const card = [
      "# T",
      "## Variables",
      "### Inputs",
      "| Name |",
      "| --- |",
      "| `b` | x |",
      "| `a` | y |",
      "### Outputs",
      "#### Calculation `c`",
      "| `z` | w |",
      "## Assumptions",
      "",
    ].join("\n\n");
    expect(cardOrder(card, "Inputs")).toEqual([["b", "a"]]);
    expect(cardOrder(card, "Outputs")).toEqual([["z"]]);
    expect(cardOrder("# No tables\n", "Inputs")).toEqual([]);
    const schema = { properties: { a: { type: "number" }, b: { type: "number" }, c: { type: "number" } } };
    expect(variables(schema, [["c", "a"]])[0]?.rows.map((row) => row.name)).toEqual(["c", "a", "b"]);
  });
});

describe("evidence and cost", () => {
  it("words each evidence status as the card does", () => {
    for (const model of models) {
      if (model.evidence) {
        expect(model.card).toContain(`Status: **${model.evidence}**. ${EVIDENCE_MEANING[model.evidence]}`);
      }
    }
    expect(Object.keys(EVIDENCE_MEANING)).toEqual([...EVIDENCE]);
    expect(Object.keys(COST_MEANING)).toEqual([...COST]);
  });
});

describe("dataProfiles", () => {
  const bound = models.filter((model) => model.bindings.length > 0);

  it("joins every bound field of every bound model to its concept and sources", () => {
    expect(bound.length).toBeGreaterThan(0);
    for (const model of bound) {
      const profiles = dataProfiles(model.bindings, conceptData, sourceData);
      expect(profiles.map((profile) => profile.profile)).toContain("default");
      const rows = profiles.flatMap((profile) => profile.rows);
      expect(rows).toHaveLength(model.bindings.length);
      for (const row of rows) {
        expect(row.sources.length, `${model.id} ${row.field}`).toBeGreaterThan(0);
        expect(row.hosted).toBe(row.sources.some((source) => source.hosted));
        for (const source of row.sources) expect(source.name).not.toBe("");
      }
    }
  });

  it("words a curve's and a matrix's binding as the card does", () => {
    const curve = bound.find((model) => model.bindings.some((binding) => binding.tenors !== null));
    const row = dataProfiles(curve?.bindings ?? [], conceptData, sourceData)
      .flatMap((profile) => profile.rows)
      .find((entry) => entry.shape?.startsWith("tenors in"));
    expect(row?.rule).toBe("the curve on or before the date: its last row, a value per tenor");
    const matrix = bound.find((model) => model.bindings.some((binding) => binding.columns.length > 0));
    expect(
      dataProfiles(matrix?.bindings ?? [], conceptData, sourceData)
        .flatMap((profile) => profile.rows)
        .some((entry) => entry.shape?.startsWith("columns ")),
    ).toBe(true);
  });

  it("fails on a concept the catalog lacks", () => {
    const binding = { ...bound[0]?.bindings[0], concept: "no.such.concept" } as NonNullable<
      (typeof bound)[number]["bindings"][number]
    >;
    expect(() => dataProfiles([binding], conceptData, sourceData)).toThrow(/the catalog lacks/);
  });
});

describe("citations and descriptions", () => {
  const base = { key: "k", citation: "c", locator: null, isbn: null };

  it("link a DOI first, then a URL, else nothing", () => {
    expect(referenceLink({ ...base, doi: "10.1/x", url: "https://example.org" })).toBe("https://doi.org/10.1/x");
    expect(referenceLink({ ...base, doi: null, url: "https://example.org" })).toBe("https://example.org");
    expect(referenceLink({ ...base, doi: null, url: null })).toBeNull();
  });

  it("cut a long summary at a word", () => {
    expect(describeModel({ summary: "Short." })).toBe("Short.");
    const long = describeModel({ summary: `${"word ".repeat(60)}end` });
    expect(long.length).toBeLessThanOrEqual(160);
    expect(long.endsWith("word…")).toBe(true);
  });
});
