// web/src/lib/fonts.ts
// The site's fonts (Phase 5 Step 17; ADR-0013's amendment of 2026-11-16):
// Literata for text and STIX Two Math for formulas, each under the SIL Open
// Font License 1.1 with no Reserved Font Name, served from our own origin with
// hashed names from the packages scripts/checks/web_licences.py admits under
// its font rule.
// global.css declares their @font-face rules; every page preloads only what
// its first paint needs, the text face's latin file. The math font is not
// preloaded: a browser fetches it only for a page with a formula.
import text from "../../node_modules/@fontsource-variable/literata/files/literata-latin-wght-normal.woff2?url";

/** The font files every page preloads. */
export const PRELOAD_FONTS: readonly string[] = [text];

/** The fonts the site serves, for /legal/licence/: each package and what of it ships. */
export const FONTS = [
  {
    name: "Literata",
    use: "the text face",
    package: "@fontsource-variable/literata",
    files: "the latin upright and italic variable files",
  },
  {
    name: "STIX Two Math",
    use: "the math face, set on every formula",
    package: "@fontsource/stix-two-math",
    files: "the latin file",
  },
] as const;
