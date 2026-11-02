// web/src/lib/lists.ts
// How a calculator enters an array input (Phase 5 Step 6): as text, not as
// one control per element, because the models' arrays run to a thousand
// values (a GARCH series) and to matrices (a covariance). Numbers are
// separated by commas, spaces or new lines; text values (dates, names) and a
// matrix's rows take one line each. A token that is not a number stays text,
// so the precompiled validator names the field and its position rather than
// the value disappearing.

/** An array field's shape: a list of scalars, or a matrix of number rows. */
export interface ListShape {
  matrix: boolean;
  item: "number" | "integer" | "string" | "boolean";
}

type Schema = Readonly<Record<string, unknown>>;

function isSchema(value: unknown): value is Schema {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function itemKind(schema: unknown): ListShape["item"] {
  if (!isSchema(schema)) return "string";
  const type = schema.type;
  if (type === "number" || type === "integer" || type === "boolean") return type;
  if (Array.isArray(schema.enum) && schema.enum.every((value) => typeof value === "number")) return "number";
  return "string";
}

/** The shape of an array schema. */
export function listShape(schema: Schema): ListShape {
  const items = isSchema(schema.items) ? schema.items : {};
  if (items.type === "array") return { matrix: true, item: itemKind(items.items) };
  return { matrix: false, item: itemKind(items) };
}

function token(text: string, item: ListShape["item"]): unknown {
  if (item === "string") return text;
  if (item === "boolean") return text === "true" ? true : text === "false" ? false : text;
  const number = Number(text);
  return text !== "" && Number.isFinite(number) ? number : text;
}

function row(text: string, item: ListShape["item"]): unknown[] {
  return text
    .split(/[\s,;]+/)
    .filter((part) => part !== "")
    .map((part) => token(part, item));
}

function lines(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line !== "");
}

/** Read an array from its text. */
export function parseList(text: string, shape: ListShape): unknown[] {
  if (shape.matrix) return lines(text).map((line) => row(line, shape.item));
  if (shape.item === "string") return lines(text);
  return row(text, shape.item);
}

/** Write an array as its text; anything that is not an array is empty. */
export function formatList(value: unknown, shape: ListShape): string {
  if (!Array.isArray(value)) return "";
  if (shape.matrix) return value.map((items) => (Array.isArray(items) ? items.map(String).join(", ") : String(items))).join("\n");
  if (shape.item === "string") return value.map(String).join("\n");
  return value.map(String).join(", ");
}

/** What the form says under a list: how to separate its values. */
export function listHint(shape: ListShape): string {
  if (shape.matrix) return "One row per line, values separated by commas.";
  if (shape.item === "string") return "One value per line.";
  return "Values separated by commas, spaces or new lines.";
}
