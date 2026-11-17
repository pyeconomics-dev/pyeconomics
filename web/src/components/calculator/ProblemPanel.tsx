// web/src/components/calculator/ProblemPanel.tsx
// A run that failed (Phase 5 Step 6; ADR-0012 decision 4): the problem's title
// and detail from the error table, as text; each field's error when the
// problem names fields; a link to the problem's page; the local-mode command
// where the problem points to local mode (input-too-large, budget-exceeded);
// and, for a rate limit, when to try again. A field's error is written in a
// reader's words, under the field's name, once (Phase 5 Step 18's round 1: an
// error read "price_from_yield: Value error, ..." and came twice). Nothing the
// server sent is rendered as HTML.
import { fieldTitle, problemPage, problemSlug } from "@/lib/calculator";

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

/**
 * A validation message in a reader's words: the library's "Value error, "
 * goes, and the sentence starts with a capital.
 */
export function plainMessage(message: string): string {
  const text = message.replace(/^(?:value|assertion) error,\s*/i, "").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/**
 * Where a field error sits, without the calculation a family's errors name
 * first (as Pydantic's union does): the path to the field, or none for an
 * error about the inputs together.
 */
export function fieldPath(loc: readonly (string | number)[], calculation?: unknown): (string | number)[] {
  return loc.at(0) === calculation ? loc.slice(1) : [...loc];
}

export interface ProblemPanelProps {
  problem: ProblemDocument;
  status: number;
  retryAfter: number | null;
  localSlugs: readonly string[];
  localCommand: string;
  /** The calculation the inputs chose, which a family's errors name first. */
  calculation?: unknown;
}

export default function ProblemPanel({ problem, status, retryAfter, localSlugs, localCommand, calculation }: ProblemPanelProps) {
  const slug = problemSlug(problem.type);
  const title = typeof problem.title === "string" ? problem.title : `The run failed (HTTP ${String(status)})`;
  const detail = typeof problem.detail === "string" ? problem.detail : null;
  const fields = fieldProblems(problem);
  return (
    <div className="flex flex-col gap-2 rounded-md border border-destructive p-4" data-problem={slug ?? "unknown"}>
      <h4 className="font-semibold">{title}</h4>
      {/* The detail repeats the field errors in the API's own words: shown only when there are none. */}
      {detail && fields.length === 0 && <p className="whitespace-pre-wrap">{detail}</p>}
      {fields.length > 0 && (
        <ul className="list-disc pl-6 text-sm">
          {fields.map((field, index) => {
            const path = fieldPath(field.loc, calculation);
            const name = path.at(0);
            const rest = path.slice(1);
            return (
              <li key={`${field.loc.join(".")}-${String(index)}`} data-field-problem={path.join(".")}>
                {typeof name === "string" && (
                  <>
                    <strong className="font-medium">{fieldTitle(name)}</strong>
                    {rest.length > 0 ? ` (at ${rest.join(".")})` : ""}:{" "}
                  </>
                )}
                {plainMessage(field.msg)}
              </li>
            );
          })}
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
