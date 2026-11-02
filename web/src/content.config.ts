// web/src/content.config.ts
// The site's content collections. `models` holds every model of the
// registry.json scripts/web/export_site_data.py writes, one entry per model id,
// each validated by ModelSchema (src/lib/registry-schema.ts) at build time:
// the model pages (src/pages/models/) are generated from it, so a new model
// gains its page with no web code, and an entry the pages cannot render fails
// the build.
import { defineCollection } from "astro:content";
import { file } from "astro/loaders";

import { ModelSchema, parseModels } from "@/lib/registry-schema";

const models = defineCollection({
  loader: file("src/data/generated/registry.json", {
    parser: (text) => parseModels(JSON.parse(text)),
  }),
  schema: ModelSchema,
});

export const collections = { models };
