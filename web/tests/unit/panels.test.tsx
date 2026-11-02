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
import ProblemPanel from "@/components/calculator/ProblemPanel";
import ResultPanel from "@/components/calculator/ResultPanel";
import type { Result } from "@/lib/results";

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
    expect(html).toContain("2026-03-01T00:00:00Z");
    expect(html).toContain("observations to 2026-02-28");
    expect(html).toContain("the latest published, not those known on the as-of date");
    expect(html).toContain("<td");
    // A terms page that is not https is not linked.
    expect(html).not.toContain("javascript:");
  });
});
