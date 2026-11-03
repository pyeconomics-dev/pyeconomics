// web/tests/unit/user-data.test.ts
// "Use my own data" (src/lib/user-data.ts): the array fields of every model's
// calculations with their bounds, the header row, a column's values checked
// against the field's kind and maxItems, a matrix from several columns, and
// the template CSV, which reads back to the example it was built from.
import Papa from "papaparse";
import { describe, expect, it } from "vitest";

import { members, type Node } from "@/lib/models";
import { registryData } from "@/lib/site-data";
import {
  arrayFields,
  cellValue,
  mapColumn,
  mapColumns,
  rowLimit,
  templateCsv,
  withHeader,
  type ArrayField,
  type Cell,
  type ParsedRows,
} from "@/lib/user-data";

function model(id: string) {
  const found = registryData.models.find((entry) => entry.id === id);
  if (!found) throw new Error(`${id} is not registered`);
  return found as unknown as { input_schema: Node; examples: { inputs: Record<string, unknown> }[] };
}

function parsed(rows: Cell[][], truncated = false): ParsedRows {
  return { rows, truncated, sheet: null };
}

const LIST: ArrayField = {
  name: "cpi",
  title: "Cpi",
  shape: { matrix: false, item: "number" },
  minItems: 1,
  maxItems: 4,
  rowMin: 1,
  rowMax: 1,
};

describe("the array fields", () => {
  it("lists a calculation's array fields with their bounds", () => {
    const fields = arrayFields(model("equity.cape").input_schema, undefined);
    expect(fields.map((field) => field.name).sort()).toEqual(["cpi", "earnings"]);
    for (const field of fields) {
      expect(field.shape).toEqual({ matrix: false, item: "number" });
      expect(field.maxItems).toBe(480);
      expect(field.minItems).toBe(1);
    }
    expect(rowLimit(fields)).toBe(480);
  });

  it("reads a matrix field's row bounds and a family's chosen calculation", () => {
    const returns = arrayFields(model("portfolio.risk_based_allocation").input_schema, "equal_risk_contribution").find(
      (field) => field.name === "returns",
    );
    expect(returns?.shape.matrix).toBe(true);
    expect(returns?.rowMax).toBe(100);
    expect(returns?.maxItems).toBe(2520);
    expect(returns?.minItems).toBe(2);
    expect(arrayFields(model("foundations.time_value").input_schema, "present_value")).toEqual([]);
  });

  it("finds an array field in every model that declares one", () => {
    for (const entry of registryData.models) {
      const schema = entry.input_schema as Node;
      for (const [calculation] of members(schema)) {
        for (const field of arrayFields(schema, calculation)) {
          expect(field.maxItems, `${entry.id}.${field.name}`).toBeGreaterThan(0);
          expect(field.maxItems).toBeLessThanOrEqual(10_081);
        }
      }
    }
  });
});

describe("a file's columns", () => {
  it("takes the first row as a header when it holds text that is not a number", () => {
    const table = withHeader(parsed([["date", "cpi"], ["2024-01-31", "300.1"]]));
    expect(table.columns).toEqual(["date", "cpi"]);
    expect(table.rows).toEqual([["2024-01-31", "300.1"]]);
    expect(table.header).toBe(true);
    const bare = withHeader(parsed([[1, 2], [3, 4]]));
    expect(bare.columns).toEqual(["Column 1", "Column 2"]);
    expect(bare.rows).toHaveLength(2);
    expect(bare.header).toBe(false);
  });

  it("reads each cell as a value of the field's kind, and nothing else", () => {
    expect(cellValue("1.5", "number")).toEqual({ ok: true, value: 1.5 });
    expect(cellValue(2, "integer")).toEqual({ ok: true, value: 2 });
    expect(cellValue(2.5, "integer")).toEqual({ ok: false });
    for (const bad of ["=SUM(A1:A3)", "=HYPERLINK(\"https://example.org\")", "", null, "1e999", "NaN", true]) {
      expect(cellValue(bad as Cell, "number"), String(bad)).toEqual({ ok: false });
    }
    expect(cellValue("TRUE", "boolean")).toEqual({ ok: true, value: true });
    expect(cellValue(0, "boolean")).toEqual({ ok: true, value: false });
    expect(cellValue(" 2024-01-31 ", "string")).toEqual({ ok: true, value: "2024-01-31" });
  });
});

describe("mapping", () => {
  const table = withHeader(
    parsed([
      ["cpi", "earnings", "note"],
      ["100", 4, "a"],
      ["101", 4.4, "=1+1"],
      ["102", null, null],
      [null, null, null],
    ]),
  );

  it("gives a column's values down to its last value", () => {
    expect(mapColumn(table, 0, LIST)).toEqual({ ok: true, values: [100, 101, 102] });
    expect(mapColumn(table, 1, LIST)).toEqual({ ok: true, values: [4, 4.4] });
  });

  it("refuses a cell that is not a number, a gap, and more rows than the field takes", () => {
    const text = mapColumn(table, 2, LIST);
    expect(text.ok).toBe(false);
    if (!text.ok) expect(text.reason).toMatch(/note, row 2 of the file, is not a number/);
    const gap = withHeader(parsed([["x"], [1], [null], [3]]));
    const found = mapColumn(gap, 0, LIST);
    expect(found.ok).toBe(false);
    if (!found.ok) expect(found.reason).toMatch(/row 3 of the file, is empty/);
    const long = withHeader(parsed([["x"], ...Array.from({ length: 5 }, (_, i) => [i])]));
    const tooMany = mapColumn(long, 0, LIST);
    expect(tooMany.ok).toBe(false);
    if (!tooMany.ok) expect(tooMany.reason).toMatch(/has 5 rows; cpi takes at most 4/);
  });

  it("refuses a column that ran past the rows the worker read", () => {
    const cut = withHeader(parsed([["x"], [1], [2], [3], [4]], true));
    const found = mapColumn(cut, 0, { ...LIST, maxItems: 10 });
    expect(found.ok).toBe(false);
    if (!found.ok) expect(found.reason).toMatch(/runs past the 4 rows read/);
  });

  it("builds a matrix from several columns, one per value of a row", () => {
    const matrix: ArrayField = { ...LIST, name: "returns", shape: { matrix: true, item: "number" }, rowMin: 2, rowMax: 3 };
    const grid = withHeader(parsed([["a", "b"], [0.01, 0.02], [0.03, 0.04]]));
    expect(mapColumns(grid, [0, 1], matrix)).toEqual({ ok: true, values: [[0.01, 0.02], [0.03, 0.04]] });
    const one = mapColumns(grid, [0], matrix);
    expect(one.ok).toBe(false);
    const ragged = withHeader(parsed([["a", "b"], [0.01, 0.02], [0.03, null]]));
    expect(mapColumns(ragged, [0, 1], matrix).ok).toBe(false);
  });
});

describe("the template CSV", () => {
  it("names each field's column and reads back to the example", () => {
    const cape = model("equity.cape");
    const fields = arrayFields(cape.input_schema, undefined);
    const example = cape.examples[0]?.inputs ?? {};
    const csv = templateCsv(fields, example);
    const rows = Papa.parse<string[]>(csv, { skipEmptyLines: true }).data as Cell[][];
    const table = withHeader(parsed(rows));
    expect(table.columns).toEqual(fields.map((field) => field.name));
    for (const [index, field] of fields.entries()) {
      expect(mapColumn(table, index, field)).toEqual({ ok: true, values: example[field.name] });
    }
  });

  it("gives a matrix one column per value of its rows", () => {
    const matrix: ArrayField = { ...LIST, name: "returns", shape: { matrix: true, item: "number" }, rowMin: 2, rowMax: 3 };
    expect(templateCsv([matrix], { returns: [[1, 2], [3, 4]] })).toBe("returns_1,returns_2\r\n1,2\r\n3,4\r\n");
    expect(templateCsv([LIST], { cpi: ["a,b"] })).toBe('cpi\r\n"a,b"\r\n');
  });
});
