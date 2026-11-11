// web/src/lib/links.ts
// The site's fixed links: the header's main navigation (the domain sections
// beside it come from src/lib/paths.ts DOMAINS), the data explorer among them,
// and the footer's links to the notices, the licence, the repository, the
// documentation with its gallery, in-browser examples and finance tutorials,
// and the service's public status page (Phase 5 Step 14).

export interface Link {
  label: string;
  href: string;
}

export const REPOSITORY = "https://github.com/pyeconomics-dev/pyeconomics";
// The 1.0 documentation lives under /en/main/ until the cutover moves Read the
// Docs' default version to stable (ADR-0013 decision 18).
export const DOCUMENTATION = "https://docs.pyeconomics.dev/en/main/";
export const EXAMPLE_GALLERY = `${DOCUMENTATION}gallery/index.html`;
export const IN_BROWSER_EXAMPLES = `${DOCUMENTATION}wasm/index.html`;
export const FINANCE_TUTORIALS = `${DOCUMENTATION}tutorials/finance/index.html`;
export const LICENCE = `${REPOSITORY}/blob/main/LICENSE`;
// Better Stack's status page for production's monitors (ADR-0013 decision 15).
export const STATUS_PAGE = "https://status.pyeconomics.dev/";

/** The header's main navigation. */
export const NAVIGATION: readonly Link[] = [
  { label: "Models", href: "/models/" },
  { label: "Data", href: "/data/" },
  { label: "Coverage", href: "/coverage/" },
  { label: "Search", href: "/search/" },
  { label: "Documentation", href: DOCUMENTATION },
  { label: "GitHub", href: REPOSITORY },
];

/** The footer's links, beside the notices every page carries. */
export const FOOTER_LINKS: readonly Link[] = [
  { label: "Disclaimers", href: "/legal/disclaimers/" },
  { label: "Data sources", href: "/sources/" },
  { label: "Licence (Apache-2.0)", href: LICENCE },
  { label: "GitHub", href: REPOSITORY },
  { label: "Documentation", href: DOCUMENTATION },
  { label: "Example gallery", href: EXAMPLE_GALLERY },
  { label: "In-browser examples", href: IN_BROWSER_EXAMPLES },
  { label: "Python for finance", href: FINANCE_TUTORIALS },
  { label: "Service status", href: STATUS_PAGE },
];

/**
 * ROADMAP §5 "CFA Institute marks and content": the notice the web app
 * carries, verbatim.
 */
export const CFA_NOTICE =
  "CFA® and Chartered Financial Analyst® are trademarks owned by CFA Institute. " +
  "pyeconomics is not affiliated with, endorsed by, or a Prep Provider of CFA Institute.";

/** ROADMAP §5 "Required notices": the notice everything carries. */
export const AS_IS_NOTICE = "As is; not investment advice.";
