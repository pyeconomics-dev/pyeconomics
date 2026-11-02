// web/src/lib/figure.ts
// A TypeScript port of core/plotting.py's figure_of (ADR-0013 decision 8):
// the Plotly figure of one of a model's charts, from a result's JSON document,
// with the same traces and layout keys the Python figure's JSON holds. A test
// holds figureOf(...) deep-equal to each model's example_figure in
// registry.json (the Python figure of its example result, its template
// removed), so the calculator draws what the Python API draws. Pure: Plotly.js
// itself loads only when a chart renders (src/lib/plotly.ts).

/** A model's chart, as registry.json lists it (core/spec.py ChartSpec). */
export interface ChartSpec {
  id: string;
  title: string;
  kind: "line" | "scatter" | "bar" | "band";
  x: string;
  y: string[];
  x_label: string | null;
  y_label: string | null;
  calculation: string | null;
}

/** One Plotly trace: a scatter (line, markers or a band's edge) or a bar. */
export interface Trace {
  type: "scatter" | "bar";
  x: unknown[];
  y: unknown[];
  name: string;
  mode?: "lines" | "markers";
  line?: { width: number };
  fill?: "tonexty";
}

/** A Plotly figure: its traces and layout. */
export interface Figure {
  data: Trace[];
  layout: {
    title: { text: string };
    xaxis: { title: { text: string } };
    yaxis: { title: { text: string } };
  };
}

/** A result's JSON document, as far as a figure reads it. */
export interface ResultDocument {
  inputs: Readonly<Record<string, unknown>>;
  outputs: Readonly<Record<string, unknown>>;
}

/** A model's charts that apply to a calculation, in declared order (charts_for). */
export function chartsFor(charts: readonly ChartSpec[], calculation: unknown): ChartSpec[] {
  return charts.filter((chart) => chart.calculation === null || chart.calculation === calculation);
}

/** The charts that apply to a result. */
export function applicable(charts: readonly ChartSpec[], document: ResultDocument): ChartSpec[] {
  return chartsFor(charts, document.inputs.calculation ?? null);
}

function pick(charts: readonly ChartSpec[], chartId: string | undefined): ChartSpec {
  if (chartId !== undefined) {
    const found = charts.find((chart) => chart.id === chartId);
    if (!found) throw new Error(`no chart ${chartId}; the charts: ${charts.map((c) => c.id).join(", ") || "none"}`);
    return found;
  }
  const [only, ...rest] = charts;
  if (!only) throw new Error("no chart applies to this result");
  if (rest.length > 0) throw new Error(`several charts apply; name one of: ${charts.map((c) => c.id).join(", ")}`);
  return only;
}

function values(outputs: Readonly<Record<string, unknown>>, name: string): unknown[] {
  const found = new Map(Object.entries(outputs)).get(name);
  if (!Array.isArray(found)) throw new Error(`the output ${name} is not an array`);
  return [...found];
}

/**
 * The figure of one chart of a result: `chartId` may be left out when exactly
 * one chart applies. Throws, as figure_of raises, when none or several apply.
 */
export function figureOf(charts: readonly ChartSpec[], document: ResultDocument, chartId?: string): Figure {
  const spec = pick(applicable(charts, document), chartId);
  const { outputs } = document;
  const x = values(outputs, spec.x);
  const data: Trace[] = [];
  let lines = spec.y;
  if (spec.kind === "band") {
    const [lower = "", upper = "", ...rest] = spec.y;
    lines = rest;
    // The upper edge fills down to the lower one; an empty band draws nothing.
    data.push({ type: "scatter", x, y: values(outputs, lower), mode: "lines", line: { width: 0 }, name: lower });
    data.push({
      type: "scatter",
      x,
      y: values(outputs, upper),
      mode: "lines",
      line: { width: 0 },
      fill: "tonexty",
      name: upper,
    });
  }
  for (const name of lines) {
    const y = values(outputs, name);
    if (spec.kind === "bar") {
      data.push({ type: "bar", x, y, name });
    } else {
      data.push({ type: "scatter", x, y, mode: spec.kind === "scatter" ? "markers" : "lines", name });
    }
  }
  return {
    data,
    layout: {
      title: { text: spec.title },
      xaxis: { title: { text: spec.x_label || spec.x } },
      yaxis: { title: { text: spec.y_label || spec.y.join(", ") } },
    },
  };
}
