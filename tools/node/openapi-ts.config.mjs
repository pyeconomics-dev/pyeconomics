// tools/node/openapi-ts.config.mjs
// The TypeScript client of the REST API (ADR-0012 decision 18), generated from
// the openapi.json that `pyeconomics registry export` writes. ci.yml's clients
// job writes it to generated/openapi.json (or OPENAPI_JSON names it); the
// client goes to generated/client. generated/ is git-ignored: the client is a
// CI artifact, never committed or published in Phase 4.
import { resolve } from "node:path";

import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  // An absolute path: a relative one reads as a Hey API registry name.
  input: resolve(process.env.OPENAPI_JSON ?? "generated/openapi.json"),
  output: "generated/client",
  plugins: ["@hey-api/client-fetch", "@hey-api/typescript", "@hey-api/sdk"],
});
