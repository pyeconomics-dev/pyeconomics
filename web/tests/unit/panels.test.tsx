// web/tests/unit/panels.test.tsx
// The calculator's result and problem panels, rendered through React's server
// renderer: every string from the server reaches the page as text, never as
// HTML (a problem whose title, detail and field errors hold markup is
// escaped); a problem links its page, gives the local command where it points
// to local mode and says when to retry a rate limit; the sources panel shows
// each source's attribution, notice, licence class, terms page, as-of and
// retrieval time, and what revised data means.
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { attributes, startTags } from "../../scripts/headers.ts";
import ProblemPanel, { fieldPath, plainMessage } from "@/components/calculator/ProblemPanel";
import ResultPanel, { PendingResult } from "@/components/calculator/ResultPanel";
import { MANIFEST_LABELS, manifestFacts, retrievedText, type Result } from "@/lib/results";

const MARKUP = '<img src="x" onerror="alert(1)"><script>alert(2)</script>';

function elements(html: string): string[] {
  return startTags(html).map((tag) => /^<([a-z0-9-]+)/i.exec(tag)?.[1]?.toLowerCase() ?? "");
}

describe("the problem panel", () => {
  const problem = {
    type: "https://pyeconomics.dev/problems/invalid-input",
    title: `Invalid input ${MARKUP}`,
    status: 422,
    detail: `The inputs failed ${MARKUP}`,
    errors: [{ loc: ["macaulay_modified", "coupon_rate"], msg: `too high ${MARKUP}`, type: "less_than_equal" }],
  };

  it("renders the server's text as text", () => {
    const html = renderToString(
      <ProblemPanel problem={problem} status={422} retryAfter={null} localSlugs={[]} localCommand="x" />,
    );
    expect(elements(html)).not.toContain("img");
    expect(elements(html)).not.toContain("script");
    for (const tag of startTags(html)) for (const name of attributes(tag).keys()) expect(name).not.toMatch(/^on/);
    expect(html).toContain("&lt;img src=&quot;x&quot; onerror=&quot;alert(1)&quot;&gt;");
    expect(html).toContain('href="/problems/invalid-input/"');
    expect(html).toContain("macaulay_modified.coupon_rate");
  });

  it("gives the local command where the problem points to local mode, and when to retry", () => {
    const local = renderToString(
      <ProblemPanel
        problem={{ type: "https://pyeconomics.dev/problems/budget-exceeded", title: "Budget exceeded", detail: "d" }}
        status={422}
        retryAfter={null}
        localSlugs={["budget-exceeded"]}
        localCommand="pyeconomics models run a.b --inputs FILE"
      />,
    );
    expect(local).toContain("pyeconomics models run a.b --inputs FILE");
    const limited = renderToString(
      <ProblemPanel problem={{}} status={429} retryAfter={12} localSlugs={[]} localCommand="x" />,
    );
    expect(limited).toContain("try again in 12 seconds");
    expect(limited).toContain("The run failed (HTTP 429)");
  });

  it("links no page for a type that is not one of this site's problems", () => {
    const html = renderToString(
      <ProblemPanel problem={{ type: "javascript:alert(1)", title: "t" }} status={500} retryAfter={null} localSlugs={[]} localCommand="x" />,
    );
    expect(html).not.toContain("href=");
  });
});

describe("the result panel", () => {
  const result: Result = {
    model_id: "a.b",
    model_version: 1,
    inputs: {},
    outputs: { rate: 0.05, path: [1, 2, 3], note: MARKUP },
    warnings: [{ code: "w", message: MARKUP }],
    manifest: {
      data_sources: [
        {
          provider: "bea",
          series_id: "T1",
          field: "inflation",
          licence: "hosted-safe",
          attribution: `Source: BEA. ${MARKUP}`,
          notice: "Not endorsed by BEA.",
          terms_url: "javascript:alert(3)",
          observation_start: "2020-01-31",
          observation_end: "2026-02-28",
          retrieved_at: "2026-03-01T00:00:00Z",
          warnings: ["revised_data"],
        },
      ],
    },
  };
  const table = {
    calculation: null,
    rows: [{ name: "rate", unit: "rate", bounds: "", description: "The rate" }],
  };

  it("shows outputs with units, warnings and each source as text", () => {
    const html = renderToString(<ResultPanel result={result} table={table} sourceNames={{ bea: "Bureau of Economic Analysis" }} />);
    expect(elements(html)).not.toContain("img");
    expect(elements(html)).not.toContain("script");
    expect(html).toContain("Bureau of Economic Analysis");
    expect(html).toContain("Not endorsed by BEA.");
    expect(html).toContain("hosted-safe");
    // The retrieval time to the minute, in words; the JSON holds the source's own timestamp.
    expect(html).toContain("2026-03-01 00:00 UTC");
    expect(html).not.toContain("2026-03-01T00:00:00Z");
    expect(html).toContain("observations to 2026-02-28");
    // A data warning in words, with its code after them (the confirmation round: the code led).
    expect(html).toMatch(/not those known on the as-of date\.\s*(<!-- -->)?\s*<code[^>]*>revised_data<\/code>/);
    expect(html).toContain("<td");
    // A terms page that is not https is not linked.
    expect(html).not.toContain("javascript:");
  });
});

describe("a result on its way (Phase 5 Step 18's confirmation round)", () => {
  const table = {
    calculation: null,
    rows: [
      { name: "sharpe_ratio", unit: "ratio", bounds: "", description: "Mean excess return over its standard deviation" },
      { name: "observations", unit: "count", bounds: "", description: "How many returns" },
    ],
  };

  it("shows the outputs' table and the manifest's lines with nothing for a value yet", () => {
    const html = renderToString(<PendingResult table={table} />);
    // The same rows the result will have, by name, id and unit, in the same table.
    expect(html.split("data-output=").length - 1).toBe(2);
    expect(html).toContain("Sharpe ratio");
    expect(html).toContain("sharpe_ratio");
    expect(html).toContain("Mean excess return over its standard deviation");
    expect(html).toContain("Running the model…");
    for (const label of MANIFEST_LABELS) expect(html, label).toContain(label);
    // Nothing that reads as a value: no digit in any cell of the table.
    const cells = [...html.matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((found) => (found[1] ?? "").replace(/<[^>]+>/g, ""));
    expect(cells.length).toBe(2);
    for (const cell of cells) expect(cell).not.toMatch(/[0-9]/);
    // Its copy control is off until there is something to copy.
    expect(html).toMatch(/<button[^>]*disabled[^>]*>Copy the manifest/);
    expect(html).toContain('aria-busy="true"');
  });

  it("names the manifest's lines as a result does", () => {
    const facts = manifestFacts({
      model_id: "a.b",
      model_version: 1,
      inputs: {},
      outputs: {},
      warnings: [],
      manifest: { package_version: "1.0.0", inputs_sha256: "a".repeat(64), result_sha256: "b".repeat(64), schema_version: 2 },
    } as unknown as Result);
    expect(facts.map((fact) => fact.label)).toEqual([...MANIFEST_LABELS]);
  });

  it("writes a retrieval time to the minute, and leaves what is not a time as it is", () => {
    expect(retrievedText("2026-11-16T23:31:31.117201+00:00")).toBe("2026-11-16 23:31 UTC");
    expect(retrievedText("2026-10-15T12:00:00+02:00")).toBe("2026-10-15 10:00 UTC");
    expect(retrievedText("yesterday")).toBe("yesterday");
  });
});

describe("a long result (Phase 5 Step 18's rounds 2 and 3)", () => {
  const rows = (count: number) =>
    Array.from({ length: count }, (_, index) => ({ name: `output_${String(index)}`, unit: "ratio", bounds: "", description: `What output ${String(index)} is` }));
  const result = (count: number): Result =>
    ({
      model: { id: "toy.long", version: 1 },
      inputs: {},
      outputs: Object.fromEntries(rows(count).map((row, index) => [row.name, index])),
      warnings: [],
      manifest: {},
    }) as unknown as Result;

  it("lists more than eight outputs without their descriptions until asked, and fewer with them", () => {
    const long = renderToString(<ResultPanel result={result(9)} table={{ calculation: null, rows: rows(9) }} sourceNames={{}} />);
    expect(long).toContain("Say what each of the <!-- -->9<!-- --> outputs is");
    expect(long).not.toContain("What output 0 is");
    // Every output is still there by name, with its id and value.
    expect(long.split("data-output=").length - 1).toBe(9);
    const short = renderToString(<ResultPanel result={result(8)} table={{ calculation: null, rows: rows(8) }} sourceNames={{}} />);
    expect(short).not.toContain("data-describe");
    expect(short).toContain("What output 0 is");
  });
});

describe("a problem's field errors in a reader's words (Phase 5 Step 18)", () => {
  it("drops the library's prefix and the calculation's name, and says each error once", () => {
    expect(plainMessage("Value error, settlement must be before maturity")).toBe("Settlement must be before maturity");
    expect(plainMessage("Input should be greater than or equal to 0")).toBe("Input should be greater than or equal to 0");
    expect(fieldPath(["price_from_yield", "coupon_rate"], "price_from_yield")).toEqual(["coupon_rate"]);
    expect(fieldPath(["price_from_yield"], "price_from_yield")).toEqual([]);
    expect(fieldPath(["coupon_rate"], undefined)).toEqual(["coupon_rate"]);
    const html = renderToString(
      <ProblemPanel
        problem={{
          type: "https://pyeconomics.dev/problems/invalid-input",
          title: "The inputs are not valid",
          detail: "The inputs failed validation: price_from_yield: Value error, settlement must be before maturity.",
          errors: [
            { loc: ["price_from_yield"], msg: "Value error, settlement must be before maturity" },
            { loc: ["price_from_yield", "coupon_rate"], msg: "Input should be greater than or equal to 0" },
          ],
        }}
        status={422}
        retryAfter={null}
        localSlugs={[]}
        localCommand="x"
        calculation="price_from_yield"
      />,
    );
    expect(html).toContain("Settlement must be before maturity");
    expect(html).toContain("Coupon rate");
    expect(html).not.toContain("Value error");
    expect(html).not.toContain("The inputs failed validation");
    expect(html.split("ettlement must be before maturity").length).toBe(2);
  });
});
