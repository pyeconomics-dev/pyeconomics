// web/tests/visual/sample.ts
// What the visual baselines photograph (Phase 5 Step 18): ADR-0013 decision
// 19's thirteen sample pages, at a phone's and a desktop's width, in light and
// in dark. tests/unit/visual-baselines.test.ts holds the pages to Lighthouse's
// sample and the baseline files to this list, on every platform; the pictures
// themselves are compared only where they were drawn (baselines.spec.ts).

/** One sample page and the name its pictures carry. */
export interface SamplePage {
  name: string;
  path: string;
}

/** ADR-0013 decision 19's sample: the pages Lighthouse and axe are held on. */
export const SAMPLE: readonly SamplePage[] = [
  { name: "home", path: "/" },
  { name: "models", path: "/models/" },
  { name: "domain", path: "/models/fixed-income/" },
  { name: "model-bond-pricing", path: "/models/fixed-income/bond-pricing/" },
  { name: "model-time-value", path: "/models/foundations/time-value/" },
  { name: "model-policy-rule", path: "/models/macro/policy-rule/" },
  { name: "model-garch", path: "/models/econometrics/garch/" },
  { name: "data", path: "/data/" },
  { name: "search", path: "/search/" },
  { name: "coverage", path: "/coverage/" },
  { name: "sources", path: "/sources/" },
  { name: "privacy", path: "/legal/privacy/" },
  { name: "problem", path: "/problems/invalid-input/" },
];

/** The two widths: a phone's and a desktop's first screen. */
export const WIDTHS = [
  { width: 390, height: 844 },
  { width: 1440, height: 900 },
] as const;

export const THEMES = ["light", "dark"] as const;

/** A baseline's file name: `home-390-light.png`. */
export function baselineName(page: SamplePage, width: number, theme: string): string {
  return `${page.name}-${String(width)}-${theme}.png`;
}

/** Every baseline the comparison needs, sorted. */
export function baselineNames(): string[] {
  return SAMPLE.flatMap((page) => WIDTHS.flatMap(({ width }) => THEMES.map((theme) => baselineName(page, width, theme)))).sort();
}
