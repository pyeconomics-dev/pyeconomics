// web/src/lib/calculator.ts
// What a model's calculator derives from its input schema and its page's site
// data (Phase 5 Step 6; ADR-0013 decisions 8 and 11), as pure functions the
// island and the tests share: the form's uiSchema (labels and help from each
// field's title, description, unit and bounds; a calculation selector for a
// family; arrays entered as lists), the fields a data profile binds for the
// chosen calculation and whether hosted mode can serve them, and the inputs a
// run posts. Nothing here reads the network or storage.
import { bounds, cardOrder, dataProfiles, isNode, members, unit, variables, type DataProfile, type Node, type VariableTable } from "@/lib/models";
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
  /**
   * For each profile, the bound fields the hosted site may not serve, with
   * their concepts' titles, and the sources' names (issue #320): what the
   * live-data notice says before and after "Live data" is chosen.
   */
  liveNotes: LiveNote[];
  /** Data providers' names by id, for the sources panel. */
  sourceNames: Record<string, string>;
  /** The problems that point to local mode, and the command they give for this model. */
  localSlugs: string[];
  localCommand: string;
}

/** One profile's fields the hosted site may not serve, and the sources that would fill them. */
export interface LiveNote {
  profile: string;
  fields: { field: string; label: string }[];
  sources: string[];
}

/** Each profile's fields that no hosted-safe source answers, from the page's data profiles. */
export function liveNotes(profiles: readonly DataProfile[]): LiveNote[] {
  return profiles.flatMap((profile) => {
    const rows = profile.rows.filter((row) => !row.hosted);
    if (rows.length === 0) return [];
    const sources = [...new Set(rows.flatMap((row) => row.sources.filter((source) => !source.hosted).map((source) => source.name)))];
    return [{ profile: profile.profile, fields: rows.map((row) => ({ field: row.field, label: row.conceptTitle })), sources }];
  });
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
    liveNotes: liveNotes(dataProfiles(model.bindings, concepts, sources)),
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
  const parts =
    kind === "text" || kind === "flag" ? [] : DECIMAL_UNITS.has(kind) ? [`${capitalise(kind)}, as a decimal (0.05 is 5%)`] : [`Unit: ${kind}`];
  const range = boundsInWords(bounds(node));
  if (range) parts.push(range);
  return parts.join("; ");
}

/** Units whose values are decimals a visitor might type as percents (ADR-0008). */
const DECIMAL_UNITS: ReadonlySet<string> = new Set(["rate", "return", "yield"]);

function capitalise(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** A bound as a reader writes it: 1e+12 is 1,000,000,000,000. */
function numberInWords(text: string): string {
  const value = Number(text);
  if (!Number.isFinite(value)) return text;
  return Math.abs(value) >= 10_000 && Number.isInteger(value) ? value.toLocaleString("en-US") : String(value);
}

/**
 * Interval notation in words (Phase 5 Step 17's round 0: "[0, 1e+12]" read as
 * machine text): "[0, inf]" is "0 or more", "[0, 1]" is "from 0 to 1".
 */
export function boundsInWords(range: string): string {
  const match = /^([[(])\s*([^,]+),\s*([^\])]+)([\])])$/.exec(range.trim());
  if (!match) return range;
  const [, open = "[", low = "", high = "", close = "]"] = match;
  const lowOpen = open === "(";
  const highOpen = close === ")";
  const unbounded = (text: string) => /^[-+]?inf$/i.test(text.trim());
  if (unbounded(low) && unbounded(high)) return "";
  if (unbounded(high)) return lowOpen ? `more than ${numberInWords(low)}` : `${numberInWords(low)} or more`;
  if (unbounded(low)) return highOpen ? `less than ${numberInWords(high)}` : `${numberInWords(high)} or less`;
  if (!lowOpen && !highOpen) return `from ${numberInWords(low)} to ${numberInWords(high)}`;
  return `more than ${lowOpen ? "" : "or equal to "}${numberInWords(low)} and less than ${highOpen ? "" : "or equal to "}${numberInWords(high)}`;
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
        index === value ? { "ui:title": "Enter a value", ...valueUi } : { "ui:title": "Leave it out" },
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

/** A validation error as RJSF hands it to transformErrors, as far as plainErrors reads it. */
interface PlainError {
  name?: string;
  property?: string;
  message?: string;
  stack: string;
  params?: unknown;
}

/**
 * The validator's messages in a visitor's words (Phase 5 Step 17's round 0:
 * "must have required property 'Fixed Costs'" and ".periods must be >= 0"):
 * the field's label first, then what it must be. Field-level messages keep
 * their placement; only the words change.
 */
export function plainErrors<E extends PlainError>(errors: readonly E[], label: (property: string) => string): E[] {
  return errors.map((error) => {
    const params = (error.params ?? {}) as { missingProperty?: string; limit?: number; type?: string };
    const field = (error.property ?? "").replace(/^\./, "");
    let message = error.message ?? "";
    if (error.name === "required" && params.missingProperty) {
      return { ...error, message: "This is required", stack: `${label(params.missingProperty)} is required` };
    }
    if (error.name === "minimum") message = `must be ${String(params.limit)} or more`;
    else if (error.name === "maximum") message = `must be ${String(params.limit)} or less`;
    else if (error.name === "exclusiveMinimum") message = `must be more than ${String(params.limit)}`;
    else if (error.name === "exclusiveMaximum") message = `must be less than ${String(params.limit)}`;
    else if (error.name === "type" && params.type === "number") message = "must be a number";
    else if (error.name === "type" && params.type === "integer") message = "must be a whole number";
    return { ...error, message, stack: field ? `${label(field)} ${message}` : capitalise(message) };
  });
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
