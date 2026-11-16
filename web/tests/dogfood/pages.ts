// web/tests/dogfood/pages.ts
// What the dogfooding harness captures (docs/design/dogfooding.md section 5):
// one page of every type, at a phone's, a tablet's and a desktop's width, in
// light and dark. Steps 17, 18 and 20 run this list unchanged; a new page type
// joins it in the same pull request as the protocol's change log.

/** One page type and the page that stands for it. */
export interface PageType {
  /** A short name, used in file names. */
  id: string;
  path: string;
  /** What the page stands for, in the index. */
  label: string;
  /** The status the page answers with: 200, or 404 for the not-found page. */
  status: number;
}

export const PAGE_TYPES: readonly PageType[] = [
  { id: "home", path: "/", label: "Home", status: 200 },
  { id: "models", path: "/models/", label: "Every model, with filters", status: 200 },
  { id: "domain", path: "/models/fixed-income/", label: "A domain", status: 200 },
  { id: "model-instant", path: "/models/performance/risk-adjusted/", label: "A model page: instant", status: 200 },
  { id: "model-bound", path: "/models/macro/policy-rule/", label: "A model page: bound to data", status: 200 },
  { id: "model-chart", path: "/models/econometrics/ols/", label: "A model page: with a chart", status: 200 },
  { id: "model-family", path: "/models/fixed-income/duration/", label: "A model page: a family", status: 200 },
  {
    id: "model-library-only",
    path: "/models/equity/cape/",
    label: "A model page: data the hosted site may not serve",
    status: 200,
  },
  { id: "data", path: "/data/", label: "The data catalog", status: 200 },
  { id: "concept", path: "/data/us/unemployment/rate/", label: "A data concept", status: 200 },
  { id: "coverage", path: "/coverage/", label: "The coverage matrix", status: 200 },
  { id: "search", path: "/search/", label: "Search", status: 200 },
  { id: "problem", path: "/problems/invalid-input/", label: "A problem page", status: 200 },
  { id: "newsletter", path: "/newsletter/", label: "The newsletter sign-up", status: 200 },
  { id: "pro", path: "/pro/", label: "The Pro preview", status: 200 },
  { id: "legal", path: "/legal/privacy/", label: "A legal page", status: 200 },
  { id: "sources", path: "/sources/", label: "The data sources", status: 200 },
  { id: "not-found", path: "/no-such-page/", label: "The 404 page", status: 404 },
];

/** A browser window size; a phone's is emulated as a phone (touch, overlay scrollbars). */
export interface Viewport {
  name: string;
  width: number;
  height: number;
  phone: boolean;
}

export const VIEWPORTS: readonly Viewport[] = [
  { name: "390x844", width: 390, height: 844, phone: true },
  { name: "820x1180", width: 820, height: 1180, phone: false },
  { name: "1440x900", width: 1440, height: 900, phone: false },
];

export const THEMES = ["light", "dark"] as const;
export type Theme = (typeof THEMES)[number];

/** The most viewport-high tiles kept of one long page. */
export const MAX_TILES = 12;
