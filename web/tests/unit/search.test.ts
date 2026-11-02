// web/tests/unit/search.test.ts
// The search library (src/lib/search.ts): Pagefind is loaded once from the
// site's own origin, an excerpt's HTML becomes text runs (only <mark> means
// anything, every other tag is dropped, entities are decoded into text), and
// a result whose URL is not a same-origin path is refused.
import { afterEach, describe, expect, it, vi } from "vitest";

import { BUNDLE, MAX_QUERY, excerptParts, loadPagefind, resetPagefind, resultPath, search, type Pagefind } from "@/lib/search";

function fake(results: { url: string; excerpt: string; meta: Record<string, string> }[]): Pagefind & { queries: string[] } {
  const queries: string[] = [];
  return {
    queries,
    options: vi.fn(() => Promise.resolve()),
    init: vi.fn(() => Promise.resolve()),
    search: (query: string) => {
      queries.push(query);
      return Promise.resolve({ results: results.map((data) => ({ data: () => Promise.resolve(data) })) });
    },
  };
}

afterEach(() => resetPagefind());

describe("excerptParts", () => {
  it("marks the matches and keeps the rest as text", () => {
    expect(excerptParts("Bond <mark>duration</mark> and convexity")).toEqual([
      { text: "Bond ", marked: false },
      { text: "duration", marked: true },
      { text: " and convexity", marked: false },
    ]);
  });

  it("drops every other tag and decodes entities into text, never markup", () => {
    const parts = excerptParts('&lt;script&gt;alert(1)&lt;/script&gt; <img src=x onerror="a()"><b>bold</b> &amp; &#39;q&#x27; &#8364;');
    expect(parts).toEqual([{ text: "<script>alert(1)</script> bold & 'q' €", marked: false }]);
  });

  it("is empty for an empty excerpt", () => {
    expect(excerptParts("")).toEqual([]);
  });
});

describe("resultPath", () => {
  it("accepts a same-origin path only", () => {
    expect(resultPath("/models/fixed-income/duration/")).toBe("/models/fixed-income/duration/");
    expect(resultPath("//evil.example/")).toBeNull();
    expect(resultPath("https://evil.example/")).toBeNull();
    expect(resultPath("javascript:alert(1)")).toBeNull();
  });
});

describe("search", () => {
  it("returns hits with a model's domain and summary, and refuses foreign URLs", async () => {
    const pagefind = fake([
      { url: "/models/fixed-income/duration/", excerpt: "<mark>duration</mark>", meta: { title: "Bond duration", kind: "Model", domain: "Fixed income", summary: "Duration." } },
      { url: "https://evil.example/", excerpt: "x", meta: { title: "Evil" } },
      { url: "/problems/invalid-input/", excerpt: "an <mark>input</mark>", meta: { title: "Invalid input", kind: "Problem" } },
    ]);
    const hits = await search("  duration  ", 8, pagefind);
    expect(pagefind.queries).toEqual(["duration"]);
    expect(hits.map((hit) => hit.url)).toEqual(["/models/fixed-income/duration/", "/problems/invalid-input/"]);
    expect(hits[0]).toMatchObject({ title: "Bond duration", kind: "Model", domain: "Fixed income", summary: "Duration." });
    expect(hits[1]).toMatchObject({ kind: "Problem", domain: null, summary: null });
  });

  it("sends nothing for an empty query and cuts a long one", async () => {
    const pagefind = fake([]);
    expect(await search("   ", 8, pagefind)).toEqual([]);
    await search("x".repeat(500), 8, pagefind);
    expect(pagefind.queries).toEqual(["x".repeat(MAX_QUERY)]);
  });
});

describe("loadPagefind", () => {
  it("imports the bundle from the site's own path, once", async () => {
    const pagefind = fake([]);
    const importer = vi.fn(() => Promise.resolve(pagefind));
    await loadPagefind(importer);
    await loadPagefind(importer);
    expect(importer).toHaveBeenCalledTimes(1);
    expect(importer).toHaveBeenCalledWith(BUNDLE);
    expect(BUNDLE.startsWith("/")).toBe(true);
    expect(pagefind.init).toHaveBeenCalledTimes(1);
  });
});
