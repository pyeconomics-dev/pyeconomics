// web/src/components/explorer/ConceptSearch.tsx
// The /data/ search (Phase 5 Step 9; ADR-0013 decision 11): words matched
// against each concept's title, id, unit, frequency and topic, a frequency
// and a topic filter, and "only what this site serves" (the concepts the
// hosted snapshot holds, from concepts.json). The build renders the whole
// list, so a visitor without JavaScript sees every concept; once hydrated,
// the island filters it as the visitor types (src/lib/explorer.ts
// searchConcepts). Served by the local app (GET /version's mode is `local`,
// Phase 5 Step 10), every concept without parameters is charted, so the
// filter goes and each concept says so. The search keeps nothing: no
// storage, no URL.
import { useEffect, useState } from "react";

import { facetValues, searchConcepts, type ConceptListing, type ConceptQuery } from "@/lib/explorer";
import { serverMode, type ServerMode } from "@/lib/series-request";

const CONTROL =
  "h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs outline-none " +
  "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50";

export interface ConceptSearchProps {
  concepts: ConceptListing[];
}

function words(frequency: string): string {
  return frequency.replaceAll("_", " ");
}

/** Where a concept is read, as the list says it. */
function readWhere(concept: ConceptListing, mode: ServerMode): string {
  if (mode === "local") return concept.parameters ? "Read it with the Python API" : "Charted on this site";
  return concept.snapshot ? "Charted on this site" : "Read it locally";
}

export default function ConceptSearch({ concepts }: ConceptSearchProps) {
  const [query, setQuery] = useState<ConceptQuery>({ text: "", frequency: "", topic: "", served: false });
  const [ready, setReady] = useState(false);
  const [mode, setMode] = useState<ServerMode>("hosted");
  useEffect(() => {
    setReady(true);
    let current = true;
    void serverMode().then((found) => {
      if (!current || found !== "local") return;
      setMode(found);
      setQuery((query) => ({ ...query, served: false }));
    });
    return () => {
      current = false;
    };
  }, []);

  const shown = searchConcepts(concepts, query);
  const frequencies = facetValues(concepts, "frequency");
  const topics = facetValues(concepts, "topic");
  const set = (change: Partial<ConceptQuery>) => setQuery((current) => ({ ...current, ...change }));

  return (
    <div className="flex flex-col gap-6" data-concept-search="" data-ready={ready ? "true" : "false"} data-mode={mode}>
      <form
        role="search"
        aria-label="Search the data catalog"
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        onSubmit={(event) => event.preventDefault()}
      >
        <div className="flex flex-col gap-1 sm:col-span-2">
          <label htmlFor="concept-search" className="text-sm font-medium">
            Words
          </label>
          <input
            id="concept-search"
            type="search"
            className={CONTROL}
            value={query.text}
            placeholder="unemployment, treasury 10-year, core inflation"
            onChange={(event) => set({ text: event.target.value })}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="concept-frequency" className="text-sm font-medium">
            Frequency
          </label>
          <select id="concept-frequency" className={CONTROL} value={query.frequency} onChange={(event) => set({ frequency: event.target.value })}>
            <option value="">Any</option>
            {frequencies.map((value) => (
              <option key={value} value={value}>
                {words(value)}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="concept-topic" className="text-sm font-medium">
            Topic
          </label>
          <select id="concept-topic" className={CONTROL} value={query.topic} onChange={(event) => set({ topic: event.target.value })}>
            <option value="">Any</option>
            {topics.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
        {mode === "hosted" && (
          <label className="flex items-center gap-2 text-sm sm:col-span-2">
            <input type="checkbox" checked={query.served} onChange={(event) => set({ served: event.target.checked })} />
            Only the series this site charts
          </label>
        )}
      </form>
      <p role="status" aria-live="polite" className="text-sm">
        {shown.length === concepts.length
          ? `${String(concepts.length)} concepts.`
          : `${String(shown.length)} of ${String(concepts.length)} concepts match.`}
      </p>
      <ul className="grid gap-3 sm:grid-cols-2" data-concept-list="">
        {shown.map((concept) => (
          <li key={concept.id} className="flex flex-col gap-1 rounded-md border px-4 py-3" data-concept={concept.id}>
            <a href={concept.path} className="font-medium">
              {concept.title}
            </a>
            <code className="text-xs">{concept.id}</code>
            <span className="text-sm text-muted-foreground">
              {[concept.unit, words(concept.frequency), concept.topic].filter(Boolean).join(" · ")}
            </span>
            <span className="text-xs">{readWhere(concept, mode)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
