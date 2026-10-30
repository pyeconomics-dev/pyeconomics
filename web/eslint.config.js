// web/eslint.config.js
// ESLint for the site (Phase 5 Step 3): typescript-eslint's strict rules,
// eslint-plugin-security, eslint-plugin-astro and the jsx-a11y rules in their
// strict form, for .astro pages (through eslint-plugin-astro) and React
// components. `npm run lint` allows no warning; a suppression carries an
// inline justification. eslint-plugin-jsx-a11y-x is the maintained fork of
// eslint-plugin-jsx-a11y that supports ESLint 10, and eslint-plugin-astro
// loads it for its own jsx-a11y rules.
import js from "@eslint/js";
import astro from "eslint-plugin-astro";
import jsxA11y from "eslint-plugin-jsx-a11y-x";
import security from "eslint-plugin-security";
import { defineConfig, globalIgnores } from "eslint/config";
import globals from "globals";
import tseslint from "typescript-eslint";

export default defineConfig(
  globalIgnores([
    "dist/",
    ".astro/",
    ".wrangler/",
    ".lighthouse/",
    "node_modules/",
    "playwright-report/",
    "test-results/",
    "src/client/",
    "src/data/generated/",
  ]),
  js.configs.recommended,
  tseslint.configs.strict,
  tseslint.configs.stylistic,
  security.configs.recommended,
  astro.configs.recommended,
  astro.configs["jsx-a11y-strict"],
  {
    files: ["**/*.tsx"],
    ...jsxA11y.configs.strict,
  },
  {
    languageOptions: {
      globals: { ...globals.node },
    },
    linterOptions: {
      reportUnusedDisableDirectives: "error",
    },
  },
  {
    // Tests read the build output, the generated data and temporary
    // directories they create themselves: paths from the test, never from a
    // user. The rule stays on for everything that ships or builds the site.
    files: ["tests/**"],
    rules: { "security/detect-non-literal-fs-filename": "off" },
  },
);
