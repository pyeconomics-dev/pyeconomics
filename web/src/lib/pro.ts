// web/src/lib/pro.ts
// The Pro preview (Phase 5 Step 15; ROADMAP §5 "Monetization strategy &
// validation gates"; ADR-0013 decision 19): a priced fake door that records
// intent and sells nothing. Its planned features are ROADMAP §5's Pro web
// tier; its indicative prices are the maintainer's, set at Step 15's kickoff
// (2026-11-11) against the anchors there (Portfolio Visualizer $30 personal /
// $55 commercial a month, Koyfin $39 to $79). Nothing here exists, is sold or
// is charged: the page's only input is the optional waitlist.
import type { Tier } from "@/lib/events";

/** The statement the page leads with; a test holds the built page to it. */
export const PRO_DISCLOSURE =
  "Pro does not exist yet. Nothing is sold, charged or collected on this page except the optional waitlist below: " +
  "there is no account, no payment and no checkout. The prices are indicative, may change, and are not an offer.";

/** What stays true whatever Pro becomes. */
export const FREE_CORE =
  "Everything pyeconomics offers today stays free: the library is open source under Apache-2.0, for any use, " +
  "and this site's models, calculators and data stay free to use.";

/** The planned features (ROADMAP §5's Pro web tier). */
export const PRO_FEATURES: readonly { title: string; detail: string }[] = [
  { title: "Saved models and scenarios", detail: "Keep a model's inputs and scenarios on the site and come back to them." },
  { title: "Batch runs and exports", detail: "Run a model over many sets of inputs at once and export every result." },
  { title: "Higher API quotas", detail: "More runs and series a minute through the REST API and the MCP server." },
  {
    title: "A commercial-use licence",
    detail: "Use Pro's hosted features in your business (Commercial and Team).",
  },
];

/** One tier of the preview. */
export interface ProTier {
  tier: Tier;
  /** Indicative price in US dollars a month. */
  price: number;
  summary: string;
  includes: readonly string[];
}

/** The tiers and their indicative prices (the maintainer's, 2026-11-11). */
export const PRO_TIERS: readonly ProTier[] = [
  {
    tier: "personal",
    price: 19,
    summary: "For your own study and research.",
    includes: ["Saved models and scenarios", "Batch runs and exports", "Higher API quotas", "Personal use"],
  },
  {
    tier: "commercial",
    price: 49,
    summary: "For one person using pyeconomics at work.",
    includes: ["Everything in Personal", "A commercial-use licence"],
  },
  {
    tier: "team",
    price: 149,
    summary: "For a team of up to five people.",
    includes: ["Everything in Commercial", "Up to five people"],
  },
];
