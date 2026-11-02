// web/vitest.config.ts
// Unit tests (tests/unit/): the build scripts, the policy's configuration, the
// formulas, the site data, what a model page derives from its entry, and the
// model page itself rendered through Astro's container API, in Node. Astro's
// own Vite configuration compiles .astro components for them. The built site
// is tested by vitest.dist.config.ts (tests/site/) and, served, by Playwright
// (tests/e2e/).
import { getViteConfig } from "astro/config";

export default getViteConfig({
  test: {
    include: ["tests/unit/**/*.test.ts"],
    environment: "node",
  },
});
