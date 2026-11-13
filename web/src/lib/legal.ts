// web/src/lib/legal.ts
// What the legal and trust pages share (Phase 5 Step 16; ROADMAP §4 5.7;
// ADR-0013 decision 20): who operates the site and how to reach them, the
// governing law, the dates each page was last changed, the data flows the
// privacy policy is generated from (src/content/legal/data-flows.json,
// validated here at build time), the hypothetical-results legends and which
// models carry them, and ROADMAP §5's required notices.
//
// The operator is the maintainer, as an individual, until the project's own
// company exists; the maintainer chose this, the contact address and Florida
// law at the step's kickoff (2026-11-12), and counsel reviews every page
// before launch (docs/operations/counsel-review.md). A text that is still a
// question for counsel says so on its page, through `counsel` fields.

import { z } from "astro/zod";

import dataFlows from "@/content/legal/data-flows.json";
import type { Model } from "@/lib/registry-schema";

/** Who operates pyeconomics.dev and answers for these pages. */
export const OPERATOR = "Nathan Ramos";

/** The one address for legal, privacy and data-rights requests: the project's published address. */
export const CONTACT_EMAIL = "nathan.ramos.github@gmail.com";

/** The governing law of the terms of use: counsel confirms it before launch. */
export const GOVERNING_LAW = "the State of Florida, United States";

/** The repository, where the site's source and its history are public. */
export const REPOSITORY = "https://github.com/pyeconomics-dev/pyeconomics";

/** Each legal page, its path, title, description and the date it last changed. */
export interface LegalPage {
  path: string;
  title: string;
  description: string;
  updated: string;
}

export const TERMS: LegalPage = {
  path: "/legal/terms/",
  title: "Terms of use",
  description:
    "The terms of pyeconomics.dev, its API and MCP endpoint: the software's licence, acceptable use and rate limits, the data's own terms, no warranty and the limit of liability.",
  updated: "2026-11-12",
};

export const PRIVACY: LegalPage = {
  path: "/legal/privacy/",
  title: "Privacy policy",
  description:
    "What pyeconomics.dev collects, why, who processes it, where and for how long: no cookies, no accounts, and your inputs never stored.",
  updated: dataFlows.updated,
};

export const DISCLAIMERS: LegalPage = {
  path: "/legal/disclaimers/",
  title: "Disclaimers",
  description:
    "pyeconomics is for education and information: not investment advice, not registered with any regulator, provided as is, with data that may be delayed or wrong.",
  updated: "2026-11-12",
};

export const LICENCE_PAGE: LegalPage = {
  path: "/legal/licence/",
  title: "Licence",
  description:
    "pyeconomics is licensed under the Apache License 2.0. This page holds its licence, its NOTICE and the licences of the third-party code this site sends to browsers.",
  updated: "2026-11-12",
};

export const SOURCES_PAGE: LegalPage = {
  path: "/sources/",
  title: "Data sources and licences",
  description:
    "Every data source pyeconomics reads: its licence class, terms, attribution and required notices, and whether this site may serve its data.",
  updated: "2026-11-12",
};

export const LEGAL_INDEX: LegalPage = {
  path: "/legal/",
  title: "Legal",
  description: "The terms of use, privacy policy, disclaimers and licence of pyeconomics.dev, and its data sources.",
  updated: "2026-11-12",
};

/**
 * The hosted API's rate limits per client, over a moving minute
 * (server/limits.py RateLimits; tests/web/test_legal_pages.py holds them equal).
 */
export const RATE_LIMITS = { runs: "60/minute", series: "30/minute", metadata: "120/minute" } as const;

/** The FRED® API's terms, which bind anyone who reads FRED through pyeconomics on their own computer. */
export const FRED_API_TERMS = "https://fred.stlouisfed.org/docs/api/terms_of_use.html";

/** The New York Fed's Terms of Use, which its content carries with it. */
export const NYFED_TERMS = "https://www.newyorkfed.org/privacy/termsofuse.html";

/** The OECD's terms and conditions. */
export const OECD_TERMS = "https://www.oecd.org/en/about/terms-conditions.html";

/** The legal and trust pages, in the order the legal index and the footer list them. */
export const LEGAL_PAGES: readonly LegalPage[] = [TERMS, PRIVACY, DISCLAIMERS, LICENCE_PAGE, SOURCES_PAGE];

// --- The data flows (ADR-0013 "Personal data") ---

const https = z.string().regex(/^https:\/\/[^\s"<>]+$/, "an https URL");

/** A processor: a vendor that handles data for the site. */
export const ProcessorSchema = z.object({
  id: z.string().regex(/^[a-z][a-z0-9-]*$/),
  /** The legal entity. */
  name: z.string().min(1),
  /** The services the site uses. */
  service: z.string().min(1),
  /** The data processing agreement, and how it applies. */
  dpa: z.object({ url: https, basis: z.string().min(1) }),
  privacy: https,
});

/** One data flow: what is collected, why, by whom, where and for how long. */
export const FlowSchema = z.object({
  id: z.string().regex(/^[a-z][a-z0-9-]*$/),
  title: z.string().min(1),
  collected: z.string().min(1),
  purpose: z.string().min(1),
  /** The lawful basis, for readers in the EU and UK. */
  basis: z.string().min(1),
  /** A processor's id, or null where the data never leaves the reader's own device. */
  processor: z.string().nullable(),
  location: z.string().min(1),
  retention: z.string().min(1),
  /** The ADR-0013 decision behind it, or null. */
  decision: z.number().int().min(1).max(20).nullable(),
  /** Origins the browser contacts for it: the policy's connect-src and form-action. */
  origins: z.array(z.string()),
  /** Hosts the service contacts for it (a pattern's variable part as <name>). */
  hosts: z.array(z.string()),
  /** A question counsel has still to answer about it, shown on the page, or null. */
  counsel: z.string().nullable(),
});

export const DataFlowsSchema = z
  .object({
    format: z.literal(1),
    updated: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    processors: z.array(ProcessorSchema).min(1),
    flows: z.array(FlowSchema).min(1),
  })
  .superRefine((document, context) => {
    const processors = new Set(document.processors.map((processor) => processor.id));
    const used = new Set<string>();
    const ids = new Set<string>();
    for (const flow of document.flows) {
      if (ids.has(flow.id)) context.addIssue({ code: "custom", message: `flow ${flow.id} is listed twice` });
      ids.add(flow.id);
      if (flow.processor !== null) {
        if (!processors.has(flow.processor)) {
          context.addIssue({ code: "custom", message: `flow ${flow.id} names no listed processor ${flow.processor}` });
        }
        used.add(flow.processor);
      }
    }
    for (const id of processors) {
      if (!used.has(id)) context.addIssue({ code: "custom", message: `processor ${id} handles no flow` });
    }
  });

export type Processor = z.infer<typeof ProcessorSchema>;
export type Flow = z.infer<typeof FlowSchema>;
export type DataFlows = z.infer<typeof DataFlowsSchema>;

/** Validate the data flows, naming every problem. */
export function parseDataFlows(document: unknown): DataFlows {
  const parsed = DataFlowsSchema.safeParse(document);
  if (!parsed.success) {
    const problems = parsed.error.issues.map((issue) => `${issue.path.join(".") || "(root)"}: ${issue.message}`);
    throw new Error(`src/content/legal/data-flows.json:\n  ${problems.join("\n  ")}`);
  }
  return parsed.data;
}

/** The site's data flows, validated once at build time. */
export const DATA_FLOWS: DataFlows = parseDataFlows(dataFlows);

/** A flow's processor. */
export function processorOf(flow: Flow, flows: DataFlows = DATA_FLOWS): Processor | null {
  return flows.processors.find((processor) => processor.id === flow.processor) ?? null;
}

// --- Data sources (ADR-0005; ROADMAP §5 "Data licensing policy") ---

/** When the hosted snapshot runs (ADR-0013 decision 6): daily, after the US end-of-day series publish. */
export const SNAPSHOT_CADENCE = "daily at 23:30 UTC";

/** One licence class: what it means, and where its data may flow (ADR-0005's table). */
export interface LicenceClass {
  id: string;
  meaning: string;
  local: string;
  hosted: string;
}

/** ADR-0005's five classes, in its order. */
export const LICENCE_CLASSES: readonly LicenceClass[] = [
  {
    id: "hosted-safe",
    meaning: "Terms allow display by a third-party service, with attribution",
    local: "Yes",
    hosted: "Yes: snapshot, display and export, with attribution",
  },
  {
    id: "library-only",
    meaning: "Personal-use, non-commercial, no-caching or scraped terms",
    local: "Yes, under your own acceptance of the terms",
    hosted: "Never, unless the owner grants written permission",
  },
  {
    id: "byok",
    meaning: "Your own paid subscription",
    local: "Yes, on your own key",
    hosted: "Never",
  },
  {
    id: "premium-local",
    meaning: "Licensed to a machine or seat",
    local: "Yes, on the licensed machine only",
    hosted: "Never",
  },
  {
    id: "user-supplied",
    meaning: "Your own files",
    local: "Yes",
    hosted: "Processed in memory for one run, never stored",
  },
];

/** One row of ROADMAP §5's "Required notices" table. */
export interface RequiredNotice {
  source: string;
  notice: string;
}

/**
 * ROADMAP §5 "Required notices", row for row: the notice each source's data
 * carries wherever it appears. tests/unit/legal.test.ts holds it to the
 * ROADMAP's table, so a change there fails until this follows.
 */
export const REQUIRED_NOTICES: readonly RequiredNotice[] = [
  {
    source: "FRED",
    notice:
      '"This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis." (local surfaces)',
  },
  {
    source: "BEA",
    notice:
      '"This product uses the Bureau of Economic Analysis (BEA) Data API but is not endorsed or certified by BEA."',
  },
  {
    source: "Census",
    notice: '"This product uses the Census Bureau Data API but is not endorsed or certified by the Census Bureau."',
  },
  {
    source: "BLS",
    notice: "BLS's statement that it cannot vouch for data or analyses after retrieval, plus the access date",
  },
  {
    source: "NY Fed",
    notice:
      '"© [year] Federal Reserve Bank of New York" with its terms reference; reference rates carry their own terms line',
  },
  {
    source: "ECB",
    notice:
      "In a paid tier: the information may be obtained free of charge from the ECB — before payment and on each access",
  },
  {
    source: "World Bank, OECD, Eurostat, IMF",
    notice: "Each source's prescribed source line, with the dataset name and access date",
  },
  { source: "Everything", notice: '"As is; not investment advice"' },
];

// --- Hypothetical results (ROADMAP §5 "Disclaimers"; ADR-0013 decision 20) ---

/**
 * The registry tags that mark a model whose outputs are simulated or
 * hypothetical: the Monte Carlo, historical-simulation and backtest families.
 * The legend follows the tags, never a list of ids, so a new model that
 * simulates carries it by declaring the tag.
 */
export const SIMULATED_TAGS: readonly string[] = ["monte carlo", "simulation", "historical simulation", "backtesting"];

/**
 * FINRA Rule 2214(c)(4)'s legend, as a template (pyeconomics is not a FINRA
 * member; read 2026-11-12): its words, with the model in place of
 * "[name of investment analysis tool]".
 */
export const FINRA_2214_LEGEND =
  "IMPORTANT: The projections or other information generated by [name of investment analysis tool] regarding the likelihood of various investment outcomes are hypothetical in nature, do not reflect actual investment results and are not guarantees of future results.";

/** The legend beside a simulated model's results. */
export const HYPOTHETICAL_LEGEND = FINRA_2214_LEGEND.replace("[name of investment analysis tool]", "this model");

/**
 * What else FINRA Rule 2214(c) asks a tool to say, in our words: results vary
 * with each use and over time ((c)(2)), and the method, its assumptions and
 * limitations are described ((c)(1)).
 */
export const HYPOTHETICAL_NOTES: readonly string[] = [
  "Results may vary with each use and over time: they depend on the inputs, the random seed and the data you give the model.",
  "The model's method, assumptions and limitations are set out on this page; read them before relying on a result.",
];

/**
 * 17 CFR 4.41(b)(1)(i)'s statement, verbatim as the eCFR gives it (read
 * 2026-11-12), "under-or over-compensated" included; (b)(2) asks for it
 * prominently and in immediate proximity to the results.
 */
export const CFTC_STATEMENT =
  "These results are based on simulated or hypothetical performance results that have certain inherent limitations. Unlike the results shown in an actual performance record, these results do not represent actual trading. Also, because these trades have not actually been executed, these results may have under-or over-compensated for the impact, if any, of certain market factors, such as lack of liquidity. Simulated or hypothetical trading programs in general are also subject to the fact that they are designed with the benefit of hindsight. No representation is being made that any account will or is likely to achieve profits or losses similar to these being shown.";

/** The tags that mark futures: a simulated model with one also carries the CFTC statement. */
export const FUTURES_TAGS: readonly string[] = ["futures", "black-76"];

/** Whether a model's outputs are simulated or hypothetical. */
export function simulates(model: Pick<Model, "tags">): boolean {
  return model.tags.some((tag) => SIMULATED_TAGS.includes(tag));
}

/** Whether a simulated model involves futures, so its legend adds the CFTC statement. */
export function simulatesFutures(model: Pick<Model, "tags">): boolean {
  return simulates(model) && model.tags.some((tag) => FUTURES_TAGS.includes(tag));
}
