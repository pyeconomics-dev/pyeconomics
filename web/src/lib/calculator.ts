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
import { pythonSnippet } from "@/lib/snippets";

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
  /** The model's own MCP tool, where the server gives it one beside run_model. */
  mcpTool: string | null;
  /** Each calculation's input fields in the order the model declares them (its card's). */
  inputOrder: string[][];
  /**
   * Whether the calculator shows the run as code beneath the form. The home
   * page, whose next section is the same model from code, turns it off.
   */
  snippets?: boolean;
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
    mcpTool: surface.mcp_tool,
    inputOrder: cardOrder(model.card, "Inputs"),
  };
}

/**
 * What each part of a loaded form adds to its card's height, in pixels, on a
 * phone (one column of fields) and on a wide card (two): fitted in Phase 5
 * Step 18 to all 50 models' measured cards at 390, 820 and 1440 pixels wide
 * (median error about 30 pixels, the largest 140). A list's box grows by a
 * line for each row of a matrix; a description that wraps adds a line.
 * tests/e2e/layout-shift.spec.ts holds the result: a page must not shift as
 * its calculator loads, so a form that outgrows these numbers fails there
 * (`node scripts/form-room.ts` prints each model's measured card against its
 * estimate; refit when the form's layout changes, as round 2 did).
 */
const ROOM = {
  narrow: { base: 84, row: 130, array: 214, extraRow: 14, optional: 5, openRow: 231, openArray: 285, examples: 75, profiles: 254, family: 131, anyArray: 110, descLine: 17 },
  wide: { base: 59, row: 131, array: 199, extraRow: 13, optional: 52, openRow: 228, openArray: 243, examples: 85, profiles: 165, family: 106, anyArray: 114, descLine: 10 },
} as const;

/**
 * What the run-as-code section adds to a card around its code box, in pixels:
 * the gap above it, its heading and sentence, the choices and the copy
 * control, which wrap onto more lines on a phone. Measured, not fitted: every
 * model's is the same.
 */
const CODE_FRAME = { narrow: 262, wide: 140 } as const;

/** A code box's height for a snippet of so many lines: 16 pixels a line and 24 of padding, up to its maximum (max-h-80). */
function codeBox(lines: number): number {
  return Math.min(320, 24 + 16 * lines);
}

/** The characters of a field's description a line holds, about, under a field. */
const DESCRIPTION_LINE = 44;

/**
 * The room a model's calculator takes once its form has loaded, in pixels, on
 * a phone and on a wide card, estimated from its schema and first example at
 * build time. The page holds that room before the form loads (round 0's M12
 * and round 1: pages shifted as a calculator loaded), so what follows the
 * calculator does not move when it arrives.
 */
export function formRoom(
  model: Pick<Model, "id" | "input_schema" | "examples">,
  profiles: number,
  snippets = true,
): { narrow: number; wide: number } {
  const schema = model.input_schema as Node;
  const definitions = isNode(schema.$defs) ? schema.$defs : {};
  const inputs = model.examples.at(0)?.inputs ?? {};
  const example = new Map(Object.entries(inputs));
  const found = members(schema).find(([calculation]) => calculation === null || calculation === example.get(CALCULATION));
  const node = found?.[1] ?? {};
  const fields = Object.entries(isNode(node.properties) ? node.properties : {}).filter(
    (entry): entry is [string, Node] => entry[0] !== CALCULATION && isNode(entry[1]),
  );
  const list = (raw: Node): boolean => {
    const resolved = resolve(raw, definitions);
    return resolved.type === "array" || (Array.isArray(resolved.anyOf) && resolved.anyOf.some((option) => isNode(option) && option.type === "array"));
  };
  const needed = fields.filter(([, raw]) => !nullable(raw));
  const optional = fields.filter(([, raw]) => nullable(raw));
  const arrays = needed.filter(([, raw]) => list(raw));
  const optionalArrays = optional.filter(([, raw]) => list(raw));
  const open = optional.some(([name]) => (example.get(name) ?? null) !== null);
  const shown = [...needed, ...(open ? optional : [])];
  // A list's box shows two lines, and up to eight for a matrix, one for each of its rows (ListWidget.tsx).
  const extraRows = [...arrays, ...(open ? optionalArrays : [])].reduce((total, [name]) => {
    const value = example.get(name);
    const rows = Array.isArray(value) && Array.isArray(value[0]) ? value.length : 1;
    return total + Math.min(8, Math.max(2, rows)) - 2;
  }, 0);
  const descriptionLines = shown.reduce((total, [, raw]) => {
    const words = typeof raw.description === "string" ? raw.description : "";
    return total + Math.max(0, Math.ceil(words.length / DESCRIPTION_LINE) - 1);
  }, 0);
  // The Python snippet the form first shows: the example's inputs for its calculation.
  const names = new Set([CALCULATION, ...fields.map(([name]) => name)]);
  const first = Object.fromEntries(Object.entries(inputs).filter(([name]) => names.has(name)));
  const lines = snippets ? pythonSnippet({ modelId: model.id, inputs: first }).trimEnd().split(/\n/).length : 0;
  const estimate = (size: "narrow" | "wide"): number => {
    const part = size === "narrow" ? ROOM.narrow : ROOM.wide;
    const perRow = size === "narrow" ? 1 : 2;
    return Math.round(
      part.base +
        part.row * Math.ceil((needed.length - arrays.length) / perRow) +
        part.array * arrays.length +
        part.extraRow * extraRows +
        (optional.length > 0 ? part.optional : 0) +
        (open ? part.openRow * Math.ceil((optional.length - optionalArrays.length) / perRow) + part.openArray * optionalArrays.length : 0) +
        (model.examples.length > 1 ? part.examples : 0) +
        (profiles > 0 ? part.profiles : 0) +
        (Array.isArray(schema.oneOf) ? part.family : 0) +
        (arrays.length + optionalArrays.length > 0 ? part.anyArray : 0) +
        (part.descLine * descriptionLines) / perRow +
        (snippets ? (size === "narrow" ? CODE_FRAME.narrow : CODE_FRAME.wide) + codeBox(lines) : 0),
    );
  };
  return { narrow: estimate("narrow"), wide: estimate("wide") };
}

/**
 * An example as the form's picker names it: its name in words; its note, when
 * it has one, is shown beneath the picker, where it can wrap.
 */
export function exampleLabel(example: Pick<Example, "name">): string {
  return fieldTitle(example.name);
}

/** A family's calculations, in the schema's order: each const and its words. */
export function calculations(schema: Node): { value: string; label: string }[] {
  return members(schema)
    .filter((member): member is [string, Node] => member[0] !== null)
    .map(([value, node]) => {
      const properties = isNode(node.properties) ? node.properties : {};
      const field = isNode(properties.calculation) ? properties.calculation : {};
      const words = typeof field.description === "string" ? field.description : fieldTitle(value);
      return { value, label: words };
    });
}

/** The field help the form shows under a field: its unit and bounds; a choice, a flag or a date has no unit to show. */
export function fieldHelp(node: Node): string {
  const kind = unit(node);
  const parts =
    kind === "text" || kind === "flag" || kind === "date"
      ? []
      : DECIMAL_UNITS.has(kind)
        ? [`${capitalise(kind)}, as a decimal (0.05 is 5%)`]
        : [`Unit: ${kind}`];
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

/**
 * Abbreviations an identifier's words keep in capitals: `formula_capm` is
 * "Formula CAPM", `ebit` is "EBIT". A word outside the set is written as it is.
 */
const ACRONYMS: ReadonlySet<string> = new Set([
  "aic", "aqi", "ar1", "bic", "capm", "cfo", "cpi", "depi", "dfl", "dol", "dsri", "dtl", "dv01", "ebit", "eur",
  "fcfe", "fcff", "ff3", "ff5", "ff6", "gjr", "gmi", "grs", "hac", "hlw", "hqic", "hrp", "irr", "kwf", "lvgi",
  "mirr", "nist", "npv", "oas", "pnl", "ppp", "pvgo", "rmse", "roa", "roe", "sgai", "sgi", "tata", "tfp", "tips",
  "usd", "vif", "wacc", "xirr", "xnpv",
]);

/**
 * An identifier as a reader's words (Phase 5 Step 18's round 1: field, output
 * and example names read as code): `yield_to_maturity` is "Yield to maturity",
 * `day_count` is "Day count", `formula_capm` is "Formula CAPM".
 */
export function fieldTitle(name: string): string {
  const words = name
    .split("_")
    .filter((word) => word !== "")
    .map((word) => (ACRONYMS.has(word) ? word.toUpperCase() : word))
    .join(" ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** The title Pydantic writes for a field it was given none for: `end_of_month` is "End Of Month". */
function automaticTitle(name: string): string {
  return name
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * The names of options whose ids are abbreviations a reader may not know:
 * day counts, covariance estimators, criteria and named rules. Every other
 * option is its id written as words. tests/unit/calculator.test.ts fails on a
 * name here that no model's schema offers.
 */
export const OPTION_NAMES: ReadonlyMap<string, string> = new Map(
  Object.entries({
    act_360: "Actual/360",
    act_365_fixed: "Actual/365 Fixed",
    act_act_icma: "Actual/Actual ICMA",
    act_act_isda: "Actual/Actual ISDA",
    adjusted_taylor_1993: "Adjusted Taylor (1993)",
    aic: "AIC",
    balanced_approach_shortfalls: "Balanced approach (shortfalls)",
    bic: "BIC",
    bond_equivalent: "Bond-equivalent",
    hac: "HAC",
    hc0: "HC0",
    hc1: "HC1",
    hc2: "HC2",
    hc3: "HC3",
    he_litterman: "He-Litterman",
    hqic: "HQIC",
    nelson_siegel: "Nelson-Siegel",
    newey_west: "Newey-West",
    nonrobust: "Non-robust",
    student_t: "Student's t",
    taylor_1993: "Taylor (1993)",
    taylor_1999: "Taylor (1999)",
    thirty_360_us: "30/360 US",
    thirty_e_360: "30E/360",
    two_sided: "Two-sided",
  }),
);

/**
 * An option as a select shows it: its name, with its id beside it where the
 * name does not spell the id ("Actual/Actual ICMA (act_act_icma)"), so the
 * value the API takes stays in view. A one- or two-letter code (a trend's
 * `c` or `ct`) stays as it is: its field's description says what it means.
 */
export function optionLabel(value: unknown): string {
  const id = String(value);
  if (/^[a-z]{1,2}$/.test(id) || id === "ctt") return id;
  const label = OPTION_NAMES.get(id) ?? fieldTitle(id);
  const plain = (text: string) => text.toLowerCase().replace(/[^a-z0-9]/g, "");
  return plain(label) === plain(id) ? label : `${label} (${id})`;
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

/** Whether a field may be left out: its schema takes a value or null. */
export function nullable(node: unknown): boolean {
  return isNode(node) && Array.isArray(node.anyOf) && optionIndex(node.anyOf, true) >= 0;
}

function fieldUi(raw: Node, definitions: Node, hidden: boolean, name?: string): Record<string, unknown> {
  if (hidden) return { "ui:widget": "hidden" };
  // A title the model wrote stays; one Pydantic made from the name ("End Of
  // Month") is written as words.
  const titled =
    name !== undefined && (typeof raw.title !== "string" || raw.title === automaticTitle(name))
      ? { "ui:title": fieldTitle(name) }
      : {};
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
  // A choice shows each option's name, not its id alone.
  if (Array.isArray(node.enum)) {
    ui["ui:enumNames"] = Object.fromEntries(node.enum.map((value) => [String(value), optionLabel(value)]));
  }
  return ui;
}

/**
 * The order a form shows an object's fields in: the fields a run cannot do
 * without first, then those with a default, each group in the order the model
 * declares them (its card's), not the alphabetical order of the schema's
 * canonical JSON (Phase 5 Step 18's round 1: a bond's settlement and maturity
 * sat below its conventions).
 */
export function fieldOrder(node: Node, declared: readonly string[] = []): string[] {
  const names = Object.keys(isNode(node.properties) ? node.properties : {});
  const known = declared.filter((name) => names.includes(name));
  const all = [...known, ...names.filter((name) => !known.includes(name))];
  const required = new Set(Array.isArray(node.required) ? node.required : []);
  return [...all.filter((name) => required.has(name)), ...all.filter((name) => !required.has(name))];
}

function objectUi(node: Node, definitions: Node, hide: ReadonlySet<string>, declared: readonly string[] = []): Record<string, unknown> {
  const properties = isNode(node.properties) ? node.properties : {};
  return {
    "ui:order": fieldOrder(node, declared),
    ...Object.fromEntries(
      Object.entries(properties)
        .filter((entry): entry is [string, Node] => isNode(entry[1]))
        .map(([name, raw]) => [name, fieldUi(raw, definitions, name === CALCULATION || hide.has(name), name)]),
    ),
  };
}

/**
 * The form's uiSchema: no title or description for the form itself (the
 * page has both); for a family, a "Calculation" selector whose options carry
 * each calculation's words; each field's label and help; arrays as lists (the
 * `list` widget); a nullable field's two options named; the fields in `hide`
 * (bound to data) hidden; and each calculation's fields in `order`, the
 * model's own (fieldOrder).
 */
export function uiSchemaFor(schema: Node, hide: readonly string[] = [], order: readonly (readonly string[])[] = []): Record<string, unknown> {
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
        ...objectUi(node, definitions, hidden, order.at(index)),
      })),
    };
  }
  return { ...base, "ui:options": { label: false }, ...objectUi(schema, definitions, hidden, order.at(0)) };
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
