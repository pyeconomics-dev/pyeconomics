// web/src/components/calculator/UserDataPanel.tsx
// "Use my own data" (Phase 5 Step 9; ADR-0013 decision 11): a CSV or XLSX
// file, read in the browser by a Web Worker (src/lib/parse-file.ts), at most
// 5 MB and as many rows as the calculation's largest array field takes. The
// panel previews the first rows, lets the user choose a column for each list
// field (several, in order, for a matrix), and writes the values into the
// form; every value is checked against its field's kind and maxItems first
// (src/lib/user-data.ts). The file, its name and its other columns never
// leave the page: only the values written into the form travel, in the run's
// body. A template CSV for the calculation is built here, from its fields
// and example, with no request.
import { useMemo, useState } from "react";

import { buttonVariants } from "@/components/ui/button";
import type { Node } from "@/lib/models";
import { parseUserFile } from "@/lib/parse-file";
import {
  MAX_FILE_BYTES,
  arrayFields,
  mapColumn,
  mapColumns,
  rowLimit,
  templateCsv,
  withHeader,
  type ArrayField,
  type UserTable,
} from "@/lib/user-data";

/** The rows of a file the preview shows. */
const PREVIEW_ROWS = 5;
const CONTROL =
  "rounded-md border border-input bg-transparent px-3 py-1.5 text-sm shadow-xs focus-visible:border-ring " +
  "focus-visible:ring-[3px] focus-visible:ring-ring/50 outline-none";
const SMALL_BUTTON = buttonVariants({ variant: "outline", size: "sm" });

export interface UserDataPanelProps {
  modelId: string;
  schema: Node;
  calculation: unknown;
  /** The values the template is filled from: the chosen example's. */
  example: Readonly<Record<string, unknown>>;
  disabled: boolean;
  /** Write mapped values into the form. */
  onFill: (values: Record<string, unknown[]>) => void;
}

function saveText(text: string, filename: string): void {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function cellText(cell: unknown): string {
  return cell === null || cell === undefined ? "" : String(cell);
}

function fieldHint(field: ArrayField): string {
  const kind = field.shape.matrix ? "rows of numbers, one column per value" : `one column of ${field.shape.item === "string" ? "values" : `${field.shape.item}s`}`;
  return `${kind}; at most ${String(field.maxItems)} rows`;
}

export default function UserDataPanel({ modelId, schema, calculation, example, disabled, onFill }: UserDataPanelProps) {
  const fields = useMemo(() => arrayFields(schema, calculation), [schema, calculation]);
  const [table, setTable] = useState<UserTable | null>(null);
  const [reading, setReading] = useState(false);
  const [message, setMessage] = useState("");
  const [lists, setLists] = useState<ReadonlyMap<string, number>>(new Map());
  const [matrices, setMatrices] = useState<ReadonlyMap<string, readonly number[]>>(new Map());
  const [problems, setProblems] = useState<ReadonlyMap<string, string>>(new Map());
  const id = `user-data-${modelId.replace(".", "-")}`;

  if (fields.length === 0) return null;

  const read = async (file: File | undefined) => {
    setTable(null);
    setProblems(new Map());
    if (!file) return;
    if (file.size > MAX_FILE_BYTES) {
      setMessage("The file is larger than 5 MB: use a smaller file.");
      return;
    }
    setReading(true);
    setMessage("Reading the file in your browser…");
    try {
      const parsed = withHeader(await parseUserFile(file, rowLimit(fields)));
      setTable(parsed);
      setLists(new Map());
      setMatrices(new Map());
      const more = parsed.truncated ? ` It holds more rows than any field takes; only the first ${String(parsed.rows.length)} were read.` : "";
      setMessage(`Read ${String(parsed.rows.length)} rows and ${String(parsed.columns.length)} columns.${more} Choose a column for each field.`);
    } catch (error) {
      setMessage(`The file could not be read: ${error instanceof Error ? error.message : String(error)}.`);
    } finally {
      setReading(false);
    }
  };

  const fill = () => {
    if (!table) return;
    const values = new Map<string, unknown[]>();
    const found = new Map<string, string>();
    for (const field of fields) {
      const mapped = field.shape.matrix
        ? (matrices.get(field.name)?.length ?? 0) > 0
          ? mapColumns(table, matrices.get(field.name) ?? [], field)
          : null
        : lists.has(field.name)
          ? mapColumn(table, lists.get(field.name) ?? 0, field)
          : null;
      if (mapped === null) continue;
      if (mapped.ok) values.set(field.name, mapped.values);
      else found.set(field.name, mapped.reason);
    }
    setProblems(found);
    const filled = [...values.keys()];
    if (filled.length > 0) onFill(Object.fromEntries(values));
    setMessage(
      filled.length === 0 && found.size === 0
        ? "Choose a column for at least one field."
        : `${filled.length > 0 ? `Filled ${filled.join(", ")} from the file.` : ""}${found.size > 0 ? ` ${String(found.size)} field${found.size === 1 ? "" : "s"} could not be filled.` : ""}`.trim(),
    );
  };

  const toggle = (field: string, column: number, on: boolean) => {
    const current = matrices.get(field) ?? [];
    const next = on ? [...current, column].sort((a, b) => a - b) : current.filter((value) => value !== column);
    setMatrices(new Map([...matrices, [field, next]]));
  };

  return (
    <details className="rounded-md border p-4" data-user-data={modelId}>
      <summary className="cursor-pointer font-medium">Use my own data (CSV or XLSX)</summary>
      <div className="mt-4 flex flex-col gap-4 text-sm">
        <p className="max-w-3xl">
          Fill the list inputs from a file of your own. The file is read here, in your browser, and never uploaded: only
          the values you choose are written into the form and sent with the run. At most 5 MB; formulas count only as the
          values the file saved, and links and macros are ignored.
        </p>
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1">
            <span className="font-medium">File</span>
            <input
              id={`${id}-file`}
              type="file"
              accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              className={CONTROL}
              disabled={disabled || reading}
              onChange={(event) => void read(event.target.files?.[0])}
            />
          </label>
          <button
            type="button"
            className={SMALL_BUTTON}
            onClick={() => saveText(templateCsv(fields, example), `${modelId.replaceAll(".", "_")}_template.csv`)}
          >
            Download a template CSV
          </button>
        </div>
        <p role="status" aria-live="polite">
          {message}
        </p>
        {table && (
          <>
            <div className="overflow-x-auto" role="region" aria-label="The file's first rows" tabIndex={0}>
              <table className="w-full border-collapse text-left text-xs">
                <caption className="mb-2 text-left font-medium">
                  The first {String(Math.min(PREVIEW_ROWS, table.rows.length))} of {String(table.rows.length)} rows
                </caption>
                <thead>
                  <tr className="border-b">
                    {table.columns.map((column, index) => (
                      <th key={`${column}-${String(index)}`} scope="col" className="py-1 pr-3">
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {table.rows.slice(0, PREVIEW_ROWS).map((row, rowIndex) => (
                    <tr key={String(rowIndex)} className="border-b">
                      {table.columns.map((column, index) => (
                        <td key={`${column}-${String(index)}`} className="py-1 pr-3 font-mono">
                          {cellText(row.at(index))}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex flex-col gap-3">
              {fields.map((field) =>
                field.shape.matrix ? (
                  <fieldset key={field.name} className="flex flex-col gap-1" data-map-field={field.name}>
                    <legend className="font-medium">
                      <code>{field.name}</code> <span className="font-normal text-muted-foreground">({fieldHint(field)})</span>
                    </legend>
                    <div className="flex flex-wrap gap-3">
                      {table.columns.map((column, index) => (
                        <label key={`${column}-${String(index)}`} className="flex items-center gap-1">
                          <input
                            type="checkbox"
                            checked={(matrices.get(field.name) ?? []).includes(index)}
                            onChange={(event) => toggle(field.name, index, event.target.checked)}
                          />
                          {column}
                        </label>
                      ))}
                    </div>
                    {problems.get(field.name) && <p className="text-destructive">{problems.get(field.name)}</p>}
                  </fieldset>
                ) : (
                  <label key={field.name} className="flex flex-col gap-1" data-map-field={field.name}>
                    <span>
                      <code className="font-medium">{field.name}</code>{" "}
                      <span className="text-muted-foreground">({fieldHint(field)})</span>
                    </span>
                    <select
                      className={CONTROL}
                      value={lists.get(field.name) ?? ""}
                      onChange={(event) => {
                        const next = new Map(lists);
                        if (event.target.value === "") next.delete(field.name);
                        else next.set(field.name, Number(event.target.value));
                        setLists(next);
                      }}
                    >
                      <option value="">Not from the file</option>
                      {table.columns.map((column, index) => (
                        <option key={`${column}-${String(index)}`} value={index}>
                          {column}
                        </option>
                      ))}
                    </select>
                    {problems.get(field.name) && <span className="text-destructive">{problems.get(field.name)}</span>}
                  </label>
                ),
              )}
            </div>
            <div>
              <button type="button" className={SMALL_BUTTON} disabled={disabled} onClick={fill}>
                Fill the form
              </button>
            </div>
          </>
        )}
      </div>
    </details>
  );
}
