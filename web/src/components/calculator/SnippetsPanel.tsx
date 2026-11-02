// web/src/components/calculator/SnippetsPanel.tsx
// "Copy as Python, CLI, curl and MCP" (Phase 5 Step 6): the run the form
// would make, written for each other surface (src/lib/snippets.ts), each in a
// plain <pre> with a copy button. They name the public endpoint and the
// form's own inputs only.
import { useState } from "react";

import { SNIPPET_KINDS, snippets, type SnippetKind, type SnippetRun } from "@/lib/snippets";

const LABELS: ReadonlyMap<SnippetKind, string> = new Map([
  ["python", "Python"],
  ["cli", "Command line"],
  ["curl", "curl"],
  ["mcp", "MCP (run_model)"],
]);

const BUTTON = "rounded-md border px-2 py-1 text-xs hover:bg-accent focus-visible:outline-2";
const PRE = "max-h-80 overflow-auto rounded-md bg-muted px-4 py-3 text-xs";

export default function SnippetsPanel({ run }: { run: SnippetRun }) {
  const [copied, setCopied] = useState<SnippetKind | null>(null);
  let texts: ReadonlyMap<SnippetKind, string>;
  try {
    texts = new Map(Object.entries(snippets(run)) as [SnippetKind, string][]);
  } catch {
    return <p className="text-sm">Fix the inputs to see the snippets.</p>;
  }
  const copy = (kind: SnippetKind) => {
    void navigator.clipboard.writeText(texts.get(kind) ?? "").then(
      () => setCopied(kind),
      () => setCopied(null),
    );
  };
  return (
    <div className="flex flex-col gap-4">
      {SNIPPET_KINDS.map((kind) => {
        const label = LABELS.get(kind) ?? kind;
        return (
          <div key={kind} className="flex flex-col gap-1" data-snippet={kind}>
            <div className="flex items-center justify-between gap-2">
              <h4 className="text-sm font-medium">{label}</h4>
              <button type="button" className={BUTTON} onClick={() => copy(kind)}>
                {copied === kind ? "Copied" : `Copy ${label}`}
              </button>
            </div>
            <pre className={PRE} role="region" aria-label={`${label} snippet`} tabIndex={0}>
              <code>{texts.get(kind)}</code>
            </pre>
          </div>
        );
      })}
    </div>
  );
}
