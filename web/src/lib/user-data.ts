// web/src/lib/user-data.ts
// "Use my own data" on a model page (Phase 5 Step 9; ADR-0013 decision 11),
// as pure functions the calculator and the tests share: the array fields a
// calculation takes (a list of numbers, dates or flags, or a matrix of number
// rows), each with its bounds; a parsed file's header row and columns; the
// values a column, or for a matrix several columns, gives a field, refused
// with a reason when a cell is not a value of the field's kind, a value is
// missing between others, or there are more rows than the field's maxItems;
// and a template CSV per model. The file itself is parsed in a Web Worker
// (src/workers/parse-file.ts) and never leaves the browser: only the mapped
// values reach the form, and from it the run's body. Nothing here reads the
// network or storage.
import { propertiesFor } from "@/lib/calculator";
import { listShape, type ListShape } from "@/lib/lists";
import { isNode, members, unwrap, type Node } from "@/lib/models";

/** The largest file the page reads: 5 MB (ADR-0013 decision 11). */
export const MAX_FILE_BYTES = 5 * 1024 * 1024;

/** One cell of a parsed file: text, a number, a flag, or empty. */
export type Cell = string | number | boolean | null;

/** What the worker hands back: the rows read, and whether it stopped early. */
export interface ParsedRows {
  rows: Cell[][];
  /** The file held more rows than the page reads (the largest field's maxItems). */
  truncated: boolean;
  /** The sheet read, for an XLSX file. */
  sheet: string | null;
}

/** A parsed file with its columns named: from its header row, or by position. */
export interface UserTable {
  columns: string[];
  rows: Cell[][];
  truncated: boolean;
  /** Whether the file's first row named the columns. */
  header: boolean;
}

/** An array field of a calculation, as the mapping reads it. */
export interface ArrayField {
  name: string;
  title: string;
  shape: ListShape;
  minItems: number;
  maxItems: number;
  /** For a matrix: the fewest and most values a row takes. */
  rowMin: number;
  rowMax: number;
}

/** A field's values from a file, or why the file cannot give them. */
export type Mapped = { ok: true; values: unknown[] } | { ok: false; reason: string };

function whole(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : fallback;
}

function resolved(node: Node, definitions: Node): Node {
  const ref = node.$ref;
  const target = typeof ref === "string" ? definitions[ref.split("/").at(-1) ?? ""] : null;
  return unwrap(isNode(target) ? { ...target, ...node } : node);
}

/** The array fields of a calculation (or of the only one), in the schema's order. */
export function arrayFields(schema: Node, calculation: unknown): ArrayField[] {
  const definitions = isNode(schema.$defs) ? schema.$defs : {};
  const found = members(schema).find(([value]) => value === null || value === calculation);
  const properties = found && isNode(found[1].properties) ? found[1].properties : {};
  const names = new Set(propertiesFor(schema, calculation));
  return Object.entries(properties)
    .filter((entry): entry is [string, Node] => names.has(entry[0]) && isNode(entry[1]))
    .map(([name, raw]) => [name, resolved(raw, definitions)] as const)
    .filter(([, node]) => node.type === "array")
    .map(([name, node]) => {
      const items = isNode(node.items) ? resolved(node.items, definitions) : {};
      // A nullable array's bounds arrive as minLength and maxLength (#245);
      // the server enforces them either way.
      return {
        name,
        title: typeof node.title === "string" ? node.title : name,
        shape: listShape(node),
        minItems: whole(node.minItems ?? node.minLength, 0),
        maxItems: whole(node.maxItems ?? node.maxLength, 10_000),
        rowMin: whole(items.minItems, 1),
        rowMax: whole(items.maxItems, 1_000),
      };
    });
}

/** The most rows a model's file needs: its largest array field's maxItems. */
export function rowLimit(fields: readonly ArrayField[]): number {
  return Math.max(1, ...fields.map((field) => field.maxItems));
}

function isNumberText(cell: Cell): boolean {
  return typeof cell === "number" || (typeof cell === "string" && cell.trim() !== "" && Number.isFinite(Number(cell.trim())));
}

/**
 * Name a file's columns: its first row is a header when a cell of it is text
 * that is not a number; otherwise the columns are "Column 1", "Column 2"…
 */
export function withHeader(parsed: ParsedRows): UserTable {
  const width = Math.max(0, ...parsed.rows.map((row) => row.length));
  const first = parsed.rows.at(0) ?? [];
  const header = first.some((cell) => typeof cell === "string" && cell.trim() !== "" && !isNumberText(cell));
  const columns = Array.from({ length: width }, (_, index) => {
    const named = header ? first.at(index) : null;
    const text = typeof named === "string" ? named.trim() : named === null || named === undefined ? "" : String(named);
    return text || `Column ${String(index + 1)}`;
  });
  return { columns, rows: header ? parsed.rows.slice(1) : parsed.rows, truncated: parsed.truncated, header };
}

function cellAt(row: readonly Cell[] | undefined, column: number): Cell {
  return row?.at(column) ?? null;
}

function empty(cell: Cell): boolean {
  return cell === null || (typeof cell === "string" && cell.trim() === "");
}

/** A column's cells down to its last value: blanks after it are not rows. */
function columnCells(table: UserTable, column: number): Cell[] {
  const cells = table.rows.map((row) => cellAt(row, column));
  let last = cells.length - 1;
  while (last >= 0 && empty(cells.at(last) ?? null)) last -= 1;
  return cells.slice(0, last + 1);
}

/** Read one cell as a value of the field's item kind, or say why not. */
export function cellValue(cell: Cell, item: ListShape["item"]): { ok: true; value: unknown } | { ok: false } {
  if (item === "number" || item === "integer") {
    const value = typeof cell === "number" ? cell : typeof cell === "string" && cell.trim() !== "" ? Number(cell.trim()) : Number.NaN;
    if (!Number.isFinite(value) || (item === "integer" && !Number.isInteger(value))) return { ok: false };
    return { ok: true, value };
  }
  if (item === "boolean") {
    if (typeof cell === "boolean") return { ok: true, value: cell };
    const text = typeof cell === "string" ? cell.trim().toLowerCase() : typeof cell === "number" ? String(cell) : "";
    if (text === "true" || text === "1") return { ok: true, value: true };
    if (text === "false" || text === "0") return { ok: true, value: false };
    return { ok: false };
  }
  if (empty(cell)) return { ok: false };
  return { ok: true, value: typeof cell === "string" ? cell.trim() : String(cell) };
}

function countLimits(field: ArrayField, count: number, what: string): string | null {
  if (count > field.maxItems) {
    return `${what} has ${String(count)} rows; ${field.name} takes at most ${String(field.maxItems)}. Use a shorter range of rows.`;
  }
  if (count < field.minItems) {
    return `${what} has ${String(count)} rows; ${field.name} needs at least ${String(field.minItems)}.`;
  }
  return null;
}

/** The values one column gives a list field. */
export function mapColumn(table: UserTable, column: number, field: ArrayField): Mapped {
  const name = table.columns.at(column) ?? `Column ${String(column + 1)}`;
  const cells = columnCells(table, column);
  if (table.truncated && cells.length >= table.rows.length) {
    return { ok: false, reason: `${name} runs past the ${String(table.rows.length)} rows read; ${field.name} takes at most ${String(field.maxItems)}.` };
  }
  const limit = countLimits(field, cells.length, name);
  if (limit) return { ok: false, reason: limit };
  const values: unknown[] = [];
  for (const [index, cell] of cells.entries()) {
    const read = cellValue(cell, field.shape.item);
    if (!read.ok) {
      const kind = field.shape.item === "string" ? "a value" : `a ${field.shape.item}`;
      const row = index + 1 + (table.header ? 1 : 0);
      const problem = empty(cell) ? "is empty" : `is not ${kind}`;
      return { ok: false, reason: `${name}, row ${String(row)} of the file, ${problem}: ${field.name} takes ${kind} in every row.` };
    }
    values.push(read.value);
  }
  return { ok: true, values };
}

/** The rows several columns give a matrix field, one column per value of a row. */
export function mapColumns(table: UserTable, columns: readonly number[], field: ArrayField): Mapped {
  if (columns.length < field.rowMin || columns.length > field.rowMax) {
    return { ok: false, reason: `${field.name} takes ${String(field.rowMin)} to ${String(field.rowMax)} columns, not ${String(columns.length)}.` };
  }
  const read = columns.map((column) => mapColumn(table, column, { ...field, shape: { matrix: false, item: field.shape.item } }));
  const failed = read.find((entry) => !entry.ok);
  if (failed && !failed.ok) return failed;
  const lists = read.map((entry) => (entry.ok ? entry.values : []));
  const length = lists.at(0)?.length ?? 0;
  if (lists.some((list) => list.length !== length)) {
    return { ok: false, reason: `the columns for ${field.name} have different numbers of rows.` };
  }
  return { ok: true, values: Array.from({ length }, (_, row) => lists.map((list) => list.at(row))) };
}

function csvText(value: unknown): string {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

/**
 * A template CSV for a calculation's array fields: one column per list field
 * and one per value of a matrix row (`<field>_1`, `<field>_2`…), filled from
 * the example when it has values, so a user can replace them with their own.
 */
export function templateCsv(fields: readonly ArrayField[], example: Readonly<Record<string, unknown>>): string {
  const columns: { header: string; values: unknown[] }[] = [];
  const values = new Map(Object.entries(example));
  for (const field of fields) {
    const given = values.get(field.name);
    const list: unknown[] = Array.isArray(given) ? given : [];
    if (field.shape.matrix) {
      const width = Math.max(field.rowMin, ...list.map((row) => (Array.isArray(row) ? row.length : 0)));
      for (let index = 0; index < width; index += 1) {
        columns.push({
          header: `${field.name}_${String(index + 1)}`,
          values: list.map((row) => (Array.isArray(row) ? (row as unknown[]).at(index) : undefined)),
        });
      }
    } else {
      columns.push({ header: field.name, values: list });
    }
  }
  const height = Math.max(0, ...columns.map((column) => column.values.length));
  const lines = [columns.map((column) => csvText(column.header)).join(",")];
  for (let row = 0; row < height; row += 1) lines.push(columns.map((column) => csvText(column.values.at(row))).join(","));
  return `${lines.join("\r\n")}\r\n`;
}
