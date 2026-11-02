// web/src/lib/calculator.ts
// What a model's calculator derives from its input schema and its page's site
// data (Phase 5 Step 6; ADR-0013 decisions 8 and 11), as pure functions the
// island and the tests share: the form's uiSchema (labels and help from each
// field's title, description, unit and bounds; a calculation selector for a
// family; arrays entered as lists), the fields a data profile binds for the
// chosen calculation and whether hosted mode can serve them, and the inputs a
// run posts. Nothing here reads the network or storage.
import { bounds, cardOrder, isNode, members, unit, variables, type Node, type VariableTable } from "@/lib/models";
import type { ChartSpec } from "@/lib/figure";
import type { Model } from "@/lib/registry-schema";
import type { ConceptEntry, ProblemEntry, SourceEntry, SurfaceEntry } from "@/lib/site-data";

/** A data profile's bound fields, as surfaces.json says hosted mode can serve them. */
export interface HostedProfile {
  profile: string;
  hosted: boolean;
  fields: { field: string; hosted: boolean }[];
}

/** One model's example: the form's prefilled values. */
export interface Example {
  name: string;
  note: string | null;
  inputs: Record<string, unknown>;
}

/** The calculator's props: what its page knows at build time, all small. */
export interface CalculatorProps {
  modelId: string;
  /** The output variables tables (models.ts variables()), one per calculation. */
  outputs: VariableTable[];
  charts: ChartSpec[];
  profiles: HostedProfile[];
  /** Data providers' names by id, for the sources panel. */
  sourceNames: Record<string, string>;
  /** The problems that point to local mode, and the command they give for this model. */
  localSlugs: string[];
  localCommand: string;
}

/** The discriminator a family's members carry (core: CALCULATION_FIELD). */
export const CALCULATION = "calculation";

/** The placeholder problems.json's local command holds for the model id. */
const MODEL_PLACEHOLDER = "<model-id>";

/**
 * A model page's calculator props, at build time: its output tables, charts,
 * hosted profiles, the names of the providers its bindings may read, and the
 * local-mode command the problems that point there give.
 */
export function calculatorProps(
  model: Model,
  surface: SurfaceEntry,
  problems: readonly ProblemEntry[],
  sources: readonly SourceEntry[],
  concepts: readonly ConceptEntry[],
): CalculatorProps {
  const byConcept = new Map(concepts.map((concept) => [concept.id, concept]));
  const providers = new Set(
    model.bindings.flatMap((binding) => byConcept.get(binding.concept)?.candidates.map((c) => c.provider) ?? []),
  );
  const local = problems.filter((problem) => problem.local_command !== null);
  return {
    modelId: model.id,
    outputs: variables(model.output_schema, cardOrder(model.card, "Outputs")),
    charts: model.charts as unknown as ChartSpec[],
    profiles: surface.profiles,
    sourceNames: Object.fromEntries(sources.filter((s) => providers.has(s.id)).map((s) => [s.id, s.name])),
    localSlugs: local.map((problem) => problem.slug),
    localCommand: (local[0]?.local_command ?? `pyeconomics models run ${MODEL_PLACEHOLDER} --inputs FILE`).replace(
      MODEL_PLACEHOLDER,
      model.id,
    ),
  };
}

/** A family's calculations, in the schema's order: each const and its words. */
export function calculations(schema: Node): { value: string; label: string }[] {
  return members(schema)
    .filter((member): member is [string, Node] => member[0] !== null)
    .map(([value, node]) => {
      const properties = isNode(node.properties) ? node.properties : {};
      const field = isNode(properties.calculation) ? properties.calculation : {};
      const words = typeof field.description === "string" ? field.description : value;
      return { value, label: `${words} (${value})` };
    });
}

/** The field help the form shows under a field: its unit and bounds; a choice or flag has no unit to show. */
export function fieldHelp(node: Node): string {
  const kind = unit(node);
  const parts = kind === "text" || kind === "flag" ? [] : [`Unit: ${kind}`];
  const range = bounds(node);
  if (range) parts.push(range);
  return parts.join("; ");
}

/** A field's label when its schema has no title (a $ref to an enum): `day_count` is "Day count". */
export function fieldTitle(name: string): string {
  const words = name.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function optionIndex(options: readonly unknown[], wantNull: boolean): number {
  return options.findIndex((option) => isNode(option) && (option.type === "null") === wantNull);
}

function resolve(node: Node, definitions: Node): Node {
  const ref = node.$ref;
  if (typeof ref !== "string") return node;
  const target = definitions[ref.split("/").at(-1) ?? ""];
  return isNode(target) ? { ...target, ...node } : node;
}

function fieldUi(raw: Node, definitions: Node, hidden: boolean, name?: string): Record<string, unknown> {
  if (hidden) return { "ui:widget": "hidden" };
  const titled = name !== undefined && typeof raw.title !== "string" ? { "ui:title": fieldTitle(name) } : {};
  const options = raw.anyOf;
  if (Array.isArray(options)) {
    const value = optionIndex(options, false);
    const empty = optionIndex(options, true);
    if (value >= 0 && empty >= 0 && options.length === 2) {
      const inner = resolve(options.at(value) as Node, definitions);
      // The help sits once beside the field, not again inside its value option.
      const { "ui:help": help, ...valueUi } = fieldUi({ ...inner, ...raw, anyOf: undefined }, definitions, false);
      const ui = options.map((_, index) =>
        index === value ? { "ui:title": "A value", ...valueUi } : { "ui:title": "None (null)" },
      );
      return { ...titled, anyOf: ui, "ui:help": help };
    }
  }
  const node = resolve(raw, definitions);
  const help = fieldHelp(node);
  const ui: Record<string, unknown> = { ...titled, ...(help ? { "ui:help": help } : {}) };
  // An array is one text box (src/lib/lists.ts), RJSF's custom-widget path.
  if (node.type === "array") ui["ui:widget"] = "list";
  return ui;
}

function objectUi(node: Node, definitions: Node, hide: ReadonlySet<string>): Record<string, unknown> {
  const properties = isNode(node.properties) ? node.properties : {};
  return Object.fromEntries(
    Object.entries(properties)
      .filter((entry): entry is [string, Node] => isNode(entry[1]))
      .map(([name, raw]) => [name, fieldUi(raw, definitions, name === CALCULATION || hide.has(name), name)]),
  );
}

/**
 * The form's uiSchema: no title or description for the form itself (the
 * page has both); for a family, a "Calculation" selector whose options carry
 * each calculation's words; each field's label and help; arrays as lists (the
 * `list` widget); a nullable field's two options named; and the fields in
 * `hide` (bound to data) hidden.
 */
export function uiSchemaFor(schema: Node, hide: readonly string[] = []): Record<string, unknown> {
  const definitions = isNode(schema.$defs) ? schema.$defs : {};
  const hidden = new Set(hide);
  const base = { "ui:submitButtonOptions": { norender: true } };
  if (Array.isArray(schema.oneOf)) {
    const labels = calculations(schema);
    return {
      ...base,
      "ui:title": "Calculation",
      "ui:options": { label: false },
      oneOf: members(schema).map(([, node], index) => ({
        "ui:title": labels.at(index)?.label,
        "ui:options": { label: false },
        ...objectUi(node, definitions, hidden),
      })),
    };
  }
  return { ...base, "ui:options": { label: false }, ...objectUi(schema, definitions, hidden) };
}

/** The properties of the calculation an input object names, or of the only one. */
export function propertiesFor(schema: Node, calculation: unknown): string[] {
  const found = members(schema).find(([value]) => value === null || value === calculation);
  const properties = found && isNode(found[1].properties) ? found[1].properties : {};
  return Object.keys(properties);
}

/**
 * The fields a profile binds for the chosen calculation (a family reads only
 * that calculation's fields), each with whether hosted mode can serve it.
 */
export function boundFields(
  schema: Node,
  profile: HostedProfile | undefined,
  calculation: unknown,
): { field: string; hosted: boolean }[] {
  if (!profile) return [];
  const names = new Set(propertiesFor(schema, calculation));
  return profile.fields.filter((field) => names.has(field.field));
}

/**
 * The inputs a run posts: the form's values, less those the data fills (in
 * live mode, the bound fields) and any value left undefined.
 */
export function runInputs(
  formData: Readonly<Record<string, unknown>> | undefined,
  drop: readonly string[] = [],
): Record<string, unknown> {
  const dropped = new Set(drop);
  return Object.fromEntries(
    Object.entries(formData ?? {}).filter(([name, value]) => value !== undefined && !dropped.has(name)),
  );
}

/** A validation error as far as tidyErrors reads it (RJSFValidationError). */
interface FormError {
  name?: string;
  property?: string;
  params?: unknown;
}

/**
 * A form's errors without the noise of a nullable field's anyOf: when a
 * field has errors beside "must match a schema in anyOf" and "must be null",
 * only the others say what its value broke.
 */
export function tidyErrors<E extends FormError>(errors: readonly E[]): E[] {
  const count = new Map<string | undefined, number>();
  for (const error of errors) count.set(error.property, (count.get(error.property) ?? 0) + 1);
  const noise = (error: E): boolean =>
    error.name === "anyOf" ||
    error.name === "oneOf" ||
    (error.name === "type" && (error.params as { type?: unknown } | undefined)?.type === "null");
  return errors.filter((error) => (count.get(error.property) ?? 0) === 1 || !noise(error));
}

/** The output table of a result's calculation, or the only one. */
export function outputTable(tables: readonly VariableTable[], calculation: unknown): VariableTable | undefined {
  return tables.find((table) => table.calculation === null || table.calculation === calculation) ?? tables[0];
}

/** A problem's slug, from its type URI. */
export function problemSlug(type: unknown): string | null {
  if (typeof type !== "string") return null;
  const match = /^https:\/\/pyeconomics\.dev\/problems\/([a-z0-9-]+)$/.exec(type);
  return match?.[1] ?? null;
}

/** The page that explains a problem, on this site. */
export function problemPage(slug: string): string {
  return `/problems/${slug}/`;
}
