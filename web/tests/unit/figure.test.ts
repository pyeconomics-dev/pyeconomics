// web/tests/unit/figure.test.ts
// The TypeScript port of core/plotting.py's figure_of (src/lib/figure.ts) and
// the Plotly.js it draws with (ADR-0013 decision 8): for every model with a
// chart, figureOf over its example result deep-equals the Python figure
// registry.json carries (example_figure, its first applicable chart), and the
// plotly.js the site installs is the release mcp/apps.py's PLOTLY_JS_VERSION
// names, the one the [plot] extra's Plotly bundles.
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { applicable, chartsFor, figureOf, type ChartSpec } from "@/lib/figure";
import { registryData } from "@/lib/site-data";

const charted = registryData.models.filter((model) => Array.isArray(model.charts) && model.charts.length > 0);

describe("figureOf", () => {
  it("covers the models with charts", () => {
    expect(charted.length).toBeGreaterThanOrEqual(5);
    expect(charted.filter((model) => model.example_figure !== null).length).toBeGreaterThanOrEqual(3);
  });

  for (const model of charted) {
    it(`${model.id}: the example result's figure is example_figure`, () => {
      const charts = model.charts as unknown as ChartSpec[];
      const result = model.example_result as { inputs: Record<string, unknown>; outputs: Record<string, unknown> };
      const first = applicable(charts, result)[0];
      if (first === undefined) {
        expect(model.example_figure).toBeNull();
        return;
      }
      expect(figureOf(charts, result, first.id)).toEqual(model.example_figure);
    });
  }

  const band: ChartSpec = {
    id: "band",
    title: "A band",
    kind: "band",
    x: "t",
    y: ["low", "high", "mid"],
    x_label: null,
    y_label: "",
    calculation: "path",
  };
  const bars: ChartSpec = { ...band, id: "bars", kind: "bar", y: ["mid"], calculation: null, x_label: "Time" };
  const document = { inputs: { calculation: "path" }, outputs: { t: [1, 2], low: [0, 1], high: [2, 3], mid: [1, 2] } };

  it("draws a band's edges, its fill and its lines, labelling the axes as Python does", () => {
    expect(figureOf([band], document)).toEqual({
      data: [
        { type: "scatter", x: [1, 2], y: [0, 1], mode: "lines", line: { width: 0 }, name: "low" },
        { type: "scatter", x: [1, 2], y: [2, 3], mode: "lines", line: { width: 0 }, fill: "tonexty", name: "high" },
        { type: "scatter", x: [1, 2], y: [1, 2], mode: "lines", name: "mid" },
      ],
      layout: {
        title: { text: "A band" },
        xaxis: { title: { text: "t" } },
        yaxis: { title: { text: "low, high, mid" } },
      },
    });
  });

  it("draws bars, and picks charts by calculation", () => {
    expect(chartsFor([band, bars], "other").map((chart) => chart.id)).toEqual(["bars"]);
    const figure = figureOf([band, bars], document, "bars");
    expect(figure.data).toEqual([{ type: "bar", x: [1, 2], y: [1, 2], name: "mid" }]);
    expect(figure.layout.xaxis.title.text).toBe("Time");
  });

  it("refuses as figure_of does: no chart, several unnamed, an unknown one, a missing array", () => {
    expect(() => figureOf([], document)).toThrow(/no chart applies/);
    expect(() => figureOf([band, bars], document)).toThrow(/several charts apply/);
    expect(() => figureOf([band], document, "nope")).toThrow(/no chart nope/);
    expect(() => figureOf([bars], { inputs: {}, outputs: { t: 1, mid: [1] } })).toThrow(/not an array/);
  });
});

describe("Plotly.js", () => {
  const apps = readFileSync(new URL("../../../src/pyeconomics/mcp/apps.py", import.meta.url), "utf8");
  const pinned = /^PLOTLY_JS_VERSION: Final = "([^"]+)"$/m.exec(apps)?.[1];
  const read = (path: string) => JSON.parse(readFileSync(new URL(path, import.meta.url), "utf8")) as Record<string, unknown>;

  it("is the release the [plot] extra's Plotly bundles (mcp/apps.py PLOTLY_JS_VERSION)", () => {
    expect(pinned).toMatch(/^\d+\.\d+\.\d+$/);
    expect((read("../../package.json").devDependencies as Record<string, string>)["plotly.js"]).toBe(pinned);
    expect(read("../../node_modules/plotly.js/package.json").version).toBe(pinned);
  });

  it("ships its basic bundle and its stylesheet from the plotly.js package's dist/", () => {
    const source = readFileSync(new URL("../../src/lib/plotly.ts", import.meta.url), "utf8");
    expect(source).toContain('import("plotly.js/dist/plotly-basic.min.js")');
    expect(source).toContain('from "plotly.js/dist/plotly.css?url"');
    const bundle = readFileSync(new URL("../../node_modules/plotly.js/dist/plotly-basic.min.js", import.meta.url), "utf8");
    expect(bundle.slice(0, 200)).toContain(`plotly.js (basic - minified) v${String(pinned)}`);
    expect(bundle).toContain("no-inline-styles");
  });
});
