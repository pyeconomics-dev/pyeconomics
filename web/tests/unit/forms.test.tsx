// web/tests/unit/forms.test.tsx
// Every model's calculator form (Phase 5 Step 6; ADR-0013 decision 8), with
// the validators scripts/web/compile_validators.mjs precompiled: rendered
// through React's server renderer with each of the model's examples, and for
// a family each calculation's defaults, without a validator missing for any
// schema RJSF asks about; each example validates with no error, and the
// inputs a run would post are the example's own.
import Form from "@rjsf/shadcn";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import ListWidget from "@/components/calculator/ListWidget";
import SelectWidget from "@/components/calculator/SelectWidget";
import { CALCULATION, calculations, propertiesFor, runInputs, uiSchemaFor } from "@/lib/calculator";
import { registryData } from "@/lib/site-data";
import { fromModule, type ModelModule } from "@/lib/validators";

const MODULES = import.meta.glob<ModelModule>("../../src/data/generated/validators/*.js", { eager: true });
const WIDGETS = { list: ListWidget, SelectWidget };

function moduleOf(id: string): ModelModule {
  const module = MODULES[`../../src/data/generated/validators/${id}.js`];
  if (!module) throw new Error(`no validator for ${id}: run \`npm run data\``);
  return module;
}

describe("every model's form", () => {
  it("has a validator module for every model and no other", () => {
    const ids = Object.keys(MODULES).map((path) => path.split("/").at(-1)?.replace(/\.js$/, ""));
    expect(ids.sort()).toEqual(registryData.models.map((model) => model.id).sort());
  });

  for (const model of registryData.models) {
    it(`${model.id} renders and validates each example with no error`, () => {
      const { schema, examples, validator } = fromModule(moduleOf(model.id));
      expect(examples).toEqual(model.examples);
      const uiSchema = uiSchemaFor(schema);
      for (const example of examples) {
        const html = renderToString(
          <Form schema={schema} uiSchema={uiSchema} validator={validator} widgets={WIDGETS} formData={example.inputs} />,
        );
        expect(html, example.name).toContain("<form");
        const { errors } = validator.validateFormData(example.inputs, schema);
        expect(errors.map((error) => error.stack), example.name).toEqual([]);
        const posted = runInputs(
          Object.fromEntries(
            Object.entries(example.inputs).filter(([name]) => propertiesFor(schema, example.inputs.calculation).includes(name)),
          ),
        );
        expect(posted, example.name).toEqual(example.inputs);
      }
      for (const { value } of calculations(schema)) {
        expect(() =>
          renderToString(
            <Form schema={schema} uiSchema={uiSchema} validator={validator} widgets={WIDGETS} formData={{ [CALCULATION]: value }} />,
          ),
        ).not.toThrow();
      }
    });
  }

  it("refuses an input the schema does not take", () => {
    const model = registryData.models.find((entry) => entry.id === "fixed_income.duration");
    const { schema, examples, validator } = fromModule(moduleOf("fixed_income.duration"));
    const { errors } = validator.validateFormData({ ...examples[0]?.inputs, not_an_input: 1 }, schema);
    expect(model).toBeDefined();
    expect(errors.length).toBeGreaterThan(0);
  });
});
