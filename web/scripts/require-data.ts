// web/scripts/require-data.ts
// `npm run build` runs this first: the site builds only from the data
// scripts/web/export_site_data.py exports, the validators
// scripts/web/compile_validators.mjs precompiles from it and the client
// generated from it, so a build without them stops here with the command that
// makes them, rather than deep inside Vite with an unresolved import. A
// validator is stale when the SHA-256 it records is not its model's input
// schema's in registry.json (the schema changed and only the export ran), and
// one for a model the registry no longer holds is left over: either fails the
// build too (ADR-0013 decision 8).
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

const WEB = fileURLToPath(new URL("..", import.meta.url));

/** The files `npm run data` writes, relative to web/. */
export const REQUIRED = [
  "src/data/generated/registry.json",
  "src/data/generated/openapi.json",
  "src/data/generated/problems.json",
  "src/data/generated/sources.json",
  "src/data/generated/concepts.json",
  "src/data/generated/surfaces.json",
  "src/client/index.ts",
] as const;

/** Where the precompiled validators are, relative to web/. */
export const VALIDATORS = "src/data/generated/validators";

/** Return the required files missing under `root`. */
export function missing(root: string = WEB): string[] {
  // Fixed paths under the project root, never user input.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  return REQUIRED.filter((file) => !existsSync(`${root}/${file}`));
}

const RECORDED = /^export const schemaSha256 = "([0-9a-f]{64})";$/m;

/**
 * Return what is wrong with the precompiled validators under `root`: a model
 * with no validator, a validator compiled from another schema, or one for no
 * model. The registry must exist (missing() says when it does not).
 */
export function staleValidators(root: string = WEB): string[] {
  // Fixed paths under the project root, written by `npm run data`.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  const registry = JSON.parse(readFileSync(`${root}/${REQUIRED[0]}`, "utf8")) as {
    models: { id: string; input_schema: unknown }[];
  };
  const directory = `${root}/${VALIDATORS}`;
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- the same fixed directory
  const files = new Set(existsSync(directory) ? readdirSync(directory) : []);
  const problems: string[] = [];
  for (const model of registry.models) {
    const file = `${model.id}.js`;
    if (!files.delete(file)) {
      problems.push(`${model.id} has no validator`);
      continue;
    }
    // eslint-disable-next-line security/detect-non-literal-fs-filename -- a file readdirSync found there
    const recorded = RECORDED.exec(readFileSync(`${directory}/${file}`, "utf8"))?.[1];
    const expected = createHash("sha256").update(JSON.stringify(model.input_schema), "utf8").digest("hex");
    if (recorded !== expected) problems.push(`${model.id}'s validator was compiled from another schema`);
  }
  for (const file of files) problems.push(`${file} is a validator for no registered model`);
  return problems;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const absent = missing();
  if (absent.length > 0) {
    process.stderr.write(
      `The site data is missing (${absent.join(", ")}).\n` +
        "Run `npm run data` in web/ first: it exports the registry, the OpenAPI document, the\n" +
        "error table, the sources, the concepts and each model's surfaces, precompiles each\n" +
        "model's validator, and generates the TypeScript client.\n",
    );
    process.exit(1);
  }
  const stale = staleValidators();
  if (stale.length > 0) {
    process.stderr.write(
      `The calculators' validators are stale:\n${stale.map((problem) => `  ${problem}`).join("\n")}\n` +
        "Run `npm run data` in web/ again: it recompiles them from the exported registry.\n",
    );
    process.exit(1);
  }
}
