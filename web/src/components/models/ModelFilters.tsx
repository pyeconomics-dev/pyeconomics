// web/src/components/models/ModelFilters.tsx
// The /models/ filters (Phase 5 Step 7; ADR-0013 decision 10): one native
// <select> per facet, each option with the number of models it would leave,
// combined with AND over every model the build listed. The build renders the
// whole list, so a visitor without JavaScript sees every model; once
// hydrated, the island reads the filters from the query string (only values
// the facets offer: src/lib/filters.ts parseFilters), applies them, and
// writes each change back with replaceState, so a filtered view can be shared.
import { useEffect, useState } from "react";

import {
  applyFilters,
  filterQuery,
  optionCounts,
  parseFilters,
  type Facet,
  type FilterKey,
  type FilterModel,
  type Filters,
  withFilter,
} from "@/lib/filters";

const SELECT =
  "h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs outline-none " +
  "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50";

export interface ModelFiltersProps {
  models: FilterModel[];
  facets: Facet[];
}

export default function ModelFilters({ models, facets }: ModelFiltersProps) {
  const [filters, setFilters] = useState<Filters>(new Map());
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setFilters(parseFilters(window.location.search, facets));
    setReady(true);
  }, [facets]);

  const choose = (key: FilterKey, value: string) => {
    const next = withFilter(filters, key, value);
    setFilters(next);
    window.history.replaceState(null, "", `${window.location.pathname}${filterQuery(next)}`);
  };
  const shown = applyFilters(models, filters);
  const active = filters.size > 0;

  return (
    <div className="flex flex-col gap-6" data-model-filters="" data-ready={ready ? "true" : "false"}>
      <form
        aria-label="Filter models"
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        onSubmit={(event) => event.preventDefault()}
      >
        {facets.map((facet) => {
          const counts = optionCounts(models, filters, facet.key);
          const selected = filters.get(facet.key) ?? "";
          return (
            <div key={facet.key} className="flex flex-col gap-1">
              <label htmlFor={`filter-${facet.key}`} className="text-sm font-medium">
                {facet.label}
              </label>
              <select
                id={`filter-${facet.key}`}
                name={facet.key}
                className={SELECT}
                value={selected}
                onChange={(event) => choose(facet.key, event.target.value)}
              >
                <option value="">Any</option>
                {facet.options.map((option) => {
                  const count = counts.get(option.value) ?? 0;
                  return (
                    <option
                      key={option.value}
                      value={option.value}
                      disabled={count === 0 && option.value !== selected}
                    >
                      {`${option.label} (${String(count)})`}
                    </option>
                  );
                })}
              </select>
            </div>
          );
        })}
      </form>
      <div className="flex flex-wrap items-center gap-4">
        <p aria-live="polite" data-filter-count={shown.length}>
          {`Showing ${String(shown.length)} of ${String(models.length)} models.`}
        </p>
        {active && (
          <button
            type="button"
            className="text-sm text-link underline underline-offset-4"
            onClick={() => {
              setFilters(new Map());
              window.history.replaceState(null, "", window.location.pathname);
            }}
          >
            Clear filters
          </button>
        )}
      </div>
      <ul className="flex flex-col gap-4" data-model-list="">
        {shown.map((model) => (
          <li key={model.id} className="rounded-md border px-4 py-3" data-model={model.id}>
            <h2 className="text-lg font-semibold">
              <a href={model.path}>{model.title}</a>
            </h2>
            <p className="mt-1">{model.summary}</p>
            <p className="mt-2 text-sm text-muted-foreground">
              {model.domainTitle} · Evidence: {model.evidenceLabel} · Cost class: {model.costLabel} ·{" "}
              {model.dataLabel}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
