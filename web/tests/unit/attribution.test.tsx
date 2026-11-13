// web/tests/unit/attribution.test.tsx
// Phase 5 Step 16's attribution audit, the islands' part (ADR-0005 rule 2;
// ROADMAP §5 "Required notices"): for every provider in sources.json, its
// attribution and required notice appear verbatim in the calculator's sources
// panel and in the note the explorer draws on its chart, whether the series
// document lists its attributions or the chart builds them from the records.
// The files' part is tests/web/test_attribution_audit.py (with Phase 4's
// tests/providers/test_export_notices.py); FRED's notice on the built site is
// tests/site/'s.
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import ResultPanel from "@/components/calculator/ResultPanel";
import { chartNote, seriesFigure, type SeriesDocument } from "@/lib/explorer";
import type { Result, SourceRecord } from "@/lib/results";
import { sourceData, type SourceEntry } from "@/lib/site-data";

/** Text as React's server renderer escapes it. */
function escaped(text: string): string {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#x27;");
}

/** A Plotly annotation's text as a reader sees it: its line breaks spaces, its entities decoded. */
function drawn(text: string): string {
  return text.replaceAll("<br>", " ").replaceAll("&lt;", "<").replaceAll("&gt;", ">").replaceAll("&amp;", "&");
}

/** Collapse runs of white space, as a line-broken note does. */
function words(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

function record(source: SourceEntry): SourceRecord {
  return {
    provider: source.id,
    series_id: "AUDIT",
    licence: source.licence,
    attribution: source.attribution,
    notice: source.notice,
    terms_url: source.terms_url,
    observation_end: "2026-10-31",
    retrieved_at: "2026-11-12T00:00:00Z",
  };
}

function expected(source: SourceEntry): string[] {
  return [source.attribution, ...(source.notice ? [source.notice] : [])];
}

describe("every provider's attribution and notice", () => {
  it("covers every provider the site data lists", () => {
    expect(sourceData.length).toBeGreaterThanOrEqual(31);
  });

  for (const source of sourceData) {
    it(`${source.id}: in the calculator's sources panel`, () => {
      const result: Result = {
        model_id: "a.b",
        model_version: 1,
        inputs: {},
        outputs: { value: 1 },
        warnings: [],
        manifest: { data_sources: [record(source)] },
      };
      const table = { calculation: null, rows: [{ name: "value", unit: "", bounds: "", description: "" }] };
      const html = renderToString(<ResultPanel result={result} table={table} sourceNames={{ [source.id]: source.name }} />);
      for (const text of expected(source)) expect(html, text).toContain(escaped(text));
    });

    it(`${source.id}: in the note drawn on the explorer's chart`, () => {
      const base: SeriesDocument = {
        concept: null,
        frame: { type: "series", meta: { title: "Audit", frequency: "monthly" }, index: ["2026-10-31"], values: [1] },
        sources: [record(source)],
        attributions: expected(source),
      };
      for (const document of [base, { ...base, attributions: [] }]) {
        const note = chartNote(document);
        for (const text of expected(source)) expect(note).toContain(text);
        const [annotation] = seriesFigure(document).layout.annotations;
        for (const text of expected(source)) expect(words(drawn(annotation?.text ?? ""))).toContain(words(text));
      }
    });
  }
});
