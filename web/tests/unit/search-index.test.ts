// web/tests/unit/search-index.test.ts
// The post-build search step's checks (scripts/search-index.ts): the pages
// marked searchable, every model page among them and never the 404 page, and
// the indexed count read from Pagefind's entry file.
import { describe, expect, it } from "vitest";

import { MARKER, UNUSED, checkSearchable, indexedPages, searchablePages } from "../../scripts/search-index.ts";

const PAGES = new Map([
  ["index.html", "<main>home</main>"],
  ["404.html", "<main>lost</main>"],
  ["models/fixed-income/duration/index.html", `<main ${MARKER}="">duration</main>`],
  ["problems/index.html", `<main ${MARKER}="">problems</main>`],
  ["_astro/x.js", MARKER],
]);
const read = (file: string): string => PAGES.get(file) ?? "";

describe("search-index", () => {
  it("finds the pages marked searchable, HTML only", () => {
    expect(searchablePages([...PAGES.keys()], read)).toEqual(["models/fixed-income/duration/index.html", "problems/index.html"]);
  });

  it("requires every model page marked and the 404 page unmarked", () => {
    const files = [...PAGES.keys()];
    const marked = searchablePages(files, read);
    expect(checkSearchable(files, marked, ["fixed_income.duration"])).toEqual([]);
    expect(checkSearchable(files, [], ["fixed_income.duration"])).toEqual([
      `models/fixed-income/duration/index.html: the model page fixed_income.duration is not marked ${MARKER}`,
    ]);
    expect(checkSearchable(files, marked, ["fixed_income.convexity"])[0]).toMatch(/was not built/);
    expect(checkSearchable(files, [...marked, "404.html"], [])).toEqual([
      `404.html is marked ${MARKER}; the 404 page is never searched`,
    ]);
  });

  it("reads the indexed page count from pagefind-entry.json", () => {
    expect(indexedPages('{"version":"1.5.2","languages":{"en":{"page_count":98},"fr":{"page_count":2}}}')).toBe(100);
    expect(indexedPages("{}")).toBe(0);
  });

  it("removes only Pagefind's UI bundles", () => {
    for (const name of UNUSED) expect(name).toMatch(/ui|highlight/);
    expect(UNUSED).not.toContain("pagefind.js");
    expect(UNUSED).not.toContain("pagefind-worker.js");
  });
});
