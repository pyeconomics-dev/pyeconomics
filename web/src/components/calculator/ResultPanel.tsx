// web/src/components/calculator/ResultPanel.tsx
// A run's result (Phase 5 Step 6): the outputs as a table driven by the output
// schema (each with its unit; a long array a page at a time), the warnings,
// and the sources panel from the manifest's data_sources (attribution,
// notices, licence class, terms page, as-of and retrieval time, and what
// revised data means). Every value reaches the page as React text, never as
// HTML.
import { useState } from "react";

import type { VariableTable } from "@/lib/models";
import {
  DATA_WARNINGS,
  PAGE_SIZE,
  asOfText,
  formatValue,
  pageCount,
  pageOf,
  sourceRecords,
  type Result,
  type SourceRecord,
} from "@/lib/results";

const CELL = "py-2 pr-4 align-top";
const BUTTON =
  "rounded-md border px-2 py-1 text-xs hover:bg-accent disabled:opacity-50 focus-visible:outline-2";

function ArrayValue({ name, values }: { name: string; values: readonly unknown[] }) {
  const [page, setPage] = useState(0);
  if (values.length === 0) return <span>(empty)</span>;
  const pages = pageCount(values.length);
  const { start, items } = pageOf(values, page);
  return (
    <div className="flex flex-col gap-1">
      <ol start={start + 1} className="list-decimal pl-8 font-mono text-xs">
        {items.map((item, index) => (
          <li key={start + index}>{Array.isArray(item) ? item.map(formatValue).join(", ") : formatValue(item)}</li>
        ))}
      </ol>
      {pages > 1 && (
        <div className="flex items-center gap-2 text-xs">
          <button type="button" className={BUTTON} disabled={page === 0} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <span>
            {name}: values {start + 1}–{start + items.length} of {values.length} ({PAGE_SIZE} a page)
          </span>
          <button type="button" className={BUTTON} disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>
            Next
          </button>
        </div>
      )}
    </div>
  );
}

function OutputsTable({ table, outputs }: { table: VariableTable | undefined; outputs: Record<string, unknown> }) {
  const known = new Set(table?.rows.map((row) => row.name) ?? []);
  const rows = [
    ...(table?.rows ?? []).filter((row) => row.name in outputs),
    ...Object.keys(outputs)
      .filter((name) => !known.has(name))
      .map((name) => ({ name, unit: "", bounds: "", description: "" })),
  ].filter((row) => row.name !== "calculation");
  return (
    <div className="overflow-x-auto" role="region" aria-label="Outputs of this run" tabIndex={0}>
      <table className="w-full border-collapse text-left text-sm">
        <caption className="mb-2 text-left font-medium">Outputs of this run</caption>
        <thead>
          <tr className="border-b">
            <th scope="col" className={CELL}>
              Output
            </th>
            <th scope="col" className={CELL}>
              Value
            </th>
            <th scope="col" className={CELL}>
              Unit
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const value = outputs[row.name];
            return (
              <tr key={row.name} className="border-b">
                <th scope="row" className={`${CELL} font-normal`}>
                  <code>{row.name}</code>
                  {row.description && <span className="block text-muted-foreground">{row.description}</span>}
                </th>
                <td className={`${CELL} font-mono`}>
                  {Array.isArray(value) ? <ArrayValue name={row.name} values={value} /> : formatValue(value)}
                </td>
                <td className={CELL}>{row.unit}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Source({ record, names }: { record: SourceRecord; names: Readonly<Record<string, string>> }) {
  return (
    <li className="flex flex-col gap-1 rounded-md border p-3">
      <p>
        <strong>{names[record.provider] ?? record.provider}</strong>, series <code>{record.series_id}</code>
        {record.field && (
          <>
            {" "}
            for <code>{record.field}</code>
          </>
        )}
      </p>
      <p>{record.attribution}</p>
      {record.notice && <p className="text-muted-foreground">{record.notice}</p>}
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
        <dt className="text-muted-foreground">Licence class</dt>
        <dd>{record.licence}</dd>
        <dt className="text-muted-foreground">As of</dt>
        <dd>{asOfText(record)}</dd>
        {(record.observation_start ?? record.observation_end) && (
          <>
            <dt className="text-muted-foreground">Observations</dt>
            <dd>
              {record.observation_start ?? "…"} to {record.observation_end ?? "…"}
            </dd>
          </>
        )}
        {record.retrieved_at && (
          <>
            <dt className="text-muted-foreground">Retrieved</dt>
            <dd>{record.retrieved_at}</dd>
          </>
        )}
        {record.transforms && record.transforms.length > 0 && (
          <>
            <dt className="text-muted-foreground">Transforms</dt>
            <dd>{record.transforms.join(", ")}</dd>
          </>
        )}
        {record.terms_url?.startsWith("https://") && (
          <>
            <dt className="text-muted-foreground">Terms</dt>
            <dd>
              <a href={record.terms_url} rel="noopener noreferrer">
                The source's terms
              </a>
            </dd>
          </>
        )}
      </dl>
      {record.warnings?.map((code) => (
        <p key={code} className="text-xs">
          <code>{code}</code>: {DATA_WARNINGS.get(code) ?? "a note about this series."}
        </p>
      ))}
    </li>
  );
}

export interface ResultPanelProps {
  result: Result;
  table: VariableTable | undefined;
  sourceNames: Readonly<Record<string, string>>;
}

export default function ResultPanel({ result, table, sourceNames }: ResultPanelProps) {
  const records = sourceRecords(result);
  return (
    <div className="flex flex-col gap-4">
      <OutputsTable table={table} outputs={result.outputs} />
      <div>
        <h4 className="font-medium">Warnings</h4>
        {result.warnings.length > 0 ? (
          <ul className="list-disc pl-6 text-sm">
            {result.warnings.map((warning, index) => (
              <li key={`${warning.code}-${String(index)}`}>
                <code>{warning.code}</code>: {warning.message}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm">None.</p>
        )}
      </div>
      {records.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="font-medium">Sources</h4>
          <ul className="flex flex-col gap-2 text-sm">
            {records.map((record, index) => (
              <Source key={`${record.provider}-${record.series_id}-${String(index)}`} record={record} names={sourceNames} />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
