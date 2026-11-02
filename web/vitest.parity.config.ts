// web/vitest.parity.config.ts
// The web parity suite (tests/parity/; Phase 5 Step 6, ADR-0013 decision 8):
// every golden case through the calculator's request builder, and every
// snippet kind for one model per domain, against a local `pyeconomics serve`
// that tests/parity/serve.ts starts from the locked environment. Run after
// `npm run data`: `npm run test:parity`.
import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    include: ["tests/parity/**/*.test.ts"],
    environment: "node",
    globalSetup: ["tests/parity/serve.ts"],
    maxConcurrency: 6,
    testTimeout: 600_000,
    hookTimeout: 360_000,
  },
});
