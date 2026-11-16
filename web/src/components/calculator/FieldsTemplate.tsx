// web/src/components/calculator/FieldsTemplate.tsx
// How the calculator lays out an object's fields (Phase 5 Step 18's round 1:
// a form of a dozen fields ran several screens, with its optional inputs mixed
// among the rest). The fields a run needs come first, two to a row where the
// card is wide enough (a container query, so the home page's narrower card
// and a phone get one column); a field that may be left out (its schema takes
// a value or null) sits in a disclosure after them, which names those fields
// and opens when any holds a value. A field with a default is never hidden:
// its value changes the result. RJSF's own object template, without the
// add-a-property button no model's schema asks for.
import type { ObjectFieldTemplateProps } from "@rjsf/utils";
import { useState } from "react";

import { fieldTitle, nullable } from "@/lib/calculator";
import { isNode } from "@/lib/models";

const GRID = "grid grid-cols-1 items-start gap-x-6 gap-y-4 @xl:grid-cols-2";

/** Whether a field takes the card's whole width: a list of values, or a value with its own choice. */
function wide(node: unknown): boolean {
  if (!isNode(node)) return false;
  if (node.type === "array") return true;
  return Array.isArray(node.anyOf) && node.anyOf.some((option) => isNode(option) && option.type === "array");
}

export default function FieldsTemplate({ title, properties, schema, formData }: ObjectFieldTemplateProps) {
  const nodes = new Map(Object.entries(isNode(schema.properties) ? schema.properties : {}));
  const values = new Map(Object.entries(isNode(formData) ? formData : {}));
  const shown = properties.filter((property) => !property.hidden);
  const needed = shown.filter((property) => !nullable(nodes.get(property.name)));
  const optional = shown.filter((property) => nullable(nodes.get(property.name)));
  const filled = optional.filter((property) => (values.get(property.name) ?? null) !== null).length;
  // Open from the start when the example fills one; after that the visitor decides.
  const [open, setOpen] = useState(filled > 0);
  const cell = (name: string) => (wide(nodes.get(name)) ? "min-w-0 @xl:col-span-2" : "min-w-0");
  return (
    <div className="@container flex flex-col gap-4" data-fields="">
      {title && <p className="font-medium">{title}</p>}
      <div className={GRID}>
        {needed.map((property) => (
          <div key={property.name} className={cell(property.name)}>
            {property.content}
          </div>
        ))}
      </div>
      {optional.length > 0 && (
        <details
          className="rounded-md border px-4"
          data-optional-fields=""
          open={open}
          onToggle={(event) => setOpen(event.currentTarget.open)}
        >
          <summary className="cursor-pointer py-3 text-sm font-medium">
            {optional.length === 1 ? "1 optional input" : `${String(optional.length)} optional inputs`}:{" "}
            <span className="font-normal text-muted-foreground">
              {optional.map((property) => fieldTitle(property.name)).join(", ")}
            </span>
          </summary>
          <div className={`${GRID} pb-4`}>
            {optional.map((property) => (
              <div key={property.name} className={cell(property.name)}>
                {property.content}
              </div>
            ))}
          </div>
        </details>
      )}
      {properties
        .filter((property) => property.hidden)
        .map((property) => (
          <div key={property.name} className="hidden">
            {property.content}
          </div>
        ))}
    </div>
  );
}
