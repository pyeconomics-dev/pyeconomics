// web/src/lib/registry-schema.ts
// The Zod schema of a registry.json model entry: REGISTRY_SCHEMA's required
// keys (src/pyeconomics/surfaces/registry_schema.py), each typed as the model
// pages read it. src/content.config.ts validates every entry with it, so a
// registry change the pages cannot render (a key renamed or removed, a value
// of another type) fails the build, naming the model and the key. Extra keys
// pass: the pages render what they know, and tests/unit/registry-schema.test.ts
// holds these keys equal to the export's.
import { z } from "astro/zod";

const text = z.string();
const maybeText = z.string().nullable();
const texts = z.array(z.string());
const json = z.record(z.string(), z.unknown());

export const ReferenceSchema = z.object({
  key: text,
  citation: text,
  doi: maybeText,
  url: maybeText,
  locator: maybeText,
  isbn: maybeText,
});

export const BindingSchema = z.object({
  field: text,
  concept: text,
  transform: maybeText,
  as_of: z.enum(["last_on_or_before", "period", "window"]),
  window: z.number().int().min(1).nullable(),
  vintage: z.enum(["real_time", "latest"]),
  profile: text,
  tenors: maybeText,
  columns: texts,
});

export const ResultSchema = z.object({
  model_id: text,
  model_version: z.number().int(),
  inputs: json,
  outputs: json,
  warnings: z.array(z.object({ code: text, message: text })),
  manifest: json,
});

export const EVIDENCE = ["standard", "practitioner", "contested", "rejected", "historical"] as const;
export const COST = ["instant", "light", "heavy"] as const;

export const ModelSchema = z.object({
  id: z.string().regex(/^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$/),
  version: z.number().int().min(1),
  domain: z.string().regex(/^[a-z][a-z0-9_]*$/),
  title: text,
  summary: text,
  tags: texts,
  formula: texts.min(1),
  assumptions: texts,
  limitations: texts,
  evidence: z.enum(EVIDENCE).nullable(),
  cost: z.enum(COST).nullable(),
  references: z.array(ReferenceSchema),
  invariants: z.array(z.object({ id: text, statement: text })),
  no_invariants_reason: maybeText,
  examples: z.array(z.object({ name: text, note: maybeText, inputs: json })).min(1),
  charts: z.array(json),
  aliases: z.array(z.object({ id: text, removed_in: text })),
  bindings: z.array(BindingSchema),
  extra: maybeText,
  changelog: z.array(z.object({ version: z.number().int().min(1), note: text })),
  input_schema: json,
  output_schema: json,
  card: text,
  example_result: ResultSchema.nullable(),
  example_figure: json.nullable(),
});

export type Model = z.infer<typeof ModelSchema>;
export type Binding = z.infer<typeof BindingSchema>;
export type Reference = z.infer<typeof ReferenceSchema>;
export type Evidence = (typeof EVIDENCE)[number];
export type Cost = (typeof COST)[number];

/** registry.json's models, each validated; an invalid entry names its model. */
export function parseModels(document: unknown): Model[] {
  const models = z.object({ models: z.array(z.unknown()) }).parse(document).models;
  return models.map((entry, index) => {
    const result = ModelSchema.safeParse(entry);
    if (result.success) return result.data;
    const id = (entry as { id?: unknown }).id;
    const issues = result.error.issues.map((issue) => `${issue.path.join(".")}: ${issue.message}`);
    throw new Error(
      `registry.json model ${typeof id === "string" ? id : `#${index}`} cannot be rendered: ${issues.join("; ")}`,
    );
  });
}
