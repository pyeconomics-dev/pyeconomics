// web/src/components/models/ModelFilters.tsx
// The /models/ filters (Phase 5 Step 7; ADR-0013 decision 10): one native
// <select> per facet, each option with the number of models it would leave,
// combined with AND over every model the build listed. The build renders the
// whole list, so a visitor without JavaScript sees every model; once
// hydrated, the island reads the filters from the query string (only values
// the facets offer: src/lib/filters.ts parseFilters), applies them, and
// writes each change back with replaceState, so a filtered view can be shared.
// A choice a visitor made before the island hydrated is read from the selects
// themselves, through the same check, and kept (Phase 5 Step 18).
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

/** What the selects held when the island began to hydrate: a visitor's early choices, as a query string. */
function earlyChoices(facets: readonly Facet[]): string {
  if (typeof document === "undefined") return "";
  const params = new URLSearchParams();
  for (const facet of facets) {
    const element = document.getElementById(`filter-${facet.key}`);
    if (element instanceof HTMLSelectElement && element.value !== "") params.set(facet.key, element.value);
  }
  return params.toString();
}

export default function ModelFilters({ models, facets }: ModelFiltersProps) {
  const [filters, setFilters] = useState<Filters>(new Map());
  const [ready, setReady] = useState(false);
  // Read while hydrating, before React sets the selects to its own state.
  const [early] = useState(() => earlyChoices(facets));

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    for (const [key, value] of new URLSearchParams(early)) params.set(key, value);
    const found = parseFilters(`?${params.toString()}`, facets);
    setFilters(found);
    if (early !== "") window.history.replaceState(null, "", `${window.location.pathname}${filterQuery(found)}`);
    setReady(true);
  }, [facets, early]);

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
        className="grid grid-cols-2 gap-x-3 gap-y-3 sm:gap-4 lg:grid-cols-4"
        onSubmit={(event) => event.preventDefault()}
      >
        {facets.map((facet) => {
          const counts = optionCounts(models, filters, facet.key);
          const selected = filters.get(facet.key) ?? "";
          return (
            <div key={facet.key} className="flex min-w-0 flex-col gap-1">
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
      <ul className="grid gap-4 lg:grid-cols-2" data-model-list="">
        {shown.map((model) => (
          <li key={model.id} className="card flex flex-col gap-1" data-model={model.id}>
            <p className="eyebrow">{model.domainTitle}</p>
            <h2 className="card-title">
              <a href={model.path}>{model.title}</a>
            </h2>
            <p>{model.summary}</p>
            <p className="mt-auto pt-2 text-sm text-muted-foreground">
              <code>{model.id}</code> · Evidence: {model.evidenceLabel} · Cost class: {model.costLabel} · {model.dataLabel}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
