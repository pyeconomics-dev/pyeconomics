// web/src/components/calculator/CalculatorForm.tsx
// A model's calculator once its model is loaded (Phase 5 Step 6; ADR-0013
// decisions 8, 9 and 11): the island (Calculator.tsx) imports this module only
// when it first renders in view, with its own styles (src/styles/
// calculator.css, adopted below), so no page carries the form's code or styles
// until it is used. It renders the model's input schema with RJSF and its
// shadcn/ui theme, prefilled with the first example, and posts the inputs'
// JSON to the run route on the site's own origin (src/lib/run-request.ts). The answer's bytes are kept as
// received: the outputs table, the chart and the sources panel are drawn
// beside them, "copy JSON" and the JSON download hand them over unchanged, and
// every other download is the same POST with ?format=. A bound model offers
// live data where hosted mode can serve every bound field, and says which
// fields it cannot serve elsewhere; served by the local app (GET /version's
// mode is `local`, Phase 5 Step 10), it offers every profile, library-only
// sources included, read with the user's own keys. "Use my own data"
// (UserDataPanel.tsx, Phase 5 Step 9) fills the array inputs from a CSV or XLSX file read in a
// Web Worker; only the values it writes into the form travel, in the run's
// body. Snippets for the other surfaces follow the form. No input is kept in
// storage, the URL or analytics; text from the server is rendered as text.
import Form from "@rjsf/shadcn";
import type { ErrorSchema, RJSFValidationError } from "@rjsf/utils";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import ChartPanel from "@/components/calculator/ChartPanel";
import ListWidget from "@/components/calculator/ListWidget";
import ProblemPanel, { fieldProblems, type FieldProblem, type ProblemDocument } from "@/components/calculator/ProblemPanel";
import ResultPanel from "@/components/calculator/ResultPanel";
import SelectWidget from "@/components/calculator/SelectWidget";
import SnippetsPanel from "@/components/calculator/SnippetsPanel";
import UserDataPanel from "@/components/calculator/UserDataPanel";
import { buttonVariants } from "@/components/ui/button";
import {
  boundFields,
  outputTable,
  propertiesFor,
  runInputs,
  tidyErrors,
  uiSchemaFor,
  type CalculatorProps,
} from "@/lib/calculator";
import { report } from "@/lib/error-reporting";
import { track } from "@/lib/events";
import { applicable } from "@/lib/figure";
import { decode, parseResult, type Result } from "@/lib/results";
import { RUN_FORMATS, runModel, type RunAnswer, type RunFormat, type RunOptions } from "@/lib/run-request";
import { serverMode, type ServerMode } from "@/lib/series-request";
import type { LoadedModel } from "@/lib/validators";
import stylesheet from "@/styles/calculator.css?inline";

// The form's styles arrive with its code, as a constructed stylesheet: a
// stylesheet the page links would load before anyone uses a calculator, and
// the policy allows a sheet built through the CSS object model.
if (typeof document !== "undefined") {
  const sheet = new CSSStyleSheet();
  sheet.replaceSync(stylesheet);
  document.adoptedStyleSheets = [...document.adoptedStyleSheets, sheet];
}

const WIDGETS = { list: ListWidget, SelectWidget };

/** The downloads beside a result, each the same run with ?format=. */
const DOWNLOADS: readonly { format: Exclude<RunFormat, "json">; label: string; extension: string }[] = [
  { format: "csv", label: "CSV", extension: "csv" },
  { format: "xlsx", label: "XLSX", extension: "xlsx" },
  { format: "parquet", label: "Parquet", extension: "parquet" },
  { format: "arrow", label: "Arrow", extension: "arrow" },
  { format: "bundle", label: "Reproducibility bundle", extension: "zip" },
];

const SECTION = "flex flex-col gap-3";
const HEADING = "text-xl font-semibold";
const SMALL_BUTTON = buttonVariants({ variant: "outline", size: "sm" });
const CONTROL =
  "rounded-md border border-input bg-transparent px-3 py-1.5 text-sm shadow-xs focus-visible:border-ring " +
  "focus-visible:ring-[3px] focus-visible:ring-ring/50 outline-none";

type Outcome =
  | { kind: "result"; answer: RunAnswer; result: Result }
  | { kind: "problem"; answer: RunAnswer; problem: ProblemDocument }
  | { kind: "error"; message: string };

interface Sent {
  inputs: Record<string, unknown>;
  options: RunOptions;
}

/** Hand bytes to the browser as a file to save. */
function save(bytes: Uint8Array, filename: string, type: string): void {
  const url = URL.createObjectURL(new Blob([bytes.slice()], { type: type || "application/octet-stream" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

/** A problem's field errors, placed on the form's own fields. */
function errorSchemaOf(problems: readonly FieldProblem[], fields: readonly string[], calculation: unknown): ErrorSchema | undefined {
  const found = new Map<string, string[]>();
  for (const { loc, msg } of problems) {
    // A family's error names its calculation first, as Pydantic's union does.
    const path = loc.at(0) === calculation ? loc.slice(1) : loc;
    const field = path.at(0);
    if (typeof field !== "string" || !fields.includes(field)) continue;
    const where = path.length > 1 ? ` (at ${path.slice(1).join(".")})` : "";
    found.set(field, [...(found.get(field) ?? []), `${msg}${where}`]);
  }
  if (found.size === 0) return undefined;
  return Object.fromEntries([...found].map(([field, errors]) => [field, { __errors: errors }])) as ErrorSchema;
}

function problemOf(answer: RunAnswer): ProblemDocument {
  try {
    const parsed: unknown = JSON.parse(decode(answer.bytes));
    return typeof parsed === "object" && parsed !== null ? (parsed as ProblemDocument) : {};
  } catch {
    return {};
  }
}

function fieldList(names: readonly string[]): ReactNode {
  return names.map((name, index) => (
    <span key={name}>
      {index > 0 && ", "}
      <code>{name}</code>
    </span>
  ));
}

export default function CalculatorForm({ model, ...props }: CalculatorProps & { model: LoadedModel }) {
  const { schema, examples, validator } = model;
  const [example, setExample] = useState(0);
  const [formData, setFormData] = useState<Record<string, unknown>>(() => structuredClone(examples[0]?.inputs ?? {}));
  const [source, setSource] = useState<"values" | "data">("values");
  const [profile, setProfile] = useState(props.profiles[0]?.profile ?? "");
  const [asOf, setAsOf] = useState("");
  const [running, setRunning] = useState(false);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [sent, setSent] = useState<Sent | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [extraErrors, setExtraErrors] = useState<ErrorSchema | undefined>(undefined);
  const [mode, setMode] = useState<ServerMode>("hosted");
  const resultHeading = useRef<HTMLHeadingElement>(null);

  const calculation = formData.calculation;
  const fields = propertiesFor(schema, calculation);
  const chosen = props.profiles.find((entry) => entry.profile === profile);
  const bound = source === "data" ? boundFields(schema, chosen, calculation) : [];
  // The local app reads every source; the hosted site only hosted-safe ones.
  const unserved = mode === "local" ? [] : bound.filter((field) => !field.hosted).map((field) => field.field);
  const live = source === "data" && bound.length > 0 && unserved.length === 0;
  const filled = live ? bound.map((field) => field.field) : [];
  const filledKey = filled.join(",");
  const uiSchema = useMemo(() => uiSchemaFor(schema, filledKey ? filledKey.split(",") : []), [schema, filledKey]);
  const options: RunOptions = live ? { profile, ...(asOf ? { asOf } : {}) } : {};
  const inputs = runInputs(
    Object.fromEntries(Object.entries(formData).filter(([name]) => fields.includes(name))),
    filled,
  );

  useEffect(() => {
    if (outcome) resultHeading.current?.focus();
  }, [outcome]);

  // The server's mode is asked only once live data is chosen, so a page view
  // sends no request of its own.
  useEffect(() => {
    if (source !== "data") return;
    let current = true;
    void serverMode().then((found) => {
      if (current && found === "local") setMode(found);
    });
    return () => {
      current = false;
    };
  }, [source]);

  const choose = (index: number) => {
    setExample(index);
    setFormData(structuredClone(examples.at(index)?.inputs ?? {}));
    setExtraErrors(undefined);
  };

  const run = async () => {
    const request: Sent = { inputs, options };
    setRunning(true);
    setExtraErrors(undefined);
    setAnnouncement("Running the model…");
    try {
      const answer = await runModel(props.modelId, request.inputs, request.options);
      setSent(request);
      if (answer.ok) {
        let result: ReturnType<typeof parseResult>;
        try {
          result = parseResult(answer.bytes);
        } catch (error) {
          // The server answered 200 with bytes that are not a result: a fault
          // to report, never the visitor's.
          void report(error, "calculator");
          setOutcome({ kind: "error", message: "The server's answer could not be read." });
          setAnnouncement("The server's answer could not be read.");
          return;
        }
        setOutcome({ kind: "result", answer, result });
        track("calculator_run", { model: props.modelId });
        const warnings = result.warnings.length;
        setAnnouncement(`Done. The result has ${String(Object.keys(result.outputs).length)} outputs and ${String(warnings)} warning${warnings === 1 ? "" : "s"}.`);
      } else {
        const problem = problemOf(answer);
        setOutcome({ kind: "problem", answer, problem });
        setExtraErrors(errorSchemaOf(fieldProblems(problem), fields, calculation));
        const title = typeof problem.title === "string" ? problem.title : `HTTP ${String(answer.status)}`;
        setAnnouncement(`The run failed: ${title}.`);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setOutcome({ kind: "error", message });
      setAnnouncement("The run could not reach the server.");
    } finally {
      setRunning(false);
    }
  };

  const download = async (format: Exclude<RunFormat, "json">, extension: string) => {
    if (!sent) return;
    setAnnouncement(`Preparing the ${format} download…`);
    try {
      const answer = await runModel(props.modelId, sent.inputs, { ...sent.options, format });
      if (!answer.ok) {
        setOutcome({ kind: "problem", answer, problem: problemOf(answer) });
        setAnnouncement("The download failed.");
        return;
      }
      save(answer.bytes, answer.filename ?? `${props.modelId}.${extension}`, answer.contentType);
      track("download", { model: props.modelId, format });
      setAnnouncement(`The ${format} download is ready.`);
    } catch {
      setAnnouncement("The download could not reach the server.");
    }
  };

  const invalid = (errors: RJSFValidationError[]) => {
    const count = errors.length;
    setAnnouncement(`${String(count)} input${count === 1 ? " needs" : "s need"} fixing before the run: ${errors.map((error) => error.stack).join("; ")}`);
  };

  return (
    <>
      {examples.length > 1 && (
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">Start from an example</span>
          <select className={CONTROL} value={example} onChange={(event) => choose(Number(event.target.value))}>
            {examples.map((entry, index) => (
              <option key={entry.name} value={index}>
                {entry.name}
                {entry.note ? `: ${entry.note}` : ""}
              </option>
            ))}
          </select>
        </label>
      )}

      {props.profiles.length > 0 && (
        <fieldset className="flex flex-col gap-2 rounded-md border p-4">
          <legend className="px-1 font-medium">Where the data comes from</legend>
          <label className="flex items-center gap-2 text-sm">
            <input type="radio" name={`${props.modelId}-source`} value="values" checked={source === "values"} onChange={() => setSource("values")} />
            My own values: every input from the form
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="radio" name={`${props.modelId}-source`} value="data" checked={source === "data"} onChange={() => setSource("data")} />
            Live data: bind the model's data first, then the form's other values
          </label>
          {source === "data" && (
            <div className="flex flex-col gap-2 pl-6 text-sm">
              <div className="flex flex-wrap gap-4">
                <label className="flex flex-col gap-1">
                  <span>Profile</span>
                  <select className={CONTROL} value={profile} onChange={(event) => setProfile(event.target.value)}>
                    {props.profiles.map((entry) => (
                      <option key={entry.profile} value={entry.profile}>
                        {entry.profile}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-1">
                  <span>As of (optional)</span>
                  <input className={CONTROL} type="date" value={asOf} onChange={(event) => setAsOf(event.target.value)} />
                </label>
              </div>
              {bound.length === 0 ? (
                <p data-live="none">This profile binds none of this calculation's inputs: every input comes from the form.</p>
              ) : unserved.length > 0 ? (
                <p data-live="unserved">
                  The hosted site may not serve the data for {fieldList(unserved)}: their sources are not hosted-safe. Enter
                  your own values with "My own values", or run pyeconomics on your own computer, where every source is
                  available: <code>{`pyeconomics models run ${props.modelId} --profile ${profile}`}</code>
                </p>
              ) : mode === "local" ? (
                <p data-live="local">
                  Filled from data on this computer: {fieldList(filled)}, read from every source your installation
                  reaches, with your own keys where a source needs one. The result lists each source's attribution,
                  notices and terms. The form's other inputs are sent with the run.
                </p>
              ) : (
                <p data-live="hosted">
                  Filled from data: {fieldList(filled)}. The form's other inputs are sent with the run.
                </p>
              )}
            </div>
          )}
        </fieldset>
      )}

      {source === "values" && (
        <UserDataPanel
          modelId={props.modelId}
          schema={schema}
          calculation={calculation}
          example={examples.at(example)?.inputs ?? {}}
          disabled={running}
          onFill={(values) => {
            setFormData((current) => ({ ...current, ...values }));
            setExtraErrors(undefined);
          }}
        />
      )}

      <Form
        schema={schema}
        uiSchema={uiSchema}
        validator={validator}
        formData={formData}
        widgets={WIDGETS}
        extraErrors={extraErrors}
        showErrorList="top"
        noHtml5Validate
        focusOnFirstError
        disabled={running}
        idPrefix={`calculator-${props.modelId.replace(".", "-")}`}
        transformErrors={(errors) =>
          tidyErrors(errors).filter(
            (error) => !filled.some((field) => error.property === `.${field}` || error.property?.startsWith(`.${field}.`)),
          )
        }
        onChange={(event) => setFormData((event.formData ?? {}) as Record<string, unknown>)}
        onError={invalid}
        onSubmit={() => void run()}
      >
        <div className="mt-4 flex items-center gap-3">
          <button type="submit" className={buttonVariants()} disabled={running}>
            {running ? "Running…" : "Run"}
          </button>
        </div>
      </Form>

      <p role="status" aria-live="polite" className="text-sm">
        {announcement}
      </p>

      {outcome && (
        <section className={SECTION} aria-labelledby="calculator-result">
          <h3 id="calculator-result" ref={resultHeading} tabIndex={-1} className={HEADING}>
            {outcome.kind === "result" ? "Result" : "The run failed"}
          </h3>
          {outcome.kind === "result" && (
            <>
              <ResultPanel result={outcome.result} table={outputTable(props.outputs, outcome.result.inputs.calculation)} sourceNames={props.sourceNames} />
              <ChartPanel charts={applicable(props.charts, outcome.result)} document={outcome.result} />
              <div className="flex flex-col gap-2">
                <h4 className="font-medium">Download</h4>
                <div className="flex flex-wrap gap-2">
                  <button type="button" className={SMALL_BUTTON} onClick={() => {
                      save(outcome.answer.bytes, `${props.modelId}.json`, "application/json");
                      track("download", { model: props.modelId, format: "json" });
                    }}>
                    JSON
                  </button>
                  {DOWNLOADS.map((entry) => (
                    <button key={entry.format} type="button" className={SMALL_BUTTON} onClick={() => void download(entry.format, entry.extension)}>
                      {entry.label}
                    </button>
                  ))}
                  <button
                    type="button"
                    className={SMALL_BUTTON}
                    onClick={() => void navigator.clipboard.writeText(decode(outcome.answer.bytes)).then(() => setAnnouncement("The result's JSON is copied."))}
                  >
                    Copy JSON
                  </button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Every file carries the result's attributions, notices and manifest. Formats: {RUN_FORMATS.join(", ")}.
                </p>
              </div>
            </>
          )}
          {outcome.kind === "problem" && (
            <ProblemPanel
              problem={outcome.problem}
              status={outcome.answer.status}
              retryAfter={outcome.answer.retryAfter}
              localSlugs={props.localSlugs}
              localCommand={props.localCommand}
            />
          )}
          {outcome.kind === "error" && <p>The run could not reach the server: {outcome.message}</p>}
        </section>
      )}

      <details className="rounded-md border p-4">
        <summary className="cursor-pointer font-medium">Copy as Python, command line, curl or MCP</summary>
        <div className="mt-4">
          <SnippetsPanel run={{ modelId: props.modelId, inputs, options }} />
        </div>
      </details>
    </>
  );
}
