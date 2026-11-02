// web/src/lib/models.ts
// What a model page shows, derived from its registry.json entry at build time
// (ADR-0013 decision 2): its permanent URL, its variables tables (the card's
// own rules for units and bounds, src/pyeconomics/core/cards.py, which a test
// holds equal to each card), its data bindings joined to the catalog's
// candidates, its citations' links and the words for its evidence status.
// Pure functions over the site data: nothing here reads a file or reaches the
// browser.
import { DOCUMENTATION } from "@/lib/links";
export { ORIGIN, domainPath, domainSegment, domainTitle, idOfPath, modelPath } from "@/lib/paths";
import type { Binding, Cost, Evidence, Model, Reference } from "@/lib/registry-schema";
import type { ConceptEntry, SourceEntry } from "@/lib/site-data";

/** A model's page in the documentation, which docs/_ext/model_pages.py writes. */
export function docsUrl(id: string): string {
  const [domain = "", name = ""] = id.split(".");
  return `${DOCUMENTATION}reference/models/${domain}/${name}.html`;
}

/** What each evidence status tells a reader (core/cards.py EVIDENCE_MEANING). */
export const EVIDENCE_MEANING: Readonly<Record<Evidence, string>> = {
  standard: "Textbook consensus, such as bond duration or the CAPM formula.",
  practitioner: "A widely used rule of thumb or convention.",
  contested: "Under active academic or policy debate.",
  rejected: "Failed out of sample; kept for history and teaching.",
  historical: "A superseded methodology, kept for reproducibility.",
};

/** What each cost class means for a hosted run (surfaces/budgets.py HOSTED_BUDGETS). */
export const COST_MEANING: Readonly<Record<Cost, string>> = {
  instant: "A closed-form calculation; a hosted run may take up to 2 seconds.",
  light: "A short numerical method; a hosted run may take up to 10 seconds.",
  heavy: "Estimation or simulation; a hosted run may take up to 30 seconds.",
};

/** A citation's link: its DOI, else its URL, else none. */
export function referenceLink(reference: Reference): string | null {
  if (reference.doi) return `https://doi.org/${reference.doi}`;
  return reference.url;
}

/** One row of a variables table, as the card writes it. */
export interface Variable {
  name: string;
  unit: string;
  bounds: string;
  description: string;
}

/** A variables table, labelled by its calculation when the model has several. */
export interface VariableTable {
  calculation: string | null;
  rows: Variable[];
}

/** A JSON Schema node. */
export type Node = Readonly<Record<string, unknown>>;

/** Whether a value is a JSON object. */
export function isNode(value: unknown): value is Node {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Python's `f"{value:g}"`: six significant digits, exponent outside [1e-4, 1e6). */
export function formatG(value: number): string {
  if (value === 0) return Object.is(value, -0) ? "-0" : "0";
  if (!Number.isFinite(value)) return value > 0 ? "inf" : "-inf";
  const [mantissa = "", power = "0"] = value.toExponential(5).split("e");
  const exponent = Number(power);
  const strip = (digits: string): string => (digits.includes(".") ? digits.replace(/\.?0+$/, "") : digits);
  if (exponent < -4 || exponent >= 6) {
    const sign = exponent < 0 ? "-" : "+";
    return `${strip(mantissa)}e${sign}${String(Math.abs(exponent)).padStart(2, "0")}`;
  }
  return strip(value.toFixed(Math.max(0, 5 - exponent)));
}

/** A field's bounds as the card writes them: `[0, 1]`, `(0, inf]`, or an array's length. */
export function bounds(node: Node): string {
  const items = node.items;
  if (isNode(items)) {
    const parts: string[] = [];
    const length: string[] = [];
    if ("minItems" in node) length.push(`min ${String(node.minItems)}`);
    if ("maxItems" in node) length.push(`max ${String(node.maxItems)}`);
    if (length.length > 0) parts.push(`length ${length.join(", ")}`);
    const inner = bounds(items);
    if (inner) parts.push(`each ${inner}`);
    return parts.join("; ");
  }
  const low = (node.minimum ?? node.exclusiveMinimum) as number | undefined;
  const high = (node.maximum ?? node.exclusiveMaximum) as number | undefined;
  if (low === undefined && high === undefined) {
    return "maxLength" in node ? `at most ${String(node.maxLength)} characters` : "";
  }
  const openLow = "exclusiveMinimum" in node;
  const openHigh = "exclusiveMaximum" in node;
  return (
    `${openLow ? "(" : "["}${low === undefined ? "-inf" : formatG(low)}, ` +
    `${high === undefined ? "inf" : formatG(high)}${openHigh ? ")" : "]"}`
  );
}

/** A field's unit as the card writes it: its x-unit, `flag` or `text`. */
export function unit(node: Node): string {
  const items = node.items;
  const inner = isNode(items) ? unit(items) : "";
  if ("x-unit" in node) return String(node["x-unit"]);
  if (inner) return `${inner} (array)`;
  if (node.type === "boolean") return "flag";
  return "text";
}

/** Look through an optional field's `anyOf` with null. */
export function unwrap(node: Node): Node {
  const options = node.anyOf;
  if (Array.isArray(options)) {
    const rest = options.filter((option): option is Node => isNode(option) && option.type !== "null");
    if (rest.length === 1 && rest[0]) {
      const outer = Object.fromEntries(Object.entries(node).filter(([key]) => key !== "anyOf"));
      return { ...rest[0], ...outer };
    }
  }
  return node;
}

/** A schema's object schemas, each with its calculation when it is a union. */
export function members(schema: Node): [string | null, Node][] {
  const definitions = isNode(schema.$defs) ? schema.$defs : {};
  const options = schema.oneOf;
  if (!Array.isArray(options) || options.length === 0) return [[null, schema]];
  return options.filter(isNode).map((option) => {
    const ref = option.$ref;
    const target = typeof ref === "string" ? definitions[ref.split("/").at(-1) ?? ""] : option;
    const node = isNode(target) ? target : {};
    const properties = isNode(node.properties) ? node.properties : {};
    const calculation = isNode(properties.calculation) ? properties.calculation.const : undefined;
    return [typeof calculation === "string" ? calculation : null, node];
  });
}

/**
 * The field names of each variables table the card writes under a heading
 * ("Inputs" or "Outputs"), in the card's order: the order the model declares
 * its fields, which registry.json's canonical JSON, sorting every object's
 * keys, does not keep. Only the backquoted names are read from the card.
 */
export function cardOrder(card: string, heading: "Inputs" | "Outputs"): string[][] {
  const start = card.indexOf(`\n### ${heading}\n`);
  if (start < 0) return [];
  const next = card.indexOf(heading === "Inputs" ? "\n### Outputs\n" : "\n## ", start + 1);
  const tables: string[][] = [];
  let current: string[] | null = null;
  for (const line of card.slice(start, next < 0 ? undefined : next).split("\n")) {
    if (line.startsWith("#### ")) {
      current = [];
      tables.push(current);
    } else if (line.startsWith("| `")) {
      if (current === null) {
        current = [];
        tables.push(current);
      }
      current.push(line.slice(3, line.indexOf("`", 3)));
    }
  }
  return tables;
}

/**
 * One variables table per calculation of a model's input or output schema,
 * each table's rows in `order` (cardOrder's), any field it does not name last.
 */
export function variables(schema: Node, order: readonly (readonly string[])[] = []): VariableTable[] {
  return members(schema).map(([calculation, node], index) => {
    const properties = isNode(node.properties) ? node.properties : {};
    const names = order.at(index) ?? [];
    const rank = (name: string): number => {
      const at = names.indexOf(name);
      return at < 0 ? names.length : at;
    };
    const rows = Object.entries(properties)
      .filter((entry): entry is [string, Node] => isNode(entry[1]))
      .sort(([a], [b]) => rank(a) - rank(b))
      .map(([name, raw]) => {
        const prop = unwrap(raw);
        return {
          name,
          unit: unit(prop),
          bounds: bounds(prop),
          description: typeof prop.description === "string" ? prop.description : "",
        };
      });
    return { calculation, rows };
  });
}

/** How a page words each as-of rule and vintage policy (core/cards.py). */
const AS_OF_WORDS: Readonly<Record<Binding["as_of"], string>> = {
  last_on_or_before: "last observation on or before the date",
  period: "the observation of the period containing the date",
  window: "the last {window} observations on or before the date",
};
const VINTAGE_WORDS: Readonly<Record<Binding["vintage"], string>> = {
  real_time: "real time: as published by the date",
  latest: "latest: revised data",
};

/** A source that can fill a bound field's concept. */
export interface DataSource {
  provider: string;
  name: string;
  licence: string;
  hosted: boolean;
}

/** One bound field, joined to its concept and the sources that can fill it. */
export interface DataRow {
  field: string;
  shape: string | null;
  concept: string;
  conceptTitle: string;
  transform: string | null;
  rule: string;
  vintage: string;
  sources: DataSource[];
  hosted: boolean;
}

/** A profile's bound fields. */
export interface DataProfile {
  profile: string;
  rows: DataRow[];
}

/**
 * Each profile's bound fields with their concept, its candidates (provider,
 * licence class, whether hosted mode serves it) and the rules the binding
 * reads by, from concepts.json and sources.json. A concept the catalog lacks
 * fails the build: a page never shows a binding it cannot explain.
 */
export function dataProfiles(
  bindings: readonly Binding[],
  concepts: readonly ConceptEntry[],
  sources: readonly SourceEntry[],
): DataProfile[] {
  const byConcept = new Map(concepts.map((concept) => [concept.id, concept]));
  const names = new Map(sources.map((source) => [source.id, source.name]));
  const profiles = [...new Set(bindings.map((binding) => binding.profile))];
  return profiles.map((profile) => ({
    profile,
    rows: bindings
      .filter((binding) => binding.profile === profile)
      .map((binding) => {
        const concept = byConcept.get(binding.concept);
        if (!concept) throw new Error(`binding ${binding.field} names ${binding.concept}, which the catalog lacks`);
        let rule = AS_OF_WORDS[binding.as_of].replace("{window}", String(binding.window));
        let shape: string | null = null;
        if (binding.tenors !== null) {
          shape = `tenors in ${binding.tenors}`;
          rule = "the curve on or before the date: its last row, a value per tenor";
        } else if (binding.columns.length > 0) {
          shape = `columns ${binding.columns.join(", ")}`;
        }
        const candidates = concept.candidates.map((candidate) => ({
          provider: candidate.provider,
          name: names.get(candidate.provider) ?? candidate.provider,
          licence: candidate.licence ?? "derived",
          hosted: candidate.hosted,
        }));
        return {
          field: binding.field,
          shape,
          concept: concept.id,
          conceptTitle: concept.title,
          transform: binding.transform,
          rule,
          vintage: VINTAGE_WORDS[binding.vintage],
          sources: candidates,
          hosted: concept.hosted,
        };
      }),
  }));
}

/** The page's description: the summary, cut at a word to fit a search snippet. */
export function describe(model: Pick<Model, "summary">, limit = 160): string {
  const summary = model.summary.replace(/\s+/g, " ").trim();
  if (summary.length <= limit) return summary;
  const cut = summary.slice(0, limit - 1);
  return `${cut.slice(0, cut.lastIndexOf(" "))}…`;
}

/** JSON as the worked example shows it: two-space indentation. */
export function pretty(value: unknown): string {
  return JSON.stringify(value, null, 2);
}
