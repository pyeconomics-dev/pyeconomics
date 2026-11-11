// web/src/components/calculator/Calculator.tsx
// A model's calculator, the site's first island (Phase 5 Step 6; ADR-0013
// decisions 8, 9 and 11), hydrated when it scrolls into view. This shell is
// all a page ships: when it first renders it loads, side by side, its model's
// module (the validators scripts/web/compile_validators.mjs precompiled, the
// input schema and the examples; src/lib/validators.ts) and the form
// (CalculatorForm.tsx), whose code and stylesheet no page loads before. The
// form renders the schema with RJSF, posts the inputs' JSON to the run route
// on the site's own origin, and shows the result's bytes as received with its
// table, chart, sources, downloads and snippets. It also holds Plotly's
// no-inline-styles marker, which must be in the page before Plotly loads. An
// error that stops it loading or rendering goes to the error tracker in a
// production build (src/lib/error-reporting.ts; Phase 5 Step 14).
import { useEffect, useState, type ComponentType } from "react";

import IslandBoundary from "@/components/IslandBoundary";
import type { CalculatorProps } from "@/lib/calculator";
import { report } from "@/lib/error-reporting";
import { STYLE_MARKER } from "@/lib/plotly";
import { loadModel, type LoadedModel } from "@/lib/validators";

type Form = ComponentType<CalculatorProps & { model: LoadedModel }>;

export default function Calculator(props: CalculatorProps) {
  const [ready, setReady] = useState<{ model: LoadedModel; Form: Form } | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    Promise.all([loadModel(props.modelId), import("@/components/calculator/CalculatorForm")]).then(
      ([model, module]) => {
        if (current) setReady({ model, Form: module.default });
      },
      (error: unknown) => {
        void report(error, "calculator");
        if (current) setFailure(error instanceof Error ? error.message : String(error));
      },
    );
    return () => {
      current = false;
    };
  }, [props.modelId]);

  return (
    <div className="flex flex-col gap-6" data-calculator={props.modelId} data-ready={ready ? "true" : "false"}>
      {/* Plotly reads this before it would inject a <style> element (src/lib/plotly.ts). */}
      <div id={STYLE_MARKER.id} className={STYLE_MARKER.className} hidden />
      {ready ? (
        <IslandBoundary island="calculator">
          <ready.Form {...props} model={ready.model} />
        </IslandBoundary>
      ) : (
        <p className="text-sm">{failure ? `The calculator could not load: ${failure}` : "Loading the calculator…"}</p>
      )}
    </div>
  );
}
