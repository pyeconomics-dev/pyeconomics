// web/src/lib/explorer.ts
// What the data explorer derives (Phase 5 Step 9; ADR-0013 decision 11), as
// pure functions the pages, the islands and the tests share: each concept's
// search entry and its search over title, id, unit, frequency and topic;
// whether a concept is fetched here, needs a parameter, or is read locally
// (hosted mode offers only what the snapshot serves; local mode, Step 10,
// every concept); the transforms a concept's frequency allows, written as the
// text core/transforms.py parses; the default date range; the series route's
// path and query; and the chart: one line, with the source's attribution and
// as-of date drawn on it. Nothing here reads the network or storage.
import { conceptPath, isConceptId } from "@/lib/paths";
import type { SourceRecord } from "@/lib/results";
import type { ConceptEntry, ModelEntry } from "@/lib/site-data";

/** A concept as the /data/ search lists it: small, for the island's props. */
export interface ConceptListing {
  id: string;
  title: string;
  unit: string;
  frequency: string;
  topic: string;
  /** Whether the hosted site serves it from the snapshot. */
  snapshot: boolean;
  /** Whether it needs parameters, which only the Python API takes. */
  parameters: boolean;
  path: string;
}

/** The /data/ search's filters. */
export interface ConceptQuery {
  text: string;
  frequency: string;
  topic: string;
  /** Only the concepts the hosted site serves. */
  served: boolean;
}

/** Where the explorer runs: the hosted site, or the local app (Step 10). */
export type ExplorerMode = "hosted" | "local";

/** What a concept page offers. */
export type Availability =
  | { kind: "fetch" }
  | { kind: "parameters"; snippet: string }
  | { kind: "local"; command: string };

/** The transforms data.get applies to one series (core/transforms.py SERIES_TRANSFORMS). */
export const SERIES_TRANSFORMS = ["pct_change", "yoy", "diff", "lag", "log", "convert"] as const;
export type TransformName = (typeof SERIES_TRANSFORMS)[number];

/** The frequencies a series may be converted to, by months in a period. */
const MONTHS: ReadonlyMap<string, number> = new Map([
  ["monthly", 1],
  ["quarterly", 3],
  ["semiannual", 6],
  ["annual", 12],
]);

/** The ways a period's observations combine when converting. */
export const CONVERT_METHODS = ["mean", "sum", "first", "last", "period_end"] as const;
export type ConvertMethod = (typeof CONVERT_METHODS)[number];

/** A transform picked in the explorer: none, or one with its arguments. */
export interface TransformChoice {
  name: TransformName | "";
  periods?: number;
  to?: string;
  method?: ConvertMethod;
}

/** The words for each transform in the picker. */
export const TRANSFORM_LABELS: ReadonlyMap<TransformName, string> = new Map([
  ["pct_change", "Change, as a decimal"],
  ["yoy", "Year-over-year change"],
  ["diff", "Difference"],
  ["lag", "Earlier value (lag)"],
  ["log", "Natural logarithm"],
  ["convert", "Convert the frequency"],
]);

/** The most observations a periods argument reaches back (core/transforms.py). */
export const MAX_PERIODS = 1000;

/** The local app: the whole catalog on your own keys (ADR-0013 decision 16). */
export const LOCAL_APP = 'pip install "pyeconomics[app]" then pyeconomics serve';

/** Order by id as Python sorts text (by code point), so pages and lists agree with concepts.json. */
function byId(a: { id: string }, b: { id: string }): number {
  return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}

/** Each concept's search entry, sorted by id. */
export function conceptListings(concepts: readonly ConceptEntry[]): ConceptListing[] {
  return [...concepts]
    .sort(byId)
    .map((concept) => ({
      id: concept.id,
      title: concept.title,
      unit: concept.unit ?? concept.unit_kind ?? "",
      frequency: concept.frequency,
      topic: concept.section,
      snapshot: concept.snapshot,
      parameters: concept.parameters.length > 0,
      path: conceptPath(concept.id),
    }));
}

function tokens(text: string): string[] {
  return text
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((token) => token.length >= 2);
}

/** How well a concept matches the search words: title and id words count most. */
export function score(concept: ConceptListing, words: readonly string[]): number {
  const title = concept.title.toLowerCase();
  const id = concept.id.replaceAll(/[._]/g, " ");
  let total = 0;
  for (const word of words) {
    if (title.includes(word) || id.includes(word)) total += 3;
    if (title.startsWith(word)) total += 2;
    if (concept.topic.toLowerCase().includes(word)) total += 1;
    if (concept.unit.toLowerCase().includes(word)) total += 1;
    if (concept.frequency.replaceAll("_", " ").includes(word)) total += 1;
  }
  return total;
}

/**
 * The concepts that match a query, best first; with no words, every concept
 * that passes the filters, in id order. A word must match somewhere for a
 * concept to count.
 */
export function searchConcepts(concepts: readonly ConceptListing[], query: ConceptQuery): ConceptListing[] {
  const words = tokens(query.text);
  const kept = concepts.filter(
    (concept) =>
      (!query.frequency || concept.frequency === query.frequency) &&
      (!query.topic || concept.topic === query.topic) &&
      (!query.served || concept.snapshot),
  );
  if (words.length === 0) return kept;
  return kept
    .map((concept) => ({ concept, value: score(concept, words) }))
    .filter(({ concept, value }) => value > 0 && words.every((word) => score(concept, [word]) > 0))
    .sort((a, b) => b.value - a.value || byId(a.concept, b.concept))
    .map(({ concept }) => concept);
}

/** The values a filter offers, sorted. */
export function facetValues(concepts: readonly ConceptListing[], key: "frequency" | "topic"): string[] {
  return [...new Set(concepts.map((concept) => (key === "frequency" ? concept.frequency : concept.topic)))].sort();
}

/** The Python call that reads a concept with parameters, which the series route does not take. */
export function parameterSnippet(id: string, parameters: readonly { name: string; example: string }[]): string {
  const given = parameters.map(({ name, example }) => `${JSON.stringify(name)}: ${JSON.stringify(example)}`).join(", ");
  return `pyeconomics.data.get(${JSON.stringify(id)}, parameters={${given}})`;
}

/**
 * What a concept page offers. A concept that needs parameters is read with
 * the Python API on any server; otherwise hosted mode fetches only what the
 * snapshot serves and gives the local command for the rest, and local mode
 * fetches every concept.
 */
export function availability(
  concept: Pick<ConceptEntry, "id" | "snapshot" | "parameters" | "local_command">,
  mode: ExplorerMode,
): Availability {
  if (concept.parameters.length > 0) return { kind: "parameters", snippet: parameterSnippet(concept.id, concept.parameters) };
  if (mode === "hosted" && !concept.snapshot) return { kind: "local", command: concept.local_command };
  return { kind: "fetch" };
}

/** The models whose bindings read a concept, sorted by title. */
export function modelsReading(conceptId: string, models: readonly ModelEntry[]): ModelEntry[] {
  return models
    .filter((model) => Array.isArray(model.bindings) && model.bindings.some((binding) => isBindingOf(binding, conceptId)))
    .sort((a, b) => a.title.localeCompare(b.title));
}

function isBindingOf(binding: unknown, conceptId: string): boolean {
  return typeof binding === "object" && binding !== null && (binding as { concept?: unknown }).concept === conceptId;
}

/** The frequencies a series of this frequency may be converted to: lower ones only. */
export function convertTargets(frequency: string): string[] {
  const own = MONTHS.get(frequency) ?? 0;
  return [...MONTHS.entries()].filter(([, months]) => months > own).map(([name]) => name);
}

/** The transforms a concept offers: none for a table; yoy only for month-based series. */
export function transformsFor(frequency: string, shape: string): TransformName[] {
  if (shape !== "series") return [];
  return SERIES_TRANSFORMS.filter((name) => {
    if (name === "yoy") return MONTHS.has(frequency);
    if (name === "convert") return convertTargets(frequency).length > 0;
    return true;
  });
}

/** A transform's text, as core/transforms.py writes it canonically; "" for none. */
export function transformText(choice: TransformChoice): string {
  switch (choice.name) {
    case "":
      return "";
    case "pct_change":
    case "diff":
    case "lag": {
      const periods = Math.trunc(choice.periods ?? 1);
      if (!Number.isFinite(periods) || periods < 1 || periods > MAX_PERIODS) {
        throw new Error(`periods is a whole number from 1 to ${String(MAX_PERIODS)}`);
      }
      return periods === 1 ? choice.name : `${choice.name}(periods=${String(periods)})`;
    }
    case "convert": {
      if (!choice.to || !MONTHS.has(choice.to)) throw new Error("convert needs a frequency to convert to");
      return `convert(to=${choice.to},method=${choice.method ?? "mean"})`;
    }
    default:
      return choice.name;
  }
}

/** A date as YYYY-MM-DD, in UTC. */
export function isoDay(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/**
 * The window the explorer opens with: years back from today, by frequency,
 * ending today, so it ends at the latest observation (a series served by
 * window, such as Treasury's curves, needs both ends). An irregular series
 * opens on its whole history.
 */
export function defaultRange(frequency: string, today: Date): { start: string; end: string } {
  const years = new Map([
    ["daily", 2],
    ["business_daily", 2],
    ["weekly", 5],
    ["biweekly", 5],
    ["monthly", 10],
    ["quarterly", 30],
    ["semiannual", 30],
    ["annual", 50],
  ]).get(frequency);
  if (years === undefined) return { start: "", end: isoDay(today) };
  const start = new Date(today);
  start.setUTCFullYear(start.getUTCFullYear() - years);
  return { start: isoDay(start), end: isoDay(today) };
}

/** The formats the series route answers (server/formats.py SERIES_FORMATS). */
export const SERIES_FORMATS = ["json", "csv", "xlsx", "parquet", "arrow"] as const;
export type SeriesFormat = (typeof SERIES_FORMATS)[number];

/** What a series request asks for beside its target. */
export interface SeriesOptions {
  start?: string;
  end?: string;
  transform?: string;
  format?: SeriesFormat;
}

const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** A concept's series route. */
export function seriesPath(id: string): string {
  if (!isConceptId(id)) throw new Error(`${id} is not a concept id`);
  return `/v1/series/${id}`;
}

function checkedDay(value: string, name: string): string {
  if (!DATE.test(value)) throw new Error(`${name} is not a date (YYYY-MM-DD)`);
  return value;
}

/** A series request's query: only the options given, each checked. */
export function seriesQuery(options: SeriesOptions): Record<string, string> {
  const query: Record<string, string> = {};
  if (options.start) query.start = checkedDay(options.start, "start");
  if (options.end) query.end = checkedDay(options.end, "end");
  if (options.start && options.end && options.start > options.end) throw new Error("the start is after the end");
  if (options.transform) query.transform = options.transform;
  if (options.format && options.format !== "json") {
    if (!SERIES_FORMATS.includes(options.format)) throw new Error(`${String(options.format)} is not a series format`);
    query.format = options.format;
  }
  return query;
}

/** One source record of a series document: the record a result's manifest holds. */
export type SeriesRecord = SourceRecord;

/** A series or table frame, as data.get's document holds it. */
export interface Frame {
  type: "series" | "table";
  meta: { title: string; unit?: { text: string }; frequency: string };
  index: string[];
  values?: (number | null)[];
  columns?: { name: string; unit: { text: string } }[];
  data?: (number | null)[][];
}

/** data.get's document (surfaces/documents.py data_document). */
export interface SeriesDocument {
  concept: string | null;
  frame: Frame;
  sources: SeriesRecord[];
  attributions: string[];
}

/** Parse a series answer's bytes. */
export function parseSeries(text: string): SeriesDocument {
  const document = JSON.parse(text) as Partial<SeriesDocument>;
  const frame = document.frame;
  if (!frame || !Array.isArray(frame.index) || !Array.isArray(document.sources)) {
    throw new Error("the answer is not a series document");
  }
  return {
    concept: document.concept ?? null,
    frame,
    sources: document.sources,
    attributions: Array.isArray(document.attributions) ? document.attributions : [],
  };
}

/** A frame's columns: a series' one, or a table's names. */
export function columnsOf(frame: Frame): string[] {
  if (frame.type === "series") return [frame.meta.title];
  return (frame.columns ?? []).map((column) => column.name);
}

/** The values of one column of a frame (a series has one). */
export function valuesOf(frame: Frame, column = 0): (number | null)[] {
  if (frame.type === "series") return frame.values ?? [];
  return frame.data?.at(column) ?? [];
}

/** The date a series' data is as of: a real-time period, a retrieval, or its last observation. */
export function asOfDate(records: readonly SeriesRecord[]): string {
  const record = records.at(0);
  if (!record) return "";
  if (record.realtime?.realtime_start) return record.realtime.realtime_start;
  if (record.retrieved_at) return record.retrieved_at.slice(0, 10);
  return record.observation_end ?? "";
}

/** The note every chart carries: the attributions, and the date the data is as of. */
export function chartNote(document: Pick<SeriesDocument, "attributions" | "sources">): string {
  const texts = document.attributions.length > 0 ? document.attributions : [...new Set(document.sources.map((r) => r.attribution))];
  const date = asOfDate(document.sources);
  return [...texts, date ? `Data as of ${date}.` : ""].filter(Boolean).join(" ");
}

/**
 * Text as Plotly draws it: its pseudo-HTML tags escaped, then broken into
 * lines of at most `width` characters at spaces.
 */
export function plotlyLines(text: string, width = 100): string[] {
  const escaped = text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
  const lines: string[] = [];
  let line = "";
  for (const word of escaped.split(/\s+/).filter(Boolean)) {
    if (line && line.length + 1 + word.length > width) {
      lines.push(line);
      line = word;
    } else {
      line = line ? `${line} ${word}` : word;
    }
  }
  if (line) lines.push(line);
  return lines;
}

/** One line of a series chart. */
export interface SeriesTrace {
  type: "scatter";
  mode: "lines";
  x: string[];
  y: (number | null)[];
  name: string;
  connectgaps: false;
}

/** A series chart: one line, its title and units, and the note drawn below the plot. */
export interface SeriesFigure {
  data: SeriesTrace[];
  layout: {
    title: { text: string };
    xaxis: { title: { text: string } };
    yaxis: { title: { text: string } };
    margin: { t: number; r: number; l: number; b: number };
    annotations: {
      text: string;
      xref: "paper";
      yref: "paper";
      x: number;
      y: number;
      xanchor: "left";
      yanchor: "top";
      showarrow: false;
      align: "left";
      font: { size: number };
    }[];
    showlegend: false;
  };
}

/** The chart of one column of a series document, with its attribution and as-of date drawn on it. */
export function seriesFigure(document: SeriesDocument, column = 0): SeriesFigure {
  const frame = document.frame;
  const name = columnsOf(frame).at(column) ?? frame.meta.title;
  const unit = frame.type === "series" ? (frame.meta.unit?.text ?? "") : (frame.columns?.at(column)?.unit.text ?? "");
  const lines = plotlyLines(chartNote(document));
  return {
    data: [{ type: "scatter", mode: "lines", x: frame.index, y: valuesOf(frame, column), name, connectgaps: false }],
    layout: {
      title: { text: plotlyLines(frame.type === "series" ? frame.meta.title : `${frame.meta.title}: ${name}`, 70).join("<br>") },
      xaxis: { title: { text: "Date" } },
      yaxis: { title: { text: plotlyLines(unit, 40).join("<br>") } },
      margin: { t: 60, r: 20, l: 70, b: 70 + 16 * lines.length },
      annotations: [
        {
          text: lines.join("<br>"),
          xref: "paper",
          yref: "paper",
          x: 0,
          y: -0.18,
          xanchor: "left",
          yanchor: "top",
          showarrow: false,
          align: "left",
          font: { size: 11 },
        },
      ],
      showlegend: false,
    },
  };
}
