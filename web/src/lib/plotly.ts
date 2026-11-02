// web/src/lib/plotly.ts
// Plotly.js for the calculators' charts (ADR-0013 decisions 8 and 9): the
// basic bundle (scatter, bar and pie) and plotly.css, both from the plotly.js
// package's dist/ at the version the [plot] extra's Plotly bundles
// (mcp/apps.py PLOTLY_JS_VERSION; a test holds the two equal). Neither loads
// until a chart first renders: the stylesheet as a same-origin <link>, the
// bundle as a dynamic import. The page already holds the no-inline-styles
// marker (#plotly.js-style-global, in the calculator), so Plotly injects no
// <style> element and the policy needs no 'unsafe-inline'.
import stylesheet from "plotly.js/dist/plotly.css?url";

import type { Figure } from "@/lib/figure";

/** The id and class Plotly reads before it would inject a style element. */
export const STYLE_MARKER = { id: "plotly.js-style-global", className: "no-inline-styles" } as const;

/** What the calculator calls of Plotly. */
export interface Plotly {
  newPlot(root: HTMLElement, data: Figure["data"], layout: object, config: object): Promise<unknown>;
  purge(root: HTMLElement): void;
}

let loading: Promise<Plotly> | null = null;

function linkStylesheet(): void {
  if (document.querySelector(`link[data-plotly]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = stylesheet;
  link.dataset.plotly = "";
  document.head.append(link);
}

/** Load Plotly.js and its stylesheet once, on the first chart. */
export function loadPlotly(): Promise<Plotly> {
  loading ??= (async () => {
    if (!document.getElementById(STYLE_MARKER.id)) {
      throw new Error("the page lacks Plotly's no-inline-styles marker");
    }
    linkStylesheet();
    const module = (await import("plotly.js/dist/plotly-basic.min.js")) as { default?: Plotly } & Partial<Plotly>;
    return (module.default ?? module) as Plotly;
  })();
  return loading;
}
