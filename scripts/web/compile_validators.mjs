// scripts/web/compile_validators.mjs
// Precompile each model's input-schema validator for the calculators
// (Phase 5 Step 6; ADR-0013 decisions 8 and 9). `npm run data` in web/ runs it
// after scripts/web/export_site_data.py: for every model in registry.json it
// compiles the input schema with RJSF's compileSchemaValidators (its code
// form, compileSchemaValidatorsCode) on Ajv's draft 2020-12 class, and writes
// web/src/data/generated/validators/<model id>.js, which the calculator loads
// and hands to createPrecompiledValidator with the same schema. Nothing is
// compiled in a browser, so the policy needs no 'unsafe-eval'.
//
// Ajv writes CommonJS when a schema's $id is not an identifier (ours are
// URNs), so each module is wrapped here as an ES module: its two runtime
// helpers (Ajv's ucs2length and ajv-formats' date check, the only modules the
// generated code may require) become imports, and its exports one object.
// Beside the validators, each module exports the schema they were compiled
// from (the island renders and validates against exactly that object), the
// schema's SHA-256, and the model's examples, the form's prefilled values: the
// calculator loads them with the validator rather than from page props.
// web/scripts/require-data.ts fails the build on a validator that is missing,
// stale or left over from a removed model. Stale .js files are removed here.
//
// Usage, from anywhere (web/'s packages must be installed):
//
//     node scripts/web/compile_validators.mjs
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = fileURLToPath(new URL("../../web/", import.meta.url));
const GENERATED = join(WEB, "src", "data", "generated");
export const OUT = join(GENERATED, "validators");

// The packages come from web/'s own node_modules, as the build resolves them.
const require = createRequire(join(WEB, "package.json"));

/** The modules generated code may require: Ajv's runtime and ajv-formats' checks. */
export const RUNTIME = ["ajv/dist/runtime/ucs2length", "ajv-formats/dist/formats"];

/** The SHA-256 of a schema's JSON text: what a validator records and the build checks. */
export function schemaSha256(schema) {
  return createHash("sha256").update(JSON.stringify(schema), "utf8").digest("hex");
}

/**
 * The schema the form renders and the validators are compiled from: the
 * model's input schema without its `$schema` keyword. RJSF rewrites every
 * $ref of a schema that declares draft 2020-12 to an absolute URI before it
 * validates, so its root schema would no longer equal the precompiled
 * validator's and every check would throw; Ajv's 2020-12 class reads the
 * schema as draft 2020-12 without the keyword, so validation is unchanged.
 */
export function formSchema(schema) {
  const { $schema: _declared, ...rest } = schema;
  return rest;
}

const isObject = (value) => typeof value === "object" && value !== null && !Array.isArray(value);

/** A schema with its $refs resolved as RJSF's resolveAllReferences does: the top level, properties and items. */
function resolveRefs(schema, root, seen = []) {
  if (!isObject(schema)) return schema;
  let resolved = schema;
  if (typeof resolved.$ref === "string" && !seen.includes(resolved.$ref)) {
    const { $ref, ...local } = resolved;
    const target = $ref.split("/").slice(1).reduce((node, part) => node?.[part], root);
    resolved = { ...target, ...local };
    seen = [...seen, $ref];
  }
  if (isObject(resolved.properties)) {
    const properties = {};
    for (const [name, value] of Object.entries(resolved.properties)) properties[name] = resolveRefs(value, root, seen);
    resolved = { ...resolved, properties };
  }
  if (isObject(resolved.items)) resolved = { ...resolved, items: resolveRefs(resolved.items, root, seen) };
  return resolved;
}

/**
 * The sub-schemas RJSF validates while it chooses between a oneOf's or an
 * anyOf's options, which its schemaParser does not reach inside a oneOf
 * root's members (a nullable field's two options, say). They are what
 * getFirstMatchingOption hands the validator for each option, its $refs
 * resolved: the discriminator's property schema; an object option with its
 * "any of these keys" augmentation and no `required`; or the option itself.
 * Each is keyed by RJSF's hash of it, and keeps the root's $defs to resolve
 * the $refs it still holds.
 */
export function optionSchemas(root, hashForSchema, getDiscriminator) {
  const found = new Map();
  const visit = (node) => {
    if (Array.isArray(node)) return node.forEach(visit);
    if (!isObject(node)) return undefined;
    for (const key of ["oneOf", "anyOf"]) {
      if (!Array.isArray(node[key])) continue;
      const discriminator = getDiscriminator(node);
      for (const option of node[key]) {
        const resolved = resolveRefs(option, root);
        let asked = resolved;
        if (discriminator && isObject(resolved.properties) && resolved.properties[discriminator] !== undefined) {
          asked = resolved.properties[discriminator];
        } else if (isObject(resolved.properties)) {
          const requiresAnyOf = { anyOf: Object.keys(resolved.properties).map((name) => ({ required: [name] })) };
          asked = resolved.anyOf
            ? { ...resolved, allOf: [...(resolved.allOf ?? []), requiresAnyOf] }
            : { ...resolved, ...requiresAnyOf };
          delete asked.required;
        }
        found.set(hashForSchema(asked), asked);
      }
    }
    for (const value of Object.values(node)) visit(value);
    return undefined;
  };
  visit(root);
  return found;
}

/**
 * A family's members, by calculation: each calculation's own input schema,
 * with the root's $defs and an $id of its own. The calculation's constant
 * picks exactly one member, so data is valid for the root exactly when it is
 * valid for its calculation's member, and the form validates against that
 * member alone: Ajv reports every member's errors for a oneOf, which would
 * fill the form with the other calculations' requirements.
 */
export function memberSchemas(root) {
  const mapping = root.discriminator?.mapping;
  if (!Array.isArray(root.oneOf) || !isObject(mapping)) return {};
  return Object.fromEntries(
    Object.entries(mapping).map(([calculation, ref]) => [
      calculation,
      { ...resolveRefs({ $ref: ref }, root), $defs: root.$defs, $id: `${root.$id}:${calculation}` },
    ]),
  );
}

/**
 * Turn Ajv's CommonJS standalone code into an ES module that exports its
 * validators as one object, keyed as RJSF's precompiled validator looks them
 * up, with the model's input schema, its SHA-256 and the model's examples.
 */
export function toModule(code, model) {
  const modelId = model.id;
  const imports = [];
  const body = code.replace(/require\("([^"]+)"\)/g, (_, specifier) => {
    if (!RUNTIME.includes(specifier)) {
      throw new Error(`${modelId}: the generated validator requires ${specifier}, which is not one of ${RUNTIME.join(", ")}`);
    }
    let index = imports.indexOf(specifier);
    if (index < 0) index = imports.push(specifier) - 1;
    return `__cjs(__runtime${index})`;
  });
  if (/\bmodule\b|\brequire\b/.test(body.replace(/"(?:[^"\\]|\\.)*"/g, '""'))) {
    throw new Error(`${modelId}: the generated validator uses CommonJS beyond its exports`);
  }
  return [
    `// Generated by scripts/web/compile_validators.mjs from ${modelId}'s input schema. Do not edit.`,
    ...imports.map((specifier, index) => `import * as __runtime${index} from "${specifier}.js";`),
    // A CommonJS module's exports, whether a bundler or Node imported it.
    "const __cjs = (ns) => (ns.default && typeof ns.default === \"object\" && \"__esModule\" in ns.default ? ns.default : ns);",
    "const exports = {};",
    body.replace(/^"use strict";/, ""),
    "export default exports;",
    `export const schema = ${JSON.stringify(formSchema(model.input_schema))};`,
    `export const members = ${JSON.stringify(memberSchemas(formSchema(model.input_schema)))};`,
    `export const schemaSha256 = "${schemaSha256(model.input_schema)}";`,
    `export const examples = ${JSON.stringify(model.examples)};`,
    "",
  ].join("\n");
}

function main() {
  const { compileSchemaValidatorsCode } = require("@rjsf/validator-ajv8/compileSchemaValidators");
  const { getDiscriminatorFieldFromSchema, hashForSchema, schemaParser } = require("@rjsf/utils");
  const Ajv2020 = require("ajv/dist/2020").default;
  const registry = JSON.parse(readFileSync(join(GENERATED, "registry.json"), "utf8"));
  mkdirSync(OUT, { recursive: true });
  const written = new Set();
  for (const model of registry.models) {
    const schema = formSchema(model.input_schema);
    const parsed = new Set(Object.keys(schemaParser(schema)));
    const options = [...optionSchemas(schema, hashForSchema, getDiscriminatorFieldFromSchema)].filter(
      ([key]) => !parsed.has(key),
    );
    const members = memberSchemas(schema);
    // The schemas are JSON Schema 2020-12, as Pydantic writes them; line breaks
    // add nothing to code no one reads. RJSF's own parse gives the root and
    // its discriminators; the options join through its extenderFn hook.
    const code = compileSchemaValidatorsCode(schema, {
      AjvClass: Ajv2020,
      ajvOptionsOverrides: { code: { lines: false } },
      extenderFn: (ajv) => {
        for (const [key, asked] of options) {
          const definitions = JSON.stringify(asked).includes('"$ref"') ? { $defs: schema.$defs } : {};
          ajv.addSchema({ ...asked, ...definitions, $id: key });
        }
        for (const member of Object.values(members)) ajv.addSchema(member);
        return ajv;
      },
    });
    const name = `${model.id}.js`;
    writeFileSync(join(OUT, name), toModule(code, model));
    written.add(name);
  }
  for (const file of readdirSync(OUT)) {
    if (!written.has(file)) rmSync(join(OUT, file));
  }
  process.stdout.write(`compile_validators: ${written.size} validators in ${OUT}\n`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main();
}
