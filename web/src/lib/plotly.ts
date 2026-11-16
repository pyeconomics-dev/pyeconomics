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

import { parseColour } from "@/lib/contrast";
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

/** The tokens a chart reads, with any they refer to. */
const CHART_TOKENS = ["foreground", "muted-foreground", "border", "border-strong", "link", "primary", "eyebrow", "font-text"];

/**
 * A figure's layout in the site's theme (Phase 5 Step 17): a transparent
 * background, so the chart sits on its card in light and dark (round 0 found a
 * white box on the dark theme), and the text, grid and line colours read from
 * the design tokens. Plotly takes rgb(), not oklch(), so each token is
 * converted (src/lib/contrast.ts). Only colours change: the data, the titles
 * and the annotations' text stay the figure's own.
 */
export function themed(layout: Record<string, unknown>, root: Element = document.documentElement): Record<string, unknown> {
  const style = getComputedStyle(root);
  const tokens = new Map(CHART_TOKENS.map((name) => [name, style.getPropertyValue(`--${name}`).trim()]));
  const colour = (name: string): string => {
    try {
      const { r, g, b, a } = parseColour(tokens.get(name) ?? "", tokens);
      return `rgba(${String(Math.round(r * 255))}, ${String(Math.round(g * 255))}, ${String(Math.round(b * 255))}, ${String(a)})`;
    } catch {
      return "";
    }
  };
  const foreground = colour("foreground");
  const muted = colour("muted-foreground");
  const axis = (value: unknown) => {
    const given = (value ?? {}) as Record<string, unknown>;
    const title = (given.title ?? {}) as Record<string, unknown>;
    return {
      ...given,
      gridcolor: colour("border"),
      linecolor: colour("border-strong"),
      zerolinecolor: colour("border-strong"),
      tickfont: { ...((given.tickfont ?? {}) as object), color: muted },
      title: { ...title, font: { ...((title.font ?? {}) as object), color: foreground } },
    };
  };
  const annotations = Array.isArray(layout.annotations)
    ? (layout.annotations as Record<string, unknown>[]).map((note) => ({
        ...note,
        font: { ...((note.font ?? {}) as object), color: muted },
      }))
    : layout.annotations;
  const title = (layout.title ?? {}) as Record<string, unknown>;
  return {
    ...layout,
    paper_bgcolor: "rgba(0, 0, 0, 0)",
    plot_bgcolor: "rgba(0, 0, 0, 0)",
    font: { ...((layout.font ?? {}) as object), family: tokens.get("font-text") ?? "", color: foreground },
    title: { ...title, font: { ...((title.font ?? {}) as object), color: foreground } },
    colorway: [colour("link"), colour("primary"), colour("eyebrow"), muted].filter(Boolean),
    xaxis: axis(layout.xaxis),
    yaxis: axis(layout.yaxis),
    ...(annotations === undefined ? {} : { annotations }),
  };
}
