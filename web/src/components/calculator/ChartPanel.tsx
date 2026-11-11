// web/src/components/calculator/ChartPanel.tsx
// A result's charts (ADR-0013 decision 8): each chart the model declares for
// the result's calculation, drawn by Plotly.js from figureOf's figure, the
// figure the Python API builds. Plotly loads with the first chart
// (src/lib/plotly.ts). The modebar is off: its icon links carry no
// accessible names, and the outputs table beside the chart holds every value.
import { useEffect, useRef, useState } from "react";

import { report } from "@/lib/error-reporting";
import { figureOf, type ChartSpec, type ResultDocument } from "@/lib/figure";
import { loadPlotly } from "@/lib/plotly";

function Chart({ chart, document }: { chart: ChartSpec; document: ResultDocument }) {
  const root = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState<string | null>(null);

  useEffect(() => {
    const element = root.current;
    if (!element) return undefined;
    let cancelled = false;
    let plotly: Awaited<ReturnType<typeof loadPlotly>> | null = null;
    const figure = figureOf([chart], document, chart.id);
    loadPlotly()
      .then(async (loaded) => {
        if (cancelled) return;
        plotly = loaded;
        await loaded.newPlot(element, figure.data, { ...figure.layout, autosize: true }, {
          displayModeBar: false,
          responsive: true,
        });
      })
      .catch((error: unknown) => {
        void report(error, "calculator");
        if (!cancelled) setFailed(error instanceof Error ? error.message : String(error));
      });
    return () => {
      cancelled = true;
      plotly?.purge(element);
    };
  }, [chart, document]);

  return (
    <figure className="flex flex-col gap-2">
      <div ref={root} className="min-h-80 w-full" role="img" aria-label={`Chart: ${chart.title}`} />
      <figcaption className="text-sm text-muted-foreground">
        {chart.title}. Every value is in the outputs table.
        {failed && <span className="block">The chart could not be drawn: {failed}</span>}
      </figcaption>
    </figure>
  );
}

export default function ChartPanel({ charts, document }: { charts: readonly ChartSpec[]; document: ResultDocument }) {
  if (charts.length === 0) return null;
  return (
    <div className="flex flex-col gap-4">
      {charts.map((chart) => (
        <Chart key={chart.id} chart={chart} document={document} />
      ))}
    </div>
  );
}
