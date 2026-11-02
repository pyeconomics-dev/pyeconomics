// web/src/lib/validators.ts
// A calculator's model module (ADR-0013 decision 8): the validators
// scripts/web/compile_validators.mjs precompiled from the model's input schema,
// that schema, a family's member schemas, and the model's examples. Each
// model's module is its own chunk, loaded only when its calculator first
// renders, and each validator is built with RJSF's createPrecompiledValidator
// against the same schema object, so nothing is compiled in the browser (the
// policy has no 'unsafe-eval'). Only the precompiled validator's module is
// imported, never Ajv's compiler.
//
// A family's form is validated against its chosen calculation's member: its
// constant picks exactly one member, so the verdict is the root schema's, and
// the errors are that calculation's alone rather than every member's.
import createPrecompiledValidator from "@rjsf/validator-ajv8/lib/createPrecompiledValidator.js";
import type { RJSFSchema, ValidatorType } from "@rjsf/utils";
import type { ValidatorFunctions } from "@rjsf/validator-ajv8";

import type { Example } from "@/lib/calculator";

/** What compile_validators.mjs writes for one model. */
export interface ModelModule {
  default: ValidatorFunctions;
  schema: RJSFSchema;
  members: Record<string, RJSFSchema>;
  schemaSha256: string;
  examples: Example[];
}

/** A model's schema, examples and validator, ready for its form. */
export interface LoadedModel {
  schema: RJSFSchema;
  examples: Example[];
  validator: ValidatorType;
}

const MODULES = import.meta.glob<ModelModule>("../data/generated/validators/*.js");

/** The module path of a model's validators. */
export function modulePath(modelId: string): string {
  return `../data/generated/validators/${modelId}.js`;
}

/** The root validator, validating a family's data against its calculation's member. */
export function calculationValidator(
  root: ValidatorType,
  members: ReadonlyMap<string, { schema: RJSFSchema; validator: ValidatorType }>,
): ValidatorType {
  const memberOf = (formData: unknown) => {
    const calculation = typeof formData === "object" && formData !== null ? (formData as { calculation?: unknown }).calculation : undefined;
    return typeof calculation === "string" ? members.get(calculation) : undefined;
  };
  return {
    validateFormData(formData, schema, customValidate, transformErrors, uiSchema) {
      const member = memberOf(formData);
      if (!member) return root.validateFormData(formData, schema, customValidate, transformErrors, uiSchema);
      return member.validator.validateFormData(formData, member.schema, customValidate, transformErrors, uiSchema);
    },
    isValid: (schema, formData, rootSchema) => root.isValid(schema, formData, rootSchema),
    rawValidation: (schema, formData) => root.rawValidation(schema, formData),
  };
}

/** Build a model's validator from its module. */
export function fromModule(module: ModelModule): LoadedModel {
  const root = createPrecompiledValidator(module.default, module.schema);
  const members = new Map(
    Object.entries(module.members).map(([calculation, schema]) => [
      calculation,
      { schema, validator: createPrecompiledValidator(module.default, schema) },
    ]),
  );
  return {
    schema: module.schema,
    examples: module.examples,
    validator: members.size > 0 ? calculationValidator(root, members) : root,
  };
}

/** Load a model's module and build its validator. */
export async function loadModel(modelId: string): Promise<LoadedModel> {
  const load = MODULES[modulePath(modelId)];
  if (!load) throw new Error(`no validator was compiled for ${modelId}; run \`npm run data\``);
  return fromModule(await load());
}
