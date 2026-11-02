// web/tests/unit/snippets.test.ts
// The calculator's snippets (src/lib/snippets.ts): each kind written from the
// same inputs and data options, naming the public endpoint and the inputs
// only. tests/parity/snippets.test.ts runs them.
import { describe, expect, it } from "vitest";

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

  it("name nothing from the page: no key, cookie or header but the content type", () => {
    for (const text of Object.values(snippets(RUN))) {
      expect(text).not.toMatch(/cookie|authorization|cf-access|api[_-]?key|token/i);
      expect(text).toContain("fixed_income.duration");
    }
  });
});
