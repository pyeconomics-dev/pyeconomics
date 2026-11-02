// web/src/lib/filters.ts
// The /models/ filters (Phase 5 Step 7; ADR-0013 decision 10): domain,
// syllabus level and topic, evidence status, cost class, data needs and tag,
// combined with AND, each shown with the number of models it would leave.
// The filter island ships this module, so it imports nothing: the build
// computes each model's values and the facets (src/lib/catalog.ts) and hands
// them over as props.
//
// The state lives in the query string, and a query string is a visitor's
// input: parseFilters keeps a value only when it is one of the facet's known
// values, so nothing from the URL ever reaches the page but a value the build
// wrote, and React renders it as text. Every value is a neutral slug; none
// carries a mark (ROADMAP §5 "CFA Institute marks and content").

/** The filter keys, in the order the query string and the form write them. */
export const FILTER_KEYS = ["domain", "level", "topic", "evidence", "cost", "data", "tag"] as const;

export type FilterKey = (typeof FILTER_KEYS)[number];

/** The selected value of each filter in use. */
export type Filters = ReadonlyMap<FilterKey, string>;

/** One model, as the filters and the result list see it. */
export interface FilterModel {
  id: string;
  title: string;
  summary: string;
  path: string;
  domainTitle: string;
  evidenceLabel: string;
  costLabel: string;
  dataLabel: string;
  /** Each filter's values for this model; a model can hold several tags or topics. */
  values: ReadonlyMap<FilterKey, readonly string[]>;
}

/** One choice of a filter: its query-string value and what a reader sees. */
export interface FilterOption {
  value: string;
  label: string;
}

/** One filter and its choices, in the order they are offered. */
export interface Facet {
  key: FilterKey;
  label: string;
  options: FilterOption[];
}

/** A tag as a neutral query value: lowercase words joined by hyphens. */
export function slug(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/**
 * Read the filters from a query string: the first value of each key, kept
 * only when the facet offers it. Unknown keys and values are dropped.
 */
export function parseFilters(search: string, facets: readonly Facet[]): Filters {
  const params = new URLSearchParams(search);
  const filters = new Map<FilterKey, string>();
  for (const facet of facets) {
    const given = params.get(facet.key);
    if (given !== null && facet.options.some((option) => option.value === given)) {
      filters.set(facet.key, given);
    }
  }
  return filters;
}

/** The filters with `key` set to `value`, or cleared when `value` is "". */
export function withFilter(filters: Filters, key: FilterKey, value: string): Filters {
  const next = new Map(filters);
  if (value === "") next.delete(key);
  else next.set(key, value);
  return next;
}

/** The query string for the filters in use, in FILTER_KEYS order; "" for none. */
export function filterQuery(filters: Filters): string {
  const params = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    const value = filters.get(key);
    if (value !== undefined) params.set(key, value);
  }
  const text = params.toString();
  return text === "" ? "" : `?${text}`;
}

/** Whether a model passes every filter in use, leaving out `skip`. */
export function matches(model: FilterModel, filters: Filters, skip?: FilterKey): boolean {
  return FILTER_KEYS.every((key) => {
    const value = filters.get(key);
    return key === skip || value === undefined || (model.values.get(key) ?? []).includes(value);
  });
}

/** The models that pass every filter in use, in their given order. */
export function applyFilters(models: readonly FilterModel[], filters: Filters): FilterModel[] {
  return models.filter((model) => matches(model, filters));
}

/**
 * How many models each of a facet's options would leave: the other filters
 * applied, this one set to the option. A model counts once per option it holds.
 */
export function optionCounts(models: readonly FilterModel[], filters: Filters, key: FilterKey): Map<string, number> {
  const counts = new Map<string, number>();
  for (const model of models) {
    if (!matches(model, filters, key)) continue;
    for (const value of new Set(model.values.get(key))) counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return counts;
}
