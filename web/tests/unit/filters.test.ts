// web/tests/unit/filters.test.ts
// The /models/ filter logic (src/lib/filters.ts) on toy models: the query
// string is read as data only (an unknown key or value is dropped, never
// echoed), filters combine with AND, and each option's count applies every
// other filter in use.
import { describe, expect, it } from "vitest";

import {
  FILTER_KEYS,
  applyFilters,
  filterQuery,
  matches,
  optionCounts,
  parseFilters,
  slug,
  withFilter,
  type Facet,
  type FilterKey,
  type FilterModel,
} from "@/lib/filters";

function toy(id: string, values: Partial<Record<FilterKey, string[]>>): FilterModel {
  return {
    id,
    title: id,
    summary: "",
    path: `/models/x/${id}/`,
    domainTitle: "X",
    evidenceLabel: "Standard",
    costLabel: "Instant",
    dataLabel: "Data-free",
    values: new Map(FILTER_KEYS.map((key) => [key, new Map(Object.entries(values)).get(key) ?? []])),
  };
}

const MODELS = [
  toy("a", { domain: ["fixed-income"], level: ["1"], topic: ["l1-fixed-income"], cost: ["instant"], tag: ["bond"] }),
  toy("b", { domain: ["fixed-income"], level: ["1", "2"], topic: ["l1-fixed-income", "l2-fixed-income"], cost: ["light"], tag: ["bond", "duration"] }),
  toy("c", { domain: ["macro"], level: ["3"], topic: ["l3-asset-allocation"], cost: ["instant"], tag: [] }),
];

const FACETS: Facet[] = [
  { key: "domain", label: "Domain", options: [{ value: "fixed-income", label: "Fixed income" }, { value: "macro", label: "Macro" }] },
  { key: "cost", label: "Cost", options: [{ value: "instant", label: "Instant" }, { value: "light", label: "Light" }] },
  { key: "tag", label: "Tag", options: [{ value: "bond", label: "bond" }, { value: "duration", label: "duration" }] },
];

describe("parseFilters", () => {
  it("keeps only the values a facet offers", () => {
    const filters = parseFilters("?domain=macro&cost=heavy&tag=bond&evil=<script>", FACETS);
    expect([...filters]).toEqual([
      ["domain", "macro"],
      ["tag", "bond"],
    ]);
  });

  it("drops markup and takes the first value of a repeated key", () => {
    expect(parseFilters("?domain=%3Cimg%20src%3Dx%3E", FACETS).size).toBe(0);
    expect(parseFilters("?domain=macro&domain=fixed-income", FACETS).get("domain")).toBe("macro");
  });
});

describe("filterQuery and withFilter", () => {
  it("writes the filters in a fixed order, and nothing for none", () => {
    let filters = withFilter(new Map(), "tag", "bond");
    filters = withFilter(filters, "domain", "fixed-income");
    expect(filterQuery(filters)).toBe("?domain=fixed-income&tag=bond");
    expect(filterQuery(withFilter(withFilter(filters, "tag", ""), "domain", ""))).toBe("");
  });

  it("round-trips through parseFilters", () => {
    const filters = new Map<FilterKey, string>([
      ["cost", "light"],
      ["domain", "fixed-income"],
    ]);
    expect(parseFilters(filterQuery(filters), FACETS)).toEqual(filters);
  });
});

describe("matching and counts", () => {
  it("combines filters with AND", () => {
    expect(applyFilters(MODELS, new Map([["domain", "fixed-income"]])).map((m) => m.id)).toEqual(["a", "b"]);
    expect(
      applyFilters(
        MODELS,
        new Map<FilterKey, string>([
          ["domain", "fixed-income"],
          ["cost", "instant"],
        ]),
      ).map((m) => m.id),
    ).toEqual(["a"]);
    expect(applyFilters(MODELS, new Map([["topic", "l2-fixed-income"]])).map((m) => m.id)).toEqual(["b"]);
  });

  it("counts each option with every other filter applied", () => {
    const filters = new Map<FilterKey, string>([
      ["domain", "fixed-income"],
      ["cost", "instant"],
    ]);
    expect(optionCounts(MODELS, filters, "cost")).toEqual(
      new Map([
        ["instant", 1],
        ["light", 1],
      ]),
    );
    expect(optionCounts(MODELS, filters, "domain")).toEqual(
      new Map([
        ["fixed-income", 1],
        ["macro", 1],
      ]),
    );
    expect(optionCounts(MODELS, new Map(), "level")).toEqual(
      new Map([
        ["1", 2],
        ["2", 1],
        ["3", 1],
      ]),
    );
  });

  it("skips one filter when asked", () => {
    const model = MODELS[2];
    if (!model) throw new Error("no toy");
    expect(matches(model, new Map([["domain", "fixed-income"]]), "domain")).toBe(true);
    expect(matches(model, new Map([["domain", "fixed-income"]]))).toBe(false);
  });
});

describe("slug", () => {
  it("makes a neutral query value of a tag", () => {
    expect(slug("Value at Risk")).toBe("value-at-risk");
    expect(slug("black-scholes")).toBe("black-scholes");
    expect(slug("  r minus g! ")).toBe("r-minus-g");
  });
});
