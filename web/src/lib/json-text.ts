// web/src/lib/json-text.ts
// JSON as a page shows it (Phase 5 Step 18's round 2). JSON.stringify's
// indented form gives a list one value to a line, so a year of monthly returns
// was a dozen lines of a code box: here a list of plain values stays on one
// line while it is short, and otherwise fills lines a phone's code box shows
// whole. The text parses to the same value (tests/unit/snippets.test.ts holds
// that for every golden case's inputs); only its white space differs.

/** The longest list of plain values kept on one line, in characters. */
export const LIST_LINE = 56;

/** The widest line a longer list is filled to, its indentation included: what a phone's code box shows. */
export const LIST_WIDTH = 36;

const INDENT = "  ";

function plain(value: unknown): boolean {
  return typeof value !== "object" || value === null;
}

/**
 * Values written out, filled into lines no wider than LIST_WIDTH, each value
 * followed by its comma; the last one too when `trailing` (Python allows it,
 * JSON does not).
 */
export function fillLines(items: readonly string[], pad: string, trailing: boolean): string[] {
  const lines: string[] = [];
  let line = "";
  items.forEach((item, index) => {
    const piece = `${item}${index < items.length - 1 || trailing ? "," : ""}`;
    if (line !== "" && pad.length + line.length + 1 + piece.length > LIST_WIDTH) {
      lines.push(`${pad}${line}`);
      line = piece;
    } else {
      line = line === "" ? piece : `${line} ${piece}`;
    }
  });
  if (line !== "") lines.push(`${pad}${line}`);
  return lines;
}

/** A JSON value as indented text, its lists of plain values kept short. */
export function jsonText(value: unknown, depth = 0): string {
  const pad = INDENT.repeat(depth + 1);
  const end = INDENT.repeat(depth);
  if (Array.isArray(value)) {
    const items: unknown[] = value;
    if (items.length === 0) return "[]";
    if (items.every(plain)) {
      const texts = items.map((item) => JSON.stringify(item ?? null));
      const line = `[${texts.join(", ")}]`;
      return line.length <= LIST_LINE ? line : `[\n${fillLines(texts, pad, false).join("\n")}\n${end}]`;
    }
    return `[\n${items.map((item) => `${pad}${jsonText(item, depth + 1)}`).join(",\n")}\n${end}]`;
  }
  if (typeof value === "object" && value !== null) {
    const entries = Object.entries(value as Record<string, unknown>).filter(([, item]) => item !== undefined);
    if (entries.length === 0) return "{}";
    const lines = entries.map(([key, item]) => `${pad}${JSON.stringify(key)}: ${jsonText(item, depth + 1)}`);
    return `{\n${lines.join(",\n")}\n${end}}`;
  }
  return JSON.stringify(value ?? null);
}
