// web/tests/unit/compile-validators.test.ts
// scripts/web/compile_validators.mjs, which precompiles the calculators'
// validators at build time (ADR-0013 decision 8): the ES module it wraps
// around Ajv's code imports only Ajv's runtime and ajv-formats' checks; the
// schema it compiles drops only `$schema`; a family's members are compiled
// with the root's $defs; and every option RJSF asks the validator about while
// it picks a oneOf's or an anyOf's option is compiled too, keyed by RJSF's hash.
import { getDiscriminatorFieldFromSchema, hashForSchema, type RJSFSchema } from "@rjsf/utils";
import { describe, expect, it } from "vitest";

import {
  RUNTIME,
  formSchema,
  memberSchemas,
  optionSchemas,
  schemaSha256,
  toModule,
} from "../../../scripts/web/compile_validators.mjs";
import { registryData } from "@/lib/site-data";

const MODEL = { id: "toy.model", input_schema: { type: "object" }, examples: [] };

describe("the validator module", () => {
  it("imports the runtime it requires, and exports the validators, schema, members, hash and examples", () => {
    const code = '"use strict";exports["urn:x"] = validate1;const f = require("ajv/dist/runtime/ucs2length").default;function validate1(){}';
    const module = toModule(code, MODEL);
    expect(module).toContain('import * as __runtime0 from "ajv/dist/runtime/ucs2length.js";');
    expect(module).toContain("const f = __cjs(__runtime0).default;");
    expect(module).toContain("export default exports;");
    expect(module).toContain(`export const schemaSha256 = "${schemaSha256(MODEL.input_schema)}";`);
    expect(module).toContain("export const members = {};");
    expect(RUNTIME).toEqual(["ajv/dist/runtime/ucs2length", "ajv-formats/dist/formats"]);
  });

  it("refuses a require it does not know and CommonJS beyond the exports", () => {
    expect(() => toModule('const x = require("fs");', MODEL)).toThrow(/requires fs/);
    expect(() => toModule("module.exports = 1;", MODEL)).toThrow(/CommonJS/);
  });
});

describe("the schemas compiled", () => {
  const family = registryData.models.find((model) => model.id === "fixed_income.duration")?.input_schema as Record<
    string,
    unknown
  >;

  it("drop only the $schema keyword, so RJSF keeps the $refs as written", () => {
    const form = formSchema(family);
    expect(form).not.toHaveProperty("$schema");
    expect({ ...form, $schema: family.$schema }).toEqual(family);
  });

  it("include each family member with the root's $defs and an $id of its own", () => {
    const members = memberSchemas(formSchema(family));
    expect(Object.keys(members).sort()).toEqual(["dv01", "effective", "key_rate", "macaulay_modified"]);
    expect(members.dv01.$id).toBe(`${String(family.$id)}:dv01`);
    expect(members.dv01.$defs).toEqual(family.$defs);
    expect(members.dv01.properties.calculation.const).toBe("dv01");
    expect(memberSchemas({ type: "object" })).toEqual({});
  });

  it("include every option RJSF asks about, keyed by its hash: a nullable field's two among them", () => {
    const options = optionSchemas(formSchema(family), hashForSchema, getDiscriminatorFieldFromSchema);
    const date: RJSFSchema = { format: "date", type: "string", "x-unit": "date" };
    expect(options.get(hashForSchema(date))).toEqual(date);
    expect(options.get(hashForSchema({ type: "null" }))).toEqual({ type: "null" });
  });
});
