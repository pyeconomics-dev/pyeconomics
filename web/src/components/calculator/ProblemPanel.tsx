// web/src/components/calculator/ProblemPanel.tsx
// A run that failed (Phase 5 Step 6; ADR-0012 decision 4): the problem's title
// and detail from the error table, as text; each field's error when the
// problem names fields; a link to the problem's page; the local-mode command
// where the problem points to local mode (input-too-large, budget-exceeded);
// and, for a rate limit, when to try again. Nothing the server sent is
// rendered as HTML.
import { problemPage, problemSlug } from "@/lib/calculator";

/** An RFC 9457 problem as the API sends it (surfaces/problems.py Problem.to_dict). */
export interface ProblemDocument {
  type?: unknown;
  title?: unknown;
  status?: unknown;
  detail?: unknown;
  errors?: unknown;
}

/** One field's error inside a problem. */
export interface FieldProblem {
  loc: (string | number)[];
  msg: string;
}

/** The field errors a problem carries, each with where and what. */
export function fieldProblems(problem: ProblemDocument): FieldProblem[] {
  if (!Array.isArray(problem.errors)) return [];
  return problem.errors.flatMap((error: unknown) => {
    if (typeof error !== "object" || error === null) return [];
    const { loc, msg } = error as { loc?: unknown; msg?: unknown };
    if (!Array.isArray(loc) || typeof msg !== "string") return [];
    return [{ loc: loc.filter((part): part is string | number => typeof part === "string" || typeof part === "number"), msg }];
  });
}

export interface ProblemPanelProps {
  problem: ProblemDocument;
  status: number;
  retryAfter: number | null;
  localSlugs: readonly string[];
  localCommand: string;
}

export default function ProblemPanel({ problem, status, retryAfter, localSlugs, localCommand }: ProblemPanelProps) {
  const slug = problemSlug(problem.type);
  const title = typeof problem.title === "string" ? problem.title : `The run failed (HTTP ${String(status)})`;
  const detail = typeof problem.detail === "string" ? problem.detail : null;
  const fields = fieldProblems(problem);
  return (
    <div className="flex flex-col gap-2 rounded-md border border-destructive p-4" data-problem={slug ?? "unknown"}>
      <h4 className="font-semibold">{title}</h4>
      {detail && <p className="whitespace-pre-wrap">{detail}</p>}
      {fields.length > 0 && (
        <ul className="list-disc pl-6 text-sm">
          {fields.map((field, index) => (
            <li key={`${field.loc.join(".")}-${String(index)}`}>
              <code>{field.loc.join(".") || "inputs"}</code>: {field.msg}
            </li>
          ))}
        </ul>
      )}
      {status === 429 && (
        <p>{retryAfter === null ? "Too many runs: try again shortly." : `Too many runs: try again in ${String(retryAfter)} seconds.`}</p>
      )}
      {slug && localSlugs.includes(slug) && (
        <p>
          Run it on your own computer instead: <code>{localCommand}</code>
        </p>
      )}
      {slug && (
        <p className="text-sm">
          <a href={problemPage(slug)}>What this problem means and what to do</a>
        </p>
      )}
    </div>
  );
}
