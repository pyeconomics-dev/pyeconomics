// web/vitest.dist.config.ts
// Tests over the built site (tests/site/): they read dist/ as `npm run build`
// wrote it, so run them after the build (`npm run test:dist`).
import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    include: ["tests/site/**/*.test.ts"],
    environment: "node",
  },
});
