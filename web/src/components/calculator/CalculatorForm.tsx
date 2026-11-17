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
import CopyButton from "@/components/calculator/CopyButton";
import CopyCommand from "@/components/calculator/CopyCommand";
import FieldError from "@/components/calculator/FieldError";
import FieldsTemplate from "@/components/calculator/FieldsTemplate";
import ListWidget from "@/components/calculator/ListWidget";
import ProblemPanel, {
  fieldPath,
  fieldProblems,
  plainMessage,
  type FieldProblem,
  type ProblemDocument,
} from "@/components/calculator/ProblemPanel";
import ResultPanel from "@/components/calculator/ResultPanel";
import SelectWidget from "@/components/calculator/SelectWidget";
import SnippetsPanel from "@/components/calculator/SnippetsPanel";
import UserDataPanel from "@/components/calculator/UserDataPanel";
import { buttonVariants } from "@/components/ui/button";
import {
  boundFields,
  exampleLabel,
  fieldTitle,
  outputTable,
  plainErrors,
  propertiesFor,
  runInputs,
  tidyErrors,
  uiSchemaFor,
  type CalculatorProps,
} from "@/lib/calculator";
import { adoptStyles } from "@/lib/adopt-styles";
import { profileLabel } from "@/lib/profiles";
import { report } from "@/lib/error-reporting";
import { track } from "@/lib/events";
import { LOCAL_APP } from "@/lib/explorer";
import { applicable } from "@/lib/figure";
import { decode, outputCount, parseResult, type Result } from "@/lib/results";
import { RUN_FORMATS, runModel, type RunAnswer, type RunFormat, type RunOptions } from "@/lib/run-request";
import { serverMode, type ServerMode } from "@/lib/series-request";
import type { LoadedModel } from "@/lib/validators";
import stylesheet from "@/styles/calculator.css?inline";

// The form's styles arrive with its code, as a constructed stylesheet: a
// stylesheet the page links would load before anyone uses a calculator, and
// the policy allows a sheet built through the CSS object model. Rules the page
// already has are left out, so the page's responsive rules keep winning
// (src/lib/adopt-styles.ts).
if (typeof document !== "undefined") adoptStyles(stylesheet);

const WIDGETS = { list: ListWidget, SelectWidget };
const TEMPLATES = { ObjectFieldTemplate: FieldsTemplate, FieldErrorTemplate: FieldError };

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

/**
 * A problem's field errors, placed on the form's own fields. An error about
 * the inputs together ("settlement must be before maturity") is placed on
 * each field its words name, so the fields to change are marked (Step 18's
 * round 1: such an error showed only in a box under the form).
 */
function errorSchemaOf(problems: readonly FieldProblem[], fields: readonly string[], calculation: unknown): ErrorSchema | undefined {
  const found = new Map<string, string[]>();
  const add = (field: string, text: string) => found.set(field, [...(found.get(field) ?? []), text]);
  for (const { loc, msg } of problems) {
    // A family's error names its calculation first, as Pydantic's union does.
    const path = fieldPath(loc, calculation);
    const field = path.at(0);
    const message = plainMessage(msg);
    if (typeof field === "string" && fields.includes(field)) {
      add(field, `${message}${path.length > 1 ? ` (at ${path.slice(1).join(".")})` : ""}`);
    } else if (path.length === 0) {
      const words = ` ${msg.toLowerCase().replace(/[^a-z0-9_]+/g, " ")} `;
      for (const name of fields) {
        if (words.includes(` ${name} `) || words.includes(` ${name.replaceAll("_", " ")} `)) add(name, message);
      }
    }
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

/** Names as a sentence lists them: "A", "A and B", "A, B and C". */
function sentence(names: readonly string[]): string {
  if (names.length < 2) return names.join("");
  return `${names.slice(0, -1).join(", ")} and ${names.at(-1) ?? ""}`;
}

/** The local app's two commands: the install, then the server. */
const [INSTALL_APP = LOCAL_APP, SERVE_APP = ""] = LOCAL_APP.split(" then ");

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

  const regions = useMemo(() => new Map(Object.entries(props.profileRegions ?? {})), [props.profileRegions]);
  const calculation = formData.calculation;
  const fields = propertiesFor(schema, calculation);
  const chosen = props.profiles.find((entry) => entry.profile === profile);
  const bound = source === "data" ? boundFields(schema, chosen, calculation) : [];
  // The local app reads every source; the hosted site only hosted-safe ones.
  const unserved = mode === "local" ? [] : bound.filter((field) => !field.hosted).map((field) => field.field);
  const live = source === "data" && bound.length > 0 && unserved.length === 0;
  // Issue #320: which of a profile's fields of this calculation the hosted
  // site may not serve, known at build time, so "Live data" says so before it
  // is chosen. The local app (mode "local") serves every source.
  const offSite = (name: string) => {
    if (mode === "local") return [];
    const names = new Set(fields);
    return props.liveNotes.find((note) => note.profile === name)?.fields.filter((entry) => names.has(entry.field)) ?? [];
  };
  const nowhereHere = props.profiles.length > 0 && props.profiles.every((entry) => offSite(entry.profile).length > 0);
  const chosenNote = props.liveNotes.find((note) => note.profile === profile);
  const missing = offSite(profile);
  const filled = live ? bound.map((field) => field.field) : [];
  const filledKey = filled.join(",");
  const uiSchema = useMemo(
    () => uiSchemaFor(schema, filledKey ? filledKey.split(",") : [], props.inputOrder),
    [schema, filledKey, props.inputOrder],
  );
  const options: RunOptions = live ? { profile, ...(asOf ? { asOf } : {}) } : {};
  const inputs = runInputs(
    Object.fromEntries(Object.entries(formData).filter(([name]) => fields.includes(name))),
    filled,
  );

  // The result comes into view with its heading focused, so a visitor who
  // pressed Run at the foot of a long form sees it (round 0: it stayed below
  // the fold). At once, not as a glide: a jump link's smooth scroll over a
  // dozen screens left the form in view for a second (Step 18's round 1).
  useEffect(() => {
    if (!outcome) return;
    resultHeading.current?.scrollIntoView({ block: "start", behavior: "instant" });
    resultHeading.current?.focus({ preventScroll: true });
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
        // The same count the result's own summary gives (round 3: this line said 6, the summary 5).
        const outputs = outputCount(result);
        setAnnouncement(`Done. The result has ${String(outputs)} output${outputs === 1 ? "" : "s"} and ${String(warnings)} warning${warnings === 1 ? "" : "s"}.`);
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
                {exampleLabel(entry)}
              </option>
            ))}
          </select>
          {examples.at(example)?.note && (
            <span className="text-muted-foreground" data-example-note="">
              {examples.at(example)?.note}
            </span>
          )}
        </label>
      )}

      {props.profiles.length > 0 && (
        <fieldset className="flex flex-col gap-2 rounded-md border p-4">
          <legend className="px-1 font-medium">Where the data comes from</legend>
          <label className="flex items-center gap-2 text-sm">
            <input type="radio" name={`${props.modelId}-source`} value="values" checked={source === "values"} onChange={() => setSource("values")} />
            My own values: every input from the form
          </label>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="radio"
              className="mt-1"
              name={`${props.modelId}-source`}
              value="data"
              checked={source === "data"}
              onChange={() => setSource("data")}
            />
            {nowhereHere ? (
              <span>
                Live data: on your own computer only
                <span className="block text-muted-foreground">
                  This website may not serve this model's data. Choose it to see how to run this page on your computer.
                </span>
              </span>
            ) : (
              <span>Live data: read the model's data from its sources</span>
            )}
          </label>
          {source === "data" && (
            <div className="flex flex-col gap-2 pl-6 text-sm">
              <div className="flex flex-wrap gap-4">
                <label className="flex flex-col gap-1">
                  <span>Profile</span>
                  <select className={CONTROL} value={profile} onChange={(event) => setProfile(event.target.value)}>
                    {props.profiles.map((entry) => (
                      <option key={entry.profile} value={entry.profile}>
                        {profileLabel(entry.profile, regions.get(entry.profile) ?? null)}
                        {offSite(entry.profile).length > 0 ? ": your own computer only" : ""}
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
                <div data-live="unserved" className="flex flex-col gap-2 rounded-md border border-dashed p-3">
                  <p>
                    <strong>This website may not serve these data.</strong>{" "}
                    {chosenNote && chosenNote.sources.length > 0
                      ? `The terms of ${sentence(chosenNote.sources)} let pyeconomics read them on your own computer, but not serve them from this site. `
                      : "Their sources' terms let pyeconomics read them on your own computer, but not serve them from this site. "}
                    The data:{" "}
                    {missing.length > 0
                      ? missing.map((entry, index) => (
                          <span key={entry.field}>
                            {index > 0 && ", "}
                            {entry.label} (<code>{entry.field}</code>)
                          </span>
                        ))
                      : fieldList(unserved)}
                    .
                  </p>
                  <p>To run this page on your computer with live data, install the local app and start it:</p>
                  <CopyCommand command={INSTALL_APP} />
                  {SERVE_APP && <CopyCommand command={SERVE_APP} />}
                  <p>Or run the model from the command line, once pyeconomics is installed:</p>
                  <CopyCommand command={`pyeconomics models run ${props.modelId} --profile ${profile}`} />
                  <p>
                    On this site, choose "My own values" and enter the numbers yourself, or bring them as a file with "Use
                    my own data".
                  </p>
                </div>
              ) : mode === "local" ? (
                <p data-live="local">
                  Filled from data on this computer: {fieldList(filled)}, read from every source your installation
                  reaches, with your own keys where a source needs one. The result lists each source's attribution,
                  notices and terms. The form's other inputs are sent with the run.
                </p>
              ) : (
                <p data-live="hosted">
                  Read from data, {asOf ? `as it stood on ${asOf}` : "at its latest values"}:{" "}
                  {sentence(filled.map((field) => fieldTitle(field)))}. The result lists each series with its source
                  and the date of its last observation. The form's other inputs are sent with the run.
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
        templates={TEMPLATES}
        extraErrors={extraErrors}
        showErrorList={false}
        noHtml5Validate
        focusOnFirstError
        disabled={running}
        idPrefix={`calculator-${props.modelId.replace(".", "-")}`}
        transformErrors={(errors) =>
          plainErrors(
            tidyErrors(errors).filter(
              (error) => !filled.some((field) => error.property === `.${field}` || error.property?.startsWith(`.${field}.`)),
            ),
            (name) => {
              const field = name.split(".")[0] ?? name;
              const properties = new Map(Object.entries((schema as { properties?: Record<string, { title?: unknown }> }).properties ?? {}));
              const title = properties.get(field)?.title;
              return typeof title === "string" ? title : fieldTitle(field);
            },
          )
        }
        onChange={(event) => setFormData((event.formData ?? {}) as Record<string, unknown>)}
        onError={invalid}
        onSubmit={() => void run()}
      >
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button type="submit" className={buttonVariants()} disabled={running}>
            {running ? "Running…" : "Run"}
          </button>
          <span className="text-xs text-muted-foreground">Inputs marked * are required.</span>
          {/* The run as code is beneath the result, which can be long (Step 18's round 2). */}
          {props.snippets !== false && (
            <a href="#calculator-code" className="text-sm sm:ml-auto" data-code-link="">
              These inputs as code
            </a>
          )}
        </div>
      </Form>

      <p role="status" aria-live="polite" className="text-sm">
        {announcement}
      </p>

      {outcome && (
        <section className={`${SECTION} motion-rise`} aria-labelledby="calculator-result" data-outcome={outcome.kind}>
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
                  <CopyButton text={() => decode(outcome.answer.bytes)} label="Copy JSON" />
                </div>
                <p className="text-xs text-muted-foreground">
                  Every file carries the result's attributions, notices and manifest: the model's version, the hashes of
                  its inputs and result, and where each value came from. The bundle adds a script that runs it again.
                  Formats: {RUN_FORMATS.join(", ")}.{" "}
                  <a href="https://docs.pyeconomics.dev/en/main/results.html">What a result holds</a>
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
              calculation={calculation}
            />
          )}
          {outcome.kind === "error" && <p>The run could not reach the server: {outcome.message}</p>}
        </section>
      )}

      {props.snippets !== false && (
        <section className={SECTION} aria-labelledby="calculator-code" data-code="">
          <h3 id="calculator-code" className={HEADING}>
            The same run from code
          </h3>
          <p className="text-sm text-muted-foreground">
            These inputs as Python, a command, a request or an MCP call: each gives the same result, byte for byte.
          </p>
          <SnippetsPanel run={{ modelId: props.modelId, inputs, options }} mcpTool={props.mcpTool} install={props.install} />
        </section>
      )}
    </>
  );
}
