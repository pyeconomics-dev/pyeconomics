// web/src/lib/links.ts
// The site's fixed links: the header's main navigation (the domain sections
// beside it come from src/lib/paths.ts DOMAINS), the data explorer among them,
// and the footer's links to the terms, the privacy policy, the notices, the
// licence page (Step 16), the repository, the documentation with its gallery,
// in-browser examples and finance tutorials,
// and the service's public status page (Phase 5 Step 14), and where to ask a
// question (GitHub Discussions) and sign up for the newsletter (Step 15).

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
// Questions, ideas and show and tell (Phase 5 Step 15).
export const DISCUSSIONS = `${REPOSITORY}/discussions`;
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

/** One group of the footer's links, under its heading. */
export interface LinkGroup {
  title: string;
  links: readonly Link[];
}

/**
 * The footer's links, beside the notices every page carries, in four groups a
 * visitor can scan (Phase 5 Step 18's round 2: seventeen links ran in one
 * line): the project and how to follow it, what to learn from, where the work
 * is done, and the legal and trust pages (Phase 5 Step 16; tests/site/ and the
 * end-to-end tests hold each link in every page's footer).
 */
export const FOOTER_GROUPS: readonly LinkGroup[] = [
  {
    title: "pyeconomics",
    links: [
      // What the site is, who runs it and how its models are checked (Step 18's
      // rounds 1 and 2: no page said, then the link led to the legal index).
      { label: "About", href: "/about/" },
      { label: "AI assistants", href: "/assistants/" },
      { label: "Newsletter", href: "/newsletter/" },
      { label: "Pro preview", href: "/pro/" },
      { label: "Service status", href: STATUS_PAGE },
    ],
  },
  {
    title: "Learn",
    links: [
      { label: "Documentation", href: DOCUMENTATION },
      { label: "Example gallery", href: EXAMPLE_GALLERY },
      { label: "In-browser examples", href: IN_BROWSER_EXAMPLES },
      { label: "Python for finance", href: FINANCE_TUTORIALS },
    ],
  },
  {
    title: "Project",
    links: [
      { label: "GitHub", href: REPOSITORY },
      { label: "Discussions", href: DISCUSSIONS },
      { label: "Data sources", href: "/sources/" },
      { label: "Licence (Apache-2.0)", href: "/legal/licence/" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Legal", href: "/legal/" },
      { label: "Terms of use", href: "/legal/terms/" },
      { label: "Privacy", href: "/legal/privacy/" },
      { label: "Disclaimers", href: "/legal/disclaimers/" },
    ],
  },
];

/** Every footer link, in the groups' order. */
export const FOOTER_LINKS: readonly Link[] = FOOTER_GROUPS.flatMap((group) => group.links);

/**
 * ROADMAP §5 "CFA Institute marks and content": the notice the web app
 * carries, verbatim.
 */
export const CFA_NOTICE =
  "CFA® and Chartered Financial Analyst® are trademarks owned by CFA Institute. " +
  "pyeconomics is not affiliated with, endorsed by, or a Prep Provider of CFA Institute.";

/** ROADMAP §5 "Required notices": the notice everything carries. */
export const AS_IS_NOTICE = "As is; not investment advice.";
