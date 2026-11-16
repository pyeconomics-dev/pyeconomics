// web/src/components/calculator/SnippetsPanel.tsx
// "The same run from code" (Phase 5 Step 6): the run the form would make,
// written for each other surface (src/lib/snippets.ts). One snippet shows at a
// time, chosen from a row of buttons that is always in view beside the form
// (Step 18's round 1: the snippets sat in a closed disclosure under the
// result), in a plain <pre> with the site's copy button. The MCP snippet says
// which of the server's two tools it calls. They name the public endpoint and
// the form's own inputs only.
import { useState } from "react";

import CopyButton from "@/components/calculator/CopyButton";
import { SNIPPET_KINDS, snippets, type SnippetKind, type SnippetRun } from "@/lib/snippets";

const LABELS: ReadonlyMap<SnippetKind, string> = new Map([
  ["python", "Python"],
  ["cli", "Command line"],
  ["curl", "curl"],
  ["mcp", "MCP"],
]);

const TAB =
  "rounded-md border px-3 py-1.5 text-sm hover:bg-accent aria-pressed:border-primary aria-pressed:bg-primary " +
  "aria-pressed:text-primary-foreground";
const PRE = "max-h-80 overflow-auto rounded-md bg-muted px-4 py-3 text-xs";

export interface SnippetsPanelProps {
  run: SnippetRun;
  /** The model's own MCP tool, beside the generic run_model the snippet calls. */
  mcpTool?: string | null;
}

export default function SnippetsPanel({ run, mcpTool = null }: SnippetsPanelProps) {
  const [kind, setKind] = useState<SnippetKind>("python");
  let texts: ReadonlyMap<SnippetKind, string>;
  try {
    texts = new Map(Object.entries(snippets(run)) as [SnippetKind, string][]);
  } catch {
    return <p className="text-sm">Fix the inputs to see the run as code.</p>;
  }
  const label = LABELS.get(kind) ?? kind;
  const text = texts.get(kind) ?? "";
  return (
    <div className="flex flex-col gap-3" data-snippets="">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Show the run as">
        {SNIPPET_KINDS.map((entry) => (
          <button
            key={entry}
            type="button"
            className={TAB}
            aria-pressed={entry === kind}
            data-snippet-tab={entry}
            onClick={() => setKind(entry)}
          >
            {LABELS.get(entry) ?? entry}
          </button>
        ))}
      </div>
      <div className="flex flex-col gap-2" data-snippet={kind}>
        <pre className={PRE} role="region" aria-label={`${label} snippet`} tabIndex={0}>
          <code>{text}</code>
        </pre>
        {kind === "mcp" && (
          <p className="text-xs text-muted-foreground" data-mcp-note="">
            This calls <code>run_model</code>, the MCP server's tool that runs any model by its id.
            {mcpTool ? (
              <>
                {" "}
                The model also has a tool of its own, <code>{mcpTool}</code>, which takes the inputs alone. Both give
                the same result.
              </>
            ) : null}
          </p>
        )}
        <div>
          <CopyButton text={text} label={`Copy ${label}`} />
        </div>
      </div>
    </div>
  );
}
