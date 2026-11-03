// web/src/components/explorer/SeriesExplorer.tsx
// A concept's chart and downloads (Phase 5 Step 9; ADR-0013 decision 11),
// hydrated when it scrolls into view. A concept the hosted snapshot serves is
// read through GET /v1/series/<concept> on the site's own origin, over a date
// range and with one of the catalog's own transforms; a concept it does not
// serve gives the local command instead of a fetch, unless the server says
// it runs in local mode (GET /version: the local app, Step 10), where every
// concept is offered; a concept that needs parameters gives the Python call,
// which the series route does not take. The chart is one line drawn by
// Plotly.js's basic bundle (src/lib/plotly.ts), with the source's attribution
// and as-of date drawn on it and repeated beneath it; the sources follow
// (ResultPanel's Source), and every download is the same request with
// ?format=, so each file carries its attributions. Nothing the server sent is
// rendered as HTML, and nothing is kept in storage or the URL.
import { useEffect, useRef, useState } from "react";

import ProblemPanel, { type ProblemDocument } from "@/components/calculator/ProblemPanel";
import { Source } from "@/components/calculator/ResultPanel";
import { buttonVariants } from "@/components/ui/button";
import {
  CONVERT_METHODS,
  LOCAL_APP,
  MAX_PERIODS,
  TRANSFORM_LABELS,
  availability,
  chartNote,
  columnsOf,
  convertTargets,
  defaultRange,
  parseSeries,
  seriesFigure,
  transformText,
  transformsFor,
  type Availability,
  type ConvertMethod,
  type SeriesDocument,
  type SeriesFormat,
  type TransformChoice,
  type TransformName,
} from "@/lib/explorer";
import { STYLE_MARKER, loadPlotly } from "@/lib/plotly";
import { decode } from "@/lib/results";
import type { RunAnswer } from "@/lib/run-request";
import { getSeries, serverMode } from "@/lib/series-request";

export interface SeriesExplorerProps {
  conceptId: string;
  frequency: string;
  shape: string;
  /** Whether the hosted snapshot serves the concept. */
  snapshot: boolean;
  parameters: { name: string; example: string }[];
  /** Whether a read needs both a start and an end date. */
  needsWindow: boolean;
  localCommand: string;
  /** Data providers' names by id, for the sources. */
  sourceNames: Record<string, string>;
  /** The problems that point to local mode (problems.json). */
  localSlugs: string[];
}

/** The downloads beside a chart, each the same request with ?format=. */
const DOWNLOADS: readonly { format: Exclude<SeriesFormat, "json">; label: string; extension: string }[] = [
  { format: "csv", label: "CSV", extension: "csv" },
  { format: "xlsx", label: "XLSX", extension: "xlsx" },
  { format: "parquet", label: "Parquet", extension: "parquet" },
  { format: "arrow", label: "Arrow", extension: "arrow" },
];

const CONTROL =
  "rounded-md border border-input bg-transparent px-3 py-1.5 text-sm shadow-xs focus-visible:border-ring " +
  "focus-visible:ring-[3px] focus-visible:ring-ring/50 outline-none";
const SMALL_BUTTON = buttonVariants({ variant: "outline", size: "sm" });

type Outcome =
  | { kind: "series"; answer: RunAnswer; document: SeriesDocument }
  | { kind: "problem"; answer: RunAnswer; problem: ProblemDocument }
  | { kind: "error"; message: string };

interface Sent {
  start: string;
  end: string;
  transform: string;
}

/** Hand bytes to the browser as a file to save. */
function save(bytes: Uint8Array, filename: string, type: string): void {
  const url = URL.createObjectURL(new Blob([bytes.slice()], { type: type || "application/octet-stream" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function problemOf(answer: RunAnswer): ProblemDocument {
  try {
    const parsed: unknown = JSON.parse(decode(answer.bytes));
    return typeof parsed === "object" && parsed !== null ? (parsed as ProblemDocument) : {};
  } catch {
    return {};
  }
}

function filename(conceptId: string, extension: string): string {
  return `${conceptId.replaceAll(".", "_")}.${extension}`;
}

function SeriesChart({ document: series, column }: { document: SeriesDocument; column: number }) {
  const root = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const note = chartNote(series);

  useEffect(() => {
    const element = root.current;
    if (!element) return undefined;
    let cancelled = false;
    let plotly: Awaited<ReturnType<typeof loadPlotly>> | null = null;
    const figure = seriesFigure(series, column);
    loadPlotly()
      .then(async (loaded) => {
        if (cancelled) return;
        plotly = loaded;
        await loaded.newPlot(element, figure.data as never, { ...figure.layout, autosize: true }, {
          displayModeBar: false,
          responsive: true,
        });
      })
      .catch((error: unknown) => {
        if (!cancelled) setFailed(error instanceof Error ? error.message : String(error));
      });
    return () => {
      cancelled = true;
      plotly?.purge(element);
    };
  }, [series, column]);

  const name = columnsOf(series.frame).at(column) ?? series.frame.meta.title;
  return (
    <figure className="flex flex-col gap-2" data-series-chart="">
      <div ref={root} className="min-h-96 w-full" role="img" aria-label={`Chart: ${name}. ${note}`} />
      <figcaption className="text-sm text-muted-foreground" data-chart-note="">
        {note}
        {failed && <span className="block">The chart could not be drawn: {failed}</span>}
      </figcaption>
    </figure>
  );
}

function TransformPicker({
  choice,
  names,
  frequency,
  onChange,
}: {
  choice: TransformChoice;
  names: readonly TransformName[];
  frequency: string;
  onChange: (choice: TransformChoice) => void;
}) {
  const targets = convertTargets(frequency);
  return (
    <div className="flex flex-wrap items-end gap-4">
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">Transform</span>
        <select
          className={CONTROL}
          value={choice.name}
          onChange={(event) => {
            const name = event.target.value as TransformName | "";
            onChange(name === "convert" ? { name, to: targets[0], method: "mean" } : { name, periods: 1 });
          }}
        >
          <option value="">None: the series as published</option>
          {names.map((name) => (
            <option key={name} value={name}>
              {`${TRANSFORM_LABELS.get(name) ?? name} (${name})`}
            </option>
          ))}
        </select>
      </label>
      {(choice.name === "pct_change" || choice.name === "diff" || choice.name === "lag") && (
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">Periods back</span>
          <input
            className={`${CONTROL} w-28`}
            type="number"
            min={1}
            max={MAX_PERIODS}
            step={1}
            value={choice.periods ?? 1}
            onChange={(event) => onChange({ ...choice, periods: Number(event.target.value) })}
          />
        </label>
      )}
      {choice.name === "convert" && (
        <>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">To</span>
            <select className={CONTROL} value={choice.to} onChange={(event) => onChange({ ...choice, to: event.target.value })}>
              {targets.map((target) => (
                <option key={target} value={target}>
                  {target}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">Method</span>
            <select
              className={CONTROL}
              value={choice.method}
              onChange={(event) => onChange({ ...choice, method: event.target.value as ConvertMethod })}
            >
              {CONVERT_METHODS.map((method) => (
                <option key={method} value={method}>
                  {method.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
        </>
      )}
    </div>
  );
}

export default function SeriesExplorer(props: SeriesExplorerProps) {
  const concept = {
    id: props.conceptId,
    snapshot: props.snapshot,
    parameters: props.parameters,
    local_command: props.localCommand,
  };
  // What the snapshot serves, or what needs parameters, is decided at once;
  // anything else waits for the server to say whether it runs locally.
  const [offer, setOffer] = useState<Availability | null>(() =>
    concept.snapshot || concept.parameters.length > 0 ? availability(concept, "hosted") : null,
  );
  const [range, setRange] = useState(() => ({ start: "", end: "" }));
  const [choice, setChoice] = useState<TransformChoice>({ name: "" });
  const [column, setColumn] = useState(0);
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [sent, setSent] = useState<Sent | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const names = transformsFor(props.frequency, props.shape);

  useEffect(() => {
    setRange(defaultRange(props.frequency, new Date()));
    setHydrated(true);
  }, [props.frequency]);

  useEffect(() => {
    if (offer !== null) return undefined;
    let current = true;
    void serverMode().then((mode) => {
      if (current) setOffer(availability(concept, mode));
    });
    return () => {
      current = false;
    };
  });

  const read = async () => {
    let transform: string;
    try {
      transform = transformText(choice);
    } catch (error) {
      setAnnouncement(error instanceof Error ? error.message : String(error));
      return;
    }
    if (props.needsWindow && (!range.start || !range.end)) {
      setAnnouncement("This series needs both a start and an end date.");
      return;
    }
    const request: Sent = { start: range.start, end: range.end, transform };
    setBusy(true);
    setAnnouncement("Reading the series…");
    try {
      const answer = await getSeries(props.conceptId, request);
      setSent(request);
      if (answer.ok) {
        const document = parseSeries(decode(answer.bytes));
        setColumn(0);
        setOutcome({ kind: "series", answer, document });
        setAnnouncement(`Done: ${String(document.frame.index.length)} observations.`);
      } else {
        const problem = problemOf(answer);
        setOutcome({ kind: "problem", answer, problem });
        setAnnouncement(`The series could not be read: ${typeof problem.title === "string" ? problem.title : `HTTP ${String(answer.status)}`}.`);
      }
    } catch (error) {
      setOutcome({ kind: "error", message: error instanceof Error ? error.message : String(error) });
      setAnnouncement("The series could not reach the server.");
    } finally {
      setBusy(false);
    }
  };

  const download = async (format: Exclude<SeriesFormat, "json">, extension: string) => {
    if (!sent) return;
    setAnnouncement(`Preparing the ${format} download…`);
    try {
      const answer = await getSeries(props.conceptId, { ...sent, format });
      if (!answer.ok) {
        setOutcome({ kind: "problem", answer, problem: problemOf(answer) });
        setAnnouncement("The download failed.");
        return;
      }
      save(answer.bytes, answer.filename ?? filename(props.conceptId, extension), answer.contentType);
      setAnnouncement(`The ${format} download is ready.`);
    } catch {
      setAnnouncement("The download could not reach the server.");
    }
  };

  return (
    <div
      className="flex flex-col gap-6"
      data-series-explorer={props.conceptId}
      data-ready={offer ? offer.kind : "pending"}
      data-hydrated={hydrated ? "true" : "false"}
    >
      {/* Plotly reads this before it would inject a <style> element (src/lib/plotly.ts). */}
      <div id={STYLE_MARKER.id} className={STYLE_MARKER.className} hidden />
      {offer === null && <p className="text-sm">Checking what this server serves…</p>}
      {offer?.kind === "parameters" && (
        <div className="flex flex-col gap-2" data-offer="parameters">
          <p className="max-w-3xl">
            This concept takes {props.parameters.map((p) => p.name).join(" and ")}, which the series route does not. Read it
            with the Python package:
          </p>
          <pre className="overflow-x-auto rounded-md bg-muted px-4 py-3 text-sm" role="region" tabIndex={0} aria-label="Python call">
            <code>{offer.snippet}</code>
          </pre>
        </div>
      )}
      {offer?.kind === "local" && (
        <div className="flex flex-col gap-2" data-offer="local">
          <p className="max-w-3xl">
            The hosted site does not serve this concept: none of its sources is both hosted-safe and kept in the daily
            snapshot. Read it on your own computer, with your own keys where a source needs one:
          </p>
          <pre className="overflow-x-auto rounded-md bg-muted px-4 py-3 text-sm" role="region" tabIndex={0} aria-label="Local command">
            <code>{offer.command}</code>
          </pre>
          <p className="max-w-3xl text-sm">
            Or run this site locally, with every source: <code>{LOCAL_APP}</code>.
          </p>
        </div>
      )}
      {offer?.kind === "fetch" && (
        <form
          className="flex flex-col gap-4 rounded-md border p-4"
          aria-label="Read the series"
          onSubmit={(event) => {
            event.preventDefault();
            void read();
          }}
        >
          <div className="flex flex-wrap items-end gap-4">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">From{props.needsWindow ? "" : " (optional)"}</span>
              <input
                className={CONTROL}
                type="date"
                value={range.start}
                required={props.needsWindow}
                onChange={(event) => setRange({ ...range, start: event.target.value })}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">To{props.needsWindow ? "" : " (optional)"}</span>
              <input
                className={CONTROL}
                type="date"
                value={range.end}
                required={props.needsWindow}
                onChange={(event) => setRange({ ...range, end: event.target.value })}
              />
            </label>
          </div>
          {names.length > 0 ? (
            <TransformPicker choice={choice} names={names} frequency={props.frequency} onChange={setChoice} />
          ) : (
            <p className="text-sm text-muted-foreground">
              {props.shape === "table" ? "A table takes no transform; download it whole, or chart one column." : null}
            </p>
          )}
          <div>
            <button type="submit" className={buttonVariants()} disabled={busy}>
              {busy ? "Reading…" : "Draw the chart"}
            </button>
          </div>
        </form>
      )}

      <p role="status" aria-live="polite" className="text-sm">
        {announcement}
      </p>

      {outcome?.kind === "series" && (
        <section className="flex flex-col gap-4" aria-label="The series">
          {outcome.document.frame.type === "table" && (
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">Column</span>
              <select className={CONTROL} value={column} onChange={(event) => setColumn(Number(event.target.value))}>
                {columnsOf(outcome.document.frame).map((name, index) => (
                  <option key={name} value={index}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <SeriesChart document={outcome.document} column={column} />
          <div className="flex flex-col gap-2">
            <h3 className="font-medium">Download</h3>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className={SMALL_BUTTON}
                onClick={() => save(outcome.answer.bytes, filename(props.conceptId, "json"), "application/json")}
              >
                JSON
              </button>
              {DOWNLOADS.map((entry) => (
                <button key={entry.format} type="button" className={SMALL_BUTTON} onClick={() => void download(entry.format, entry.extension)}>
                  {entry.label}
                </button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">Every file carries the data's attributions, notices and source records.</p>
          </div>
          <div className="flex flex-col gap-2">
            <h3 className="font-medium">Sources</h3>
            <ul className="flex flex-col gap-2 text-sm">
              {outcome.document.sources.map((record, index) => (
                <Source key={`${record.provider}-${record.series_id}-${String(index)}`} record={record} names={props.sourceNames} />
              ))}
            </ul>
          </div>
        </section>
      )}
      {outcome?.kind === "problem" && (
        <ProblemPanel
          problem={outcome.problem}
          status={outcome.answer.status}
          retryAfter={outcome.answer.retryAfter}
          localSlugs={props.localSlugs}
          localCommand={props.localCommand}
        />
      )}
      {outcome?.kind === "error" && <p>The series could not reach the server: {outcome.message}</p>}
    </div>
  );
}
