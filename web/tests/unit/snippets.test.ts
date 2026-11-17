// web/tests/unit/snippets.test.ts
// The calculator's snippets (src/lib/snippets.ts): each kind written from the
// same inputs and data options, naming the public endpoint and the inputs
// only. tests/parity/snippets.test.ts runs them.
import { describe, expect, it } from "vitest";

import golden from "@/data/generated/golden.json";
import { LIST_WIDTH, fillLines, jsonText } from "@/lib/json-text";
import { API_ORIGIN, cliSnippet, curlSnippet, mcpCall, pythonLiteral, pythonSnippet, snippets } from "@/lib/snippets";

const RUN = { modelId: "fixed_income.duration", inputs: { rate: 0.05, flag: true, none: null, tenors: [1, 2], name: 'it\'s "q"' } };

describe("pythonLiteral", () => {
  it("writes JSON values as Python literals", () => {
    expect(pythonLiteral(null)).toBe("None");
    expect(pythonLiteral(true)).toBe("True");
    expect(pythonLiteral(false)).toBe("False");
    expect(pythonLiteral(1e-7)).toBe("1e-7");
    expect(pythonLiteral('a "b"\n')).toBe('"a \\"b\\"\\n"');
    expect(pythonLiteral([[1, 2], [3]])).toBe("[\n    [1, 2],\n    [3],\n]");
    // A long list fills lines a phone's code box shows whole.
    const long = Array.from({ length: 14 }, (_, index) => index / 100);
    expect(pythonLiteral({ returns: long }).split("\n")).toEqual([
      "{",
      '    "returns": [',
      "        0, 0.01, 0.02, 0.03, 0.04,",
      "        0.05, 0.06, 0.07, 0.08,",
      "        0.09, 0.1, 0.11, 0.12, 0.13,",
      "    ],",
      "}",
    ]);
    expect(pythonLiteral({ weights: [0.5, 0.5] })).toBe('{\n    "weights": [0.5, 0.5],\n}');
    expect(pythonLiteral({})).toBe("{}");
    expect(() => pythonLiteral(Number.NaN)).toThrow(/NaN/);
  });
});

describe("the snippets", () => {
  it("run the model in Python, binding live data first when asked", () => {
    expect(pythonSnippet(RUN)).toContain('result = pyeconomics.run("fixed_income.duration", inputs)');
    expect(pythonSnippet(RUN)).toContain('"flag": True,');
    const bound = pythonSnippet({ ...RUN, options: { profile: "default", asOf: "2026-03-05" } });
    expect(bound).toContain("import datetime as dt");
    expect(bound).toContain('bound = pyeconomics.bind("fixed_income.duration", profile="default", as_of=dt.date(2026, 3, 5), **inputs)');
  });

  it("run the command line with the inputs' JSON on standard input", () => {
    expect(cliSnippet(RUN)).toMatch(/^pyeconomics models run fixed_income\.duration --inputs - <<'JSON'\n\{\n/);
    expect(cliSnippet(RUN)).toMatch(/\nJSON\n$/);
    expect(cliSnippet({ ...RUN, options: { profile: "us_sep", asOf: "2026-03-05" } })).toContain(
      "run fixed_income.duration --profile us_sep --as-of 2026-03-05 --inputs -",
    );
  });

  it("post with curl to the public endpoint, or the origin given", () => {
    expect(curlSnippet(RUN)).toContain(`-X POST ${API_ORIGIN}/v1/models/fixed_income.duration/run \\`);
    expect(curlSnippet(RUN, "http://127.0.0.1:9")).toContain("http://127.0.0.1:9/v1/models/");
    expect(curlSnippet({ ...RUN, options: { profile: "default", asOf: "2026-03-05" } })).toContain(
      "'https://pyeconomics.dev/v1/models/fixed_income.duration/run?profile=default&as_of=2026-03-05'",
    );
  });

  it("call MCP's run_model with the inputs and data options as its arguments", () => {
    expect(mcpCall(RUN)).toEqual({ name: "run_model", arguments: { model_id: RUN.modelId, inputs: RUN.inputs } });
    expect(mcpCall({ ...RUN, options: { profile: "default" } }).arguments).toMatchObject({ profile: "default" });
  });

  it("write JSON that parses to the same inputs, its lists short enough to read", () => {
    const cases = (golden as { cases: { model: string; inputs: Record<string, unknown> }[] }).cases;
    expect(cases.length).toBeGreaterThan(100);
    for (const entry of cases) {
      const text = jsonText(entry.inputs);
      expect(JSON.parse(text), entry.model).toEqual(entry.inputs);
    }
    const returns = Array.from({ length: 12 }, (_, index) => (index % 2 === 0 ? 0.021 : -0.013));
    const lines = jsonText({ returns, weights: [0.5, 0.5], matrix: [[1, 2], [3, 4]] }).split("\n");
    // Twelve values fill three lines, none wider than a phone's code box; a short list stays on one.
    expect(lines.filter((line) => /^\s+-?0\.0/.test(line))).toHaveLength(3);
    expect(Math.max(...lines.map((line) => line.length))).toBeLessThanOrEqual(LIST_WIDTH);
    expect(lines).toContain('  "weights": [0.5, 0.5],');
    expect(lines).toContain("    [1, 2],");
    expect(fillLines(["1", "2"], "", false)).toEqual(["1, 2"]);
    expect(fillLines(["1", "2"], "", true)).toEqual(["1, 2,"]);
    expect(jsonText([])).toBe("[]");
    expect(jsonText({})).toBe("{}");
    expect(jsonText(null)).toBe("null");
  });

  it("name nothing from the page: no key, cookie or header but the content type", () => {
    for (const text of Object.values(snippets(RUN))) {
      expect(text).not.toMatch(/cookie|authorization|cf-access|api[_-]?key|token/i);
      expect(text).toContain("fixed_income.duration");
    }
  });
});
