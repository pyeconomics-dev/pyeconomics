// web/vitest.config.ts
// Unit tests (tests/unit/): the headers step, the policy's configuration, the
// formulas, the site data and the build info, in Node. The pages themselves
// are tested built and served, by Playwright (tests/e2e/).
import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    include: ["tests/unit/**/*.test.ts"],
    environment: "node",
  },
});
