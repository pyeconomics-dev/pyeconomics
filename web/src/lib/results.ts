// web/src/lib/results.ts
// How a calculator reads the result bytes it received (ADR-0012 decision 3):
// parsed once for its tables, never re-serialized, so "copy JSON" and the JSON
// download hand over the bytes as the API sent them. The outputs table follows
// the model's output schema (its card's order and units); long arrays are
// shown a page at a time; the sources panel reads the manifest's data_sources,
// one record per bound field (core/provenance.py DataSource).

/** A warning a result carries. */
export interface ResultWarning {
  code: string;
  message: string;
}

/** One data source record of a result's manifest, as far as the page shows it. */
export interface SourceRecord {
  provider: string;
  series_id: string;
  dataset?: string | null;
  concept?: string | null;
  field?: string | null;
  vintage?: string | null;
  realtime?: { realtime_start: string; realtime_end?: string | null } | null;
  observation_start?: string | null;
  observation_end?: string | null;
  transforms?: string[];
  retrieved_at?: string | null;
  licence: string;
  attribution: string;
  notice?: string | null;
  terms_url?: string | null;
  cache_hit?: boolean;
  warnings?: string[];
}

/** A result's canonical JSON, parsed. */
export interface Result {
  model_id: string;
  model_version: number;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  warnings: ResultWarning[];
  manifest: { data_sources?: SourceRecord[] } & Record<string, unknown>;
}

/** The values one page of an array shows. */
export const PAGE_SIZE = 25;

/** The text of a response body, as UTF-8. */
export function decode(bytes: Uint8Array): string {
  return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
}

/** Parse a result's bytes. */
export function parseResult(bytes: Uint8Array): Result {
  const document = JSON.parse(decode(bytes)) as Partial<Result>;
  if (typeof document.model_id !== "string" || typeof document.outputs !== "object" || document.outputs === null) {
    throw new Error("the answer is not a result");
  }
  return {
    model_id: document.model_id,
    model_version: Number(document.model_version),
    inputs: document.inputs ?? {},
    outputs: document.outputs,
    warnings: Array.isArray(document.warnings) ? document.warnings : [],
    manifest: document.manifest ?? {},
  };
}

/** A scalar output as text: a number as JSON writes it, null as undefined. */
export function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "undefined (null)";
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

/** Units whose values are decimals, shown with their percent beside them. */
const PERCENT_UNITS: ReadonlySet<string> = new Set(["rate", "return", "yield"]);

/**
 * A value as the outputs table shows it (Phase 5 Step 17's round 0: raw
 * floats such as 0.10014999999999999 read as noise): a number to ten
 * significant digits, which drops binary rounding's last digits, and a
 * decimal rate, return or yield with its percent beside it. Display only: the
 * result's bytes, "copy JSON" and every download keep the exact values.
 */
export function displayValue(value: unknown, unit = ""): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return formatValue(value);
  const shown = String(Number(value.toPrecision(10)));
  if (!PERCENT_UNITS.has(unit)) return shown;
  return `${shown} (${String(Number((value * 100).toPrecision(8)))}%)`;
}

/** How many pages an array of this length needs. */
export function pageCount(length: number, size = PAGE_SIZE): number {
  return Math.max(1, Math.ceil(length / size));
}

/** One page of an array, with the index of its first value. */
export function pageOf<T>(values: readonly T[], page: number, size = PAGE_SIZE): { start: number; items: T[] } {
  const last = pageCount(values.length, size) - 1;
  const index = Math.min(Math.max(0, page), last);
  return { start: index * size, items: values.slice(index * size, (index + 1) * size) };
}

/** The data sources a result read, from its manifest. */
export function sourceRecords(result: Result): SourceRecord[] {
  const records = result.manifest.data_sources;
  return Array.isArray(records) ? records : [];
}

/**
 * What a run gave, in one line a visitor reads first (Phase 5 Step 18's round
 * 1: nothing said a run had finished, or which data it read): how many outputs
 * and warnings, and, for a run on live data, how many series it read and the
 * date of the latest observation among them.
 */
/** How many outputs a result holds, as its table lists them: a family's calculation is not one. */
export function outputCount(result: Result): number {
  return Object.keys(result.outputs).filter((name) => name !== "calculation").length;
}

export function runSummary(result: Result): string {
  const outputs = outputCount(result);
  const warnings = result.warnings.length;
  const parts = [
    `The run finished: ${String(outputs)} ${outputs === 1 ? "output" : "outputs"}, ` +
      `${warnings === 0 ? "no warnings" : `${String(warnings)} ${warnings === 1 ? "warning" : "warnings"}`}.`,
  ];
  const records = sourceRecords(result);
  if (records.length > 0) {
    const latest = records
      .map((record) => record.observation_end ?? "")
      .filter((date) => date !== "")
      .sort()
      .at(-1);
    parts.push(
      `It read ${String(records.length)} data series` +
        `${latest ? `, with observations to ${latest}` : ""}: each is listed under Sources.`,
    );
  }
  return parts.join(" ");
}

/** One fact of a result's manifest, as the page lists it. */
export interface ManifestFact {
  label: string;
  value: string;
}

/**
 * The manifest's facts a reader checks a result by (core/manifest.py): the
 * model and its version, the package's version, and the SHA-256 of the inputs
 * and of the result. Only strings and numbers the manifest holds; a field it
 * lacks is left out.
 */
export function manifestFacts(result: Result): ManifestFact[] {
  const manifest = new Map(Object.entries(result.manifest));
  const text = (key: string): string | null => {
    const value = manifest.get(key);
    return typeof value === "string" || typeof value === "number" ? String(value) : null;
  };
  const rows: [string, string | null][] = [
    ["Model", `${result.model_id}, version ${String(result.model_version)}`],
    ["pyeconomics version", text("package_version")],
    ["Inputs SHA-256", text("inputs_sha256")],
    ["Result SHA-256", text("result_sha256")],
    ["Manifest schema", text("schema_version")],
    ["Seed", text("seed")],
  ];
  return rows.flatMap(([label, value]) => (value === null ? [] : [{ label, value }]));
}

/** What a data warning code means for a reader (data/cache/policy.py NOTE_WARNINGS and bindings). */
export const DATA_WARNINGS: ReadonlyMap<string, string> = new Map(
  Object.entries({
  revised_data:
    "Revised data: the source keeps only its current estimates, so the values are the latest published, " +
    "not those known on the as-of date.",
  served_offline: "Served from the local cache in offline mode.",
  bls_keyless: "Read from the BLS without its catalog, so the series' unit and seasonal adjustment are not known.",
  served_from_snapshot:
    "Served from the hosted service's daily snapshot of the source, taken at the retrieval time shown, not fetched for this request.",
  stale_snapshot:
    "The snapshot is more than two days old: the source could not be read since, so newer data may exist.",
  }),
);

/** The as-of words of a record: its real-time period, vintage or last observation. */
export function asOfText(record: SourceRecord): string {
  if (record.realtime?.realtime_start) return `as published on ${record.realtime.realtime_start}`;
  if (record.vintage) return `vintage ${record.vintage}`;
  if (record.observation_end) return `observations to ${record.observation_end}`;
  return "latest";
}
