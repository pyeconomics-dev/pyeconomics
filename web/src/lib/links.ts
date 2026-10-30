// web/src/lib/links.ts
// The site's fixed links: the header's main navigation, which Step 7 fills
// with the model sections and the data explorer, and the footer's links to
// the notices, the licence, the repository and the documentation.

export interface Link {
  label: string;
  href: string;
}

export const REPOSITORY = "https://github.com/pyeconomics-dev/pyeconomics";
// The 1.0 documentation lives under /en/main/ until the cutover moves Read the
// Docs' default version to stable (ADR-0013 decision 18).
export const DOCUMENTATION = "https://pyeconomics.readthedocs.io/en/main/";
export const LICENCE = `${REPOSITORY}/blob/main/LICENSE`;

/** The header's main navigation. */
export const NAVIGATION: readonly Link[] = [
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
