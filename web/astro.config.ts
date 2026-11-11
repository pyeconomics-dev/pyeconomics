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
// holds, the file reader's worker bundle included, for the licence check of
// what ships. @astrojs/sitemap lists every page
// on the production origin (sitemap-index.xml), except the 404 page, which is
// not a page anyone should land on from a search. `client:interaction`
// (src/directives/interaction.ts) hydrates an island when a visitor first
// reaches for it: the header's search box, so no page loads a script for it.
// A production build given the browser DSN (csp.config.ts sentryBuild) hands
// it and the release to the islands' error reporting (src/lib/error-reporting.ts)
// through Vite's define; every other build defines both as empty, so its
// islands report nothing (Phase 5 Step 14).
import { fileURLToPath } from "node:url";

import react from "@astrojs/react";
import sitemap from "@astrojs/sitemap";
import tailwindcss from "@tailwindcss/vite";
import type { AstroIntegration, AstroUserConfig } from "astro";
import { defineConfig } from "astro/config";

import { DIRECTIVES, SENTRY, metaDirectives } from "./csp.config.ts";
import { buildVersion } from "./scripts/headers.ts";
import shippedPackages from "./scripts/shipped-packages.ts";
import { gitSha } from "./src/lib/build-info.ts";

// Astro types each directive as its name followed by any text; every name in
// csp.config.ts is one of Astro's, and scripts/headers.ts checks the result.
type Csp = Exclude<NonNullable<NonNullable<AstroUserConfig["security"]>["csp"]>, boolean>;
type Directive = NonNullable<Csp["directives"]>[number];

/** Registers `client:interaction`. */
function interactionDirective(): AstroIntegration {
  return {
    name: "pyeconomics:interaction-directive",
    hooks: {
      "astro:config:setup": ({ addClientDirective }) => {
        addClientDirective({
          name: "interaction",
          entrypoint: fileURLToPath(new URL("./src/directives/interaction.ts", import.meta.url)),
        });
      },
    },
  };
}

/** The release a production build's error events name: version and commit. */
const SENTRY_RELEASE = SENTRY ? `pyeconomics@${buildVersion()}+${gitSha()}` : "";

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
  integrations: [react(), interactionDirective(), sitemap({ filter: (page) => !page.endsWith("/404/") })],
  vite: {
    plugins: [tailwindcss(), shippedPackages()],
    // The file reader for "use my own data" is a module worker (src/workers/),
    // bundled on its own; its packages ship too, so they are recorded.
    worker: { format: "es", plugins: () => [shippedPackages()] },
    build: { assetsInlineLimit: 0 },
    define: {
      "import.meta.env.PUBLIC_SENTRY_DSN": JSON.stringify(SENTRY?.dsn ?? ""),
      "import.meta.env.PUBLIC_SENTRY_RELEASE": JSON.stringify(SENTRY_RELEASE),
    },
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
