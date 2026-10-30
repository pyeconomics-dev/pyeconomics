// web/astro.config.ts
// The pyeconomics site (ADR-0006; ADR-0013 decisions 2 and 9): static output
// with no adapter, so every route is prerendered to a file and a server route
// fails the build; React 19 islands; Tailwind 4 through its Vite plugin; and
// Astro's Content Security Policy, which hashes what Astro inlines into each
// page's <meta> policy. Nothing else is inlined: stylesheets and scripts are
// always files (inlineStylesheets 'never', assetsInlineLimit 0), so the policy
// holds only the island runtime's hashes. The ClientRouter and Shiki are never
// used, because Astro's policy supports neither. scripts/headers.ts runs after
// the build and writes the same policy, with every page's hashes, into
// dist/_headers. shippedPackages() records the npm packages the client bundle
// holds, for the licence check of what ships.
import react from "@astrojs/react";
import tailwindcss from "@tailwindcss/vite";
import type { AstroUserConfig } from "astro";
import { defineConfig } from "astro/config";

import { DIRECTIVES, metaDirectives } from "./csp.config.ts";
import shippedPackages from "./scripts/shipped-packages.ts";

// Astro types each directive as its name followed by any text; every name in
// csp.config.ts is one of Astro's, and scripts/headers.ts checks the result.
type Csp = Exclude<NonNullable<NonNullable<AstroUserConfig["security"]>["csp"]>, boolean>;
type Directive = NonNullable<Csp["directives"]>[number];

export default defineConfig({
  site: "https://pyeconomics.dev",
  output: "static",
  trailingSlash: "always",
  build: {
    format: "directory",
    inlineStylesheets: "never",
  },
  devToolbar: { enabled: false },
  markdown: { syntaxHighlight: false },
  integrations: [react()],
  vite: {
    plugins: [tailwindcss(), shippedPackages()],
    build: { assetsInlineLimit: 0 },
  },
  security: {
    csp: {
      algorithm: "SHA-256",
      directives: metaDirectives() as Directive[],
      scriptDirective: { resources: [...(DIRECTIVES["script-src"] ?? [])] },
      styleDirective: { resources: [...(DIRECTIVES["style-src"] ?? [])] },
    },
  },
});
