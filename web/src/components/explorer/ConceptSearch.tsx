// web/src/components/explorer/ConceptSearch.tsx
// The /data/ search (Phase 5 Step 9; ADR-0013 decision 11): words matched
// against each concept's title, id, unit, frequency and topic, a frequency
// and a topic filter, and "only what this site serves" (the concepts the
// hosted snapshot holds, from concepts.json). The build renders the whole
// list, so a visitor without JavaScript sees every concept; once hydrated,
// the island filters it as the visitor types (src/lib/explorer.ts
// searchConcepts). With no words typed the list is grouped by topic, each
// topic a heading the links above the list jump to; a search gives one list,
// best match first (Step 18's round 1: 171 series in id order opened on
// Canada's). What a visitor typed before the island hydrated is kept (round
// 0: it was lost). Served by the local app (GET /version's mode is `local`,
// Phase 5 Step 10), every concept without parameters is charted, so the
// filter goes and each concept says so. The search keeps nothing: no
// storage, no URL.
import { useEffect, useState } from "react";

import { facetValues, searchConcepts, topicAnchor, type ConceptListing, type ConceptQuery } from "@/lib/explorer";
import { serverMode, type ServerMode } from "@/lib/series-request";

const CONTROL =
  "h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs outline-none " +
  "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50";
const SEARCH =
  "h-11 w-full rounded-md border border-input bg-background px-3 py-1 text-base shadow-xs outline-none " +
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

function Card({ concept, mode, topic = false }: { concept: ConceptListing; mode: ServerMode; topic?: boolean }) {
  return (
    <li className="flex flex-col gap-1 rounded-md border px-4 py-3" data-concept={concept.id}>
      <a href={concept.path} className="font-medium">
        {concept.title}
      </a>
      <span className="text-sm text-muted-foreground">
        {[concept.unit, words(concept.frequency), topic ? concept.topic : ""].filter(Boolean).join(" · ")}
      </span>
      <code className="text-xs text-muted-foreground">{concept.id}</code>
      <span className="text-xs">{readWhere(concept, mode)}</span>
    </li>
  );
}

/** What the form held when the island began to hydrate: what a visitor typed and chose before it could answer. */
function earlyQuery(): ConceptQuery | null {
  if (typeof document === "undefined") return null;
  const field = (id: string) => document.getElementById(id);
  const text = field("concept-search");
  const frequency = field("concept-frequency");
  const topic = field("concept-topic");
  const served = field("concept-served");
  return {
    text: text instanceof HTMLInputElement ? text.value : "",
    frequency: frequency instanceof HTMLSelectElement ? frequency.value : "",
    topic: topic instanceof HTMLSelectElement ? topic.value : "",
    served: served instanceof HTMLInputElement ? served.checked : false,
  };
}

export default function ConceptSearch({ concepts }: ConceptSearchProps) {
  const [query, setQuery] = useState<ConceptQuery>({ text: "", frequency: "", topic: "", served: false });
  const [ready, setReady] = useState(false);
  const [mode, setMode] = useState<ServerMode>("hosted");
  // Read while hydrating, before React sets the fields to its own state.
  const [early] = useState(earlyQuery);
  useEffect(() => {
    // What the visitor entered before the island hydrated is kept, each
    // choice only if the form offers it.
    if (early) {
      setQuery({
        text: early.text,
        frequency: facetValues(concepts, "frequency").includes(early.frequency) ? early.frequency : "",
        topic: facetValues(concepts, "topic").includes(early.topic) ? early.topic : "",
        served: early.served,
      });
    }
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
  }, [early, concepts]);

  const shown = searchConcepts(concepts, query);
  const frequencies = facetValues(concepts, "frequency");
  const topics = facetValues(concepts, "topic");
  const set = (change: Partial<ConceptQuery>) => setQuery((current) => ({ ...current, ...change }));
  // With no words, the list is read by topic; a search ranks across topics.
  const grouped = query.text.trim() === "";
  const groups = grouped
    ? topics
        .map((topic) => ({
          topic,
          concepts: shown.filter((concept) => concept.topic === topic).sort((a, b) => a.title.localeCompare(b.title, "en")),
        }))
        .filter((group) => group.concepts.length > 0)
    : [];

  return (
    <div className="flex flex-col gap-6" data-concept-search="" data-ready={ready ? "true" : "false"} data-mode={mode}>
      <form
        role="search"
        aria-label="Search the data catalog"
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        onSubmit={(event) => event.preventDefault()}
      >
        <div className="flex flex-col gap-1 sm:col-span-2 lg:col-span-4">
          <label htmlFor="concept-search" className="font-medium">
            Search the series
          </label>
          <input
            id="concept-search"
            type="search"
            className={SEARCH}
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
          <label className="flex items-center gap-2 text-sm sm:col-span-2 lg:self-end lg:pb-2">
            <input id="concept-served" type="checkbox" checked={query.served} onChange={(event) => set({ served: event.target.checked })} />
            Only the series this site charts
          </label>
        )}
      </form>
      <p role="status" aria-live="polite" className="text-sm">
        {shown.length === concepts.length
          ? `${String(concepts.length)} series, by topic.`
          : `${String(shown.length)} of ${String(concepts.length)} series match.`}
      </p>
      {grouped && groups.length > 1 && (
        <nav aria-label="Topics" data-topics="">
          <ul className="flex flex-wrap gap-2 text-sm">
            {groups.map((group) => (
              <li key={group.topic}>
                <a href={`#${topicAnchor(group.topic)}`} className="inline-flex min-h-9 items-center rounded-full border px-3 no-underline hover:bg-accent">
                  {group.topic} ({group.concepts.length})
                </a>
              </li>
            ))}
          </ul>
        </nav>
      )}
      {grouped ? (
        <div className="flex flex-col gap-8" data-concept-list="">
          {groups.map((group) => (
            <section key={group.topic} aria-labelledby={topicAnchor(group.topic)} className="flex flex-col gap-3" data-topic={group.topic}>
              <h2 id={topicAnchor(group.topic)} className="subsection-title scroll-mt-6">
                {group.topic}
              </h2>
              <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {group.concepts.map((concept) => (
                  <Card key={concept.id} concept={concept} mode={mode} />
                ))}
              </ul>
            </section>
          ))}
        </div>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" data-concept-list="">
          {shown.map((concept) => (
            <Card key={concept.id} concept={concept} mode={mode} topic />
          ))}
        </ul>
      )}
    </div>
  );
}
