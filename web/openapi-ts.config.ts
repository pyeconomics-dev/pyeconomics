// web/openapi-ts.config.ts
// The site's TypeScript client of the REST API (ADR-0012 decision 18), from
// the openapi.json scripts/web/export_site_data.py writes. `npm run data`
// generates it into src/client/, which is git-ignored: like the site data, it
// is rebuilt from the registry on every build. The calculators (Step 6) call
// the API on the site's own origin through it.
import { fileURLToPath } from "node:url";

import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  // An absolute path: a relative one reads as a Hey API registry name.
  input: fileURLToPath(new URL("src/data/generated/openapi.json", import.meta.url)),
  output: "src/client",
  plugins: ["@hey-api/client-fetch", "@hey-api/typescript", "@hey-api/sdk"],
});
