// web/src/workers/parse-file.ts
// The Web Worker that reads a user's file for "use my own data" (Phase 5 Step
// 9; ADR-0013 decision 11), so a large or hostile file never blocks the page.
// The page (src/lib/parse-file.ts) posts the File and the most rows it needs;
// the worker refuses a file over 5 MB or of another kind, reads a CSV with
// Papa Parse and the first sheet of an XLSX with read-excel-file, and posts
// back the cells as values: text, numbers, flags and dates as ISO text. A
// formula is read as nothing but the value its file last saved, and links,
// macros and other sheets are never read; no cell is evaluated. An XLSX whose
// parts declare more than 50 MB unpacked is refused before it is unzipped.
// It reads at most the rows asked for (and says it stopped), makes no
// request, and keeps nothing: the page terminates it after one file.
import { unzipSync } from "fflate";
import Papa from "papaparse";
import { readSheet } from "read-excel-file/web-worker";

import { MAX_FILE_BYTES, type Cell, type ParsedRows } from "@/lib/user-data";

/** The most an XLSX's parts may declare unpacked. */
const MAX_UNPACKED_BYTES = 50 * 1024 * 1024;

/** What the page posts. */
export interface ParseRequest {
  file: File;
  /** The most data rows to read, beside a header row. */
  maxRows: number;
}

/** What the worker posts back. */
export type ParseReply = { ok: true; parsed: ParsedRows } | { ok: false; reason: string };

function kindOf(file: File): "csv" | "xlsx" | null {
  const name = file.name.toLowerCase();
  if (name.endsWith(".csv")) return "csv";
  if (name.endsWith(".xlsx")) return "xlsx";
  return null;
}

function cellOf(value: unknown): Cell {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string" || typeof value === "boolean") return value;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value.toISOString().slice(0, 10);
  return null;
}

function readCsv(text: string, limit: number): ParsedRows {
  const result = Papa.parse<string[]>(text, { skipEmptyLines: "greedy", preview: limit + 1, dynamicTyping: false });
  const rows = result.data.map((row) => row.map((cell) => cellOf(cell)));
  const truncated = rows.length > limit || text.split(/\r?\n/).filter((line) => line.trim() !== "").length > rows.length;
  return { rows: rows.slice(0, limit), truncated, sheet: null };
}

function checkUnpacked(bytes: Uint8Array): void {
  let total = 0;
  unzipSync(bytes, {
    filter(entry) {
      total += entry.originalSize;
      return false;
    },
  });
  if (total > MAX_UNPACKED_BYTES) throw new Error("the workbook unpacks to more than 50 MB");
}

async function readXlsx(bytes: Uint8Array, limit: number): Promise<ParsedRows> {
  checkUnpacked(bytes);
  const rows = (await readSheet(bytes.buffer as ArrayBuffer)) as unknown[][];
  return { rows: rows.slice(0, limit).map((row) => row.map(cellOf)), truncated: rows.length > limit, sheet: "the first sheet" };
}

async function parse(request: ParseRequest): Promise<ParseReply> {
  const { file, maxRows } = request;
  const kind = kindOf(file);
  if (kind === null) return { ok: false, reason: "the file is not a .csv or an .xlsx file" };
  if (file.size > MAX_FILE_BYTES) return { ok: false, reason: "the file is larger than 5 MB" };
  // One header row beside the data rows.
  const limit = Math.max(1, Math.trunc(maxRows)) + 1;
  try {
    const parsed = kind === "csv" ? readCsv(await file.text(), limit) : await readXlsx(new Uint8Array(await file.arrayBuffer()), limit);
    return { ok: true, parsed };
  } catch (error) {
    return { ok: false, reason: `the file could not be read: ${error instanceof Error ? error.message : String(error)}` };
  }
}

/** The worker's global scope, as far as this module uses it. */
const scope = self as unknown as {
  addEventListener(type: "message", listener: (event: MessageEvent<ParseRequest>) => void): void;
  postMessage(message: ParseReply): void;
};

scope.addEventListener("message", (event) => {
  void parse(event.data).then((reply) => scope.postMessage(reply));
});
