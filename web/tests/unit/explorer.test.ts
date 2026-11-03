// web/tests/unit/explorer.test.ts
// The data explorer's logic (src/lib/explorer.ts, src/lib/series-request.ts):
// the concept search over title, id, unit, frequency and topic; whether a
// concept is fetched, needs parameters or is read locally, in hosted and
// local mode; the transforms each frequency allows and their text, held to
// core/transforms.py's canonical form; the default range; the series route's
// path and query; the request, its bytes kept; the server's mode; and the
// chart, whose attribution and as-of date are drawn on it as escaped text.
import { describe, expect, it } from "vitest";

import {
  SERIES_TRANSFORMS,
  availability,
  chartNote,
  conceptListings,
  convertTargets,
  defaultRange,
  facetValues,
  modelsReading,
  parseSeries,
  plotlyLines,
  searchConcepts,
  seriesFigure,
  seriesPath,
  seriesQuery,
  transformText,
  transformsFor,
  type ConceptQuery,
  type SeriesDocument,
} from "@/lib/explorer";
import { DATA_PATH, conceptPath, isConceptId } from "@/lib/paths";
import { forgetServerMode, getSeries, serverMode } from "@/lib/series-request";
import { conceptData, registryData } from "@/lib/site-data";

const LISTINGS = conceptListings(conceptData);
const ANY: ConceptQuery = { text: "", frequency: "", topic: "", served: false };

function concept(id: string) {
  const found = conceptData.find((entry) => entry.id === id);
  if (!found) throw new Error(`${id} is not in concepts.json`);
  return found;
}

const DOCUMENT: SeriesDocument = {
  concept: "us.unemployment.rate",
  frame: {
    type: "series",
    meta: { title: "Unemployment rate", unit: { text: "Decimal" }, frequency: "monthly" },
    index: ["2024-01-31", "2024-02-29"],
    values: [0.037, null],
  },
  sources: [
    {
      provider: "bls",
      series_id: "LNS14000000",
      licence: "hosted-safe",
      attribution: "Source: U.S. Bureau of Labor Statistics <BLS> & partners.",
      retrieved_at: "2026-11-02T23:41:00Z",
      transforms: ["diff"],
    },
  ],
  attributions: ["Source: U.S. Bureau of Labor Statistics <BLS> & partners."],
};

describe("concept pages", () => {
  it("put each concept at a path made from its id, one to one", () => {
    expect(conceptPath("us.unemployment.rate")).toBe("/data/us/unemployment/rate/");
    expect(conceptPath("us.inflation.pce_core.yoy")).toBe("/data/us/inflation/pce-core/yoy/");
    const paths = conceptData.map((entry) => conceptPath(entry.id));
    expect(new Set(paths).size).toBe(paths.length);
    for (const path of paths) expect(path.startsWith(DATA_PATH) && path.endsWith("/")).toBe(true);
    for (const bad of ["us.rate", "a.b.c.d.e", "Us.x.y", "us..x", "us._x.y", "us.x-y.z", "../a.b.c"]) {
      expect(isConceptId(bad), bad).toBe(false);
      expect(() => conceptPath(bad)).toThrow(/not a concept id/);
    }
    expect(conceptPath("factors.ff3.us.monthly")).toBe("/data/factors/ff3/us/monthly/");
  });

  it("list every model whose bindings read a concept", () => {
    const readers = modelsReading("us.treasury.nominal_10y", registryData.models).map((model) => model.id);
    expect(readers.length).toBeGreaterThan(0);
    for (const id of readers) {
      const model = registryData.models.find((entry) => entry.id === id);
      expect((model?.bindings as { concept: string }[]).some((b) => b.concept === "us.treasury.nominal_10y")).toBe(true);
    }
    expect(modelsReading("no.such.concept", registryData.models)).toEqual([]);
  });
});

describe("the concept search", () => {
  it("lists every concept, sorted by id, with no words", () => {
    expect(searchConcepts(LISTINGS, ANY).map((entry) => entry.id)).toEqual([...conceptData.map((c) => c.id)].sort());
  });

  it("says which concepts need parameters, which local mode reads with the Python API", () => {
    for (const listing of LISTINGS) {
      expect(listing.parameters, listing.id).toBe(concept(listing.id).parameters.length > 0);
    }
    expect(LISTINGS.find((entry) => entry.id === "us.sep.unemployment")?.parameters).toBe(true);
    expect(LISTINGS.find((entry) => entry.id === "factors.ff3.us.monthly")?.parameters).toBe(false);
  });

  it("finds a concept by its title, its id, its unit, its frequency and its topic", () => {
    const first = (text: string) => searchConcepts(LISTINGS, { ...ANY, text }).at(0)?.id;
    expect(first("unemployment rate")).toBe("us.unemployment.rate");
    expect(first("nominal_10y")).toBe("us.treasury.nominal_10y");
    const unemployment = LISTINGS.find((entry) => entry.id === "us.unemployment.rate");
    expect(unemployment).toBeDefined();
    if (!unemployment) return;
    for (const word of [unemployment.unit, unemployment.frequency, unemployment.topic]) {
      expect(searchConcepts(LISTINGS, { ...ANY, text: word }).map((entry) => entry.id), word).toContain("us.unemployment.rate");
    }
    expect(searchConcepts(LISTINGS, { ...ANY, text: "zzzz qqqq" })).toEqual([]);
  });

  it("needs every word to match, and ranks title words first", () => {
    const found = searchConcepts(LISTINGS, { ...ANY, text: "treasury real" });
    expect(found.length).toBeGreaterThan(0);
    for (const entry of found) expect(`${entry.title} ${entry.id}`.toLowerCase()).toMatch(/treasury|tips/);
    expect(found.every((entry) => /real/i.test(`${entry.title} ${entry.id} ${entry.unit} ${entry.topic}`))).toBe(true);
  });

  it("filters by frequency, topic and what the hosted site serves", () => {
    const monthly = searchConcepts(LISTINGS, { ...ANY, frequency: "monthly" });
    expect(monthly.length).toBeGreaterThan(0);
    expect(monthly.every((entry) => entry.frequency === "monthly")).toBe(true);
    const topic = facetValues(LISTINGS, "topic")[0] ?? "";
    expect(searchConcepts(LISTINGS, { ...ANY, topic }).every((entry) => entry.topic === topic)).toBe(true);
    const served = searchConcepts(LISTINGS, { ...ANY, served: true });
    expect(served.length).toBe(conceptData.filter((entry) => entry.snapshot).length);
    expect(served.some((entry) => entry.id.startsWith("factors."))).toBe(false);
  });
});

describe("what a concept page offers", () => {
  it("fetches in hosted mode only what the snapshot serves, and gives the local command for the rest", () => {
    expect(availability(concept("us.unemployment.rate"), "hosted")).toEqual({ kind: "fetch" });
    expect(availability(concept("factors.ff3.us.monthly"), "hosted")).toEqual({
      kind: "local",
      command: "pyeconomics data get factors.ff3.us.monthly",
    });
    for (const entry of conceptData) {
      const offer = availability(entry, "hosted");
      if (offer.kind === "fetch") expect(entry.snapshot, entry.id).toBe(true);
    }
  });

  it("fetches every concept in local mode, the local app", () => {
    for (const entry of conceptData.filter((c) => c.parameters.length === 0)) {
      expect(availability(entry, "local"), entry.id).toEqual({ kind: "fetch" });
    }
  });

  it("gives the Python call for a concept with parameters, on any server", () => {
    const sep = concept("us.sep.unemployment");
    for (const mode of ["hosted", "local"] as const) {
      const offer = availability(sep, mode);
      expect(offer.kind).toBe("parameters");
      if (offer.kind === "parameters") {
        expect(offer.snippet).toMatch(/^pyeconomics\.data\.get\("us\.sep\.unemployment", parameters=\{"meeting": "[^"]+", "year": "[^"]+"\}\)$/);
      }
    }
  });
});

describe("transforms", () => {
  it("offers yoy only for month-based series and convert only to a lower frequency", () => {
    expect(transformsFor("monthly", "series")).toEqual([...SERIES_TRANSFORMS]);
    expect(transformsFor("daily", "series")).not.toContain("yoy");
    expect(transformsFor("daily", "series")).toContain("convert");
    expect(transformsFor("annual", "series")).toEqual(["pct_change", "yoy", "diff", "lag", "log"]);
    expect(transformsFor("monthly", "table")).toEqual([]);
    expect(convertTargets("monthly")).toEqual(["quarterly", "semiannual", "annual"]);
    expect(convertTargets("business_daily")).toEqual(["monthly", "quarterly", "semiannual", "annual"]);
    expect(convertTargets("annual")).toEqual([]);
  });

  it("writes each transform as core/transforms.py's canonical text", () => {
    expect(transformText({ name: "" })).toBe("");
    expect(transformText({ name: "yoy" })).toBe("yoy");
    expect(transformText({ name: "log" })).toBe("log");
    expect(transformText({ name: "pct_change", periods: 1 })).toBe("pct_change");
    expect(transformText({ name: "pct_change", periods: 12 })).toBe("pct_change(periods=12)");
    expect(transformText({ name: "diff", periods: 3 })).toBe("diff(periods=3)");
    expect(transformText({ name: "lag" })).toBe("lag");
    expect(transformText({ name: "convert", to: "quarterly", method: "mean" })).toBe("convert(to=quarterly,method=mean)");
    expect(() => transformText({ name: "diff", periods: 0 })).toThrow(/periods/);
    expect(() => transformText({ name: "diff", periods: 1001 })).toThrow(/periods/);
    expect(() => transformText({ name: "convert", to: "weekly" })).toThrow(/convert/);
  });
});

describe("the request", () => {
  it("opens on a window ending today, sized by frequency", () => {
    const today = new Date("2026-11-03T12:00:00Z");
    expect(defaultRange("monthly", today)).toEqual({ start: "2016-11-03", end: "2026-11-03" });
    expect(defaultRange("business_daily", today)).toEqual({ start: "2024-11-03", end: "2026-11-03" });
    expect(defaultRange("irregular", today)).toEqual({ start: "", end: "2026-11-03" });
  });

  it("names the series route and asks only for what is given, each checked", () => {
    expect(seriesPath("us.unemployment.rate")).toBe("/v1/series/us.unemployment.rate");
    expect(() => seriesPath("fred:UNRATE")).toThrow(/not a concept id/);
    expect(seriesQuery({})).toEqual({});
    expect(seriesQuery({ start: "2020-01-01", end: "2020-12-31", transform: "yoy", format: "csv" })).toEqual({
      start: "2020-01-01",
      end: "2020-12-31",
      transform: "yoy",
      format: "csv",
    });
    expect(seriesQuery({ format: "json" })).toEqual({});
    expect(() => seriesQuery({ start: "01/01/2020" })).toThrow(/date/);
    expect(() => seriesQuery({ start: "2021-01-01", end: "2020-01-01" })).toThrow(/after/);
    expect(() => seriesQuery({ format: "bundle" as never })).toThrow(/series format/);
  });

  it("gets the series route through the generated client and keeps the bytes", async () => {
    const seen: Request[] = [];
    const body = new TextEncoder().encode(JSON.stringify(DOCUMENT));
    const fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      seen.push(new Request(input, init));
      return new Response(body, {
        status: 200,
        headers: { "Content-Type": "text/csv", "Content-Disposition": 'attachment; filename="us.unemployment.rate.csv"' },
      });
    }) as typeof globalThis.fetch;
    const answer = await getSeries("us.unemployment.rate", { start: "2024-01-01", transform: "diff(periods=1)", format: "csv" }, { baseUrl: "http://127.0.0.1:1", fetch });
    expect(seen.at(0)?.method).toBe("GET");
    expect(seen.at(0)?.url).toBe("http://127.0.0.1:1/v1/series/us.unemployment.rate?start=2024-01-01&transform=diff(periods%3D1)&format=csv");
    expect(answer.bytes).toEqual(body);
    expect(answer.filename).toBe("us.unemployment.rate.csv");
  });

  it("reads the server's mode once, and takes anything but local mode as hosted", async () => {
    const answer = (body: unknown, status = 200) =>
      (async () => new Response(JSON.stringify(body), { status })) as unknown as typeof globalThis.fetch;
    forgetServerMode();
    expect(await serverMode(answer({ mode: "local" }))).toBe("local");
    expect(await serverMode(answer({ mode: "hosted" }))).toBe("local");
    forgetServerMode();
    expect(await serverMode(answer({ mode: "hosted" }))).toBe("hosted");
    forgetServerMode();
    expect(await serverMode(answer({ mode: "library" }))).toBe("hosted");
    forgetServerMode();
    expect(await serverMode(answer({}, 404))).toBe("hosted");
    forgetServerMode();
    expect(await serverMode((async () => Promise.reject(new Error("offline"))) as unknown as typeof globalThis.fetch)).toBe("hosted");
    forgetServerMode();
  });
});

describe("the chart", () => {
  it("parses a series document and refuses anything else", () => {
    expect(parseSeries(JSON.stringify(DOCUMENT)).frame.index).toHaveLength(2);
    expect(() => parseSeries('{"model_id": "a.b"}')).toThrow(/not a series document/);
  });

  it("draws the attribution and the as-of date on the chart, as escaped text", () => {
    expect(chartNote(DOCUMENT)).toBe("Source: U.S. Bureau of Labor Statistics <BLS> & partners. Data as of 2026-11-02.");
    const figure = seriesFigure(DOCUMENT);
    expect(figure.data).toEqual([
      { type: "scatter", mode: "lines", x: DOCUMENT.frame.index, y: [0.037, null], name: "Unemployment rate", connectgaps: false },
    ]);
    const [note] = figure.layout.annotations;
    expect(note?.text).toBe("Source: U.S. Bureau of Labor Statistics &lt;BLS&gt; &amp; partners. Data as of 2026-11-02.");
    expect(note?.text).not.toMatch(/<(?!br>)/);
    expect(figure.layout.yaxis.title.text).toBe("Decimal");
  });

  it("charts a table's chosen column", () => {
    const table: SeriesDocument = {
      ...DOCUMENT,
      frame: {
        type: "table",
        meta: { title: "Par curve", frequency: "business_daily" },
        index: ["2026-01-02"],
        columns: [
          { name: "1y", unit: { text: "Decimal" } },
          { name: "10y", unit: { text: "Decimal" } },
        ],
        data: [[0.04], [0.045]],
      },
    };
    const figure = seriesFigure(table, 1);
    expect(figure.data[0]?.y).toEqual([0.045]);
    expect(figure.layout.title.text).toBe("Par curve: 10y");
  });

  it("breaks a long note into lines at spaces and dates by the real-time period first", () => {
    const lines = plotlyLines("word ".repeat(60), 50);
    expect(lines.every((line) => line.length <= 50)).toBe(true);
    expect(lines.join(" ")).toBe("word ".repeat(60).trim());
    const vintage = { ...DOCUMENT, sources: [{ ...DOCUMENT.sources[0], realtime: { realtime_start: "2025-06-01" } }] } as SeriesDocument;
    expect(chartNote(vintage)).toMatch(/Data as of 2025-06-01\.$/);
  });
});
