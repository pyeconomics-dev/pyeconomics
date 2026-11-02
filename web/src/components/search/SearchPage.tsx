// web/src/components/search/SearchPage.tsx
// The /search/ page's island (Phase 5 Step 7): a search box and every hit,
// through Pagefind on the site's own origin (src/lib/search.ts). The query
// arrives as ?q= from the header's form; it is read as text, sent only to the
// index in the browser, and written back to the address with replaceState so
// a search can be shared. Pagefind loads only once there is a query.
import { useEffect, useRef, useState } from "react";

import SearchResults from "@/components/search/SearchResults";
import { MAX_QUERY, search, type SearchHit } from "@/lib/search";

const INPUT =
  "h-10 w-full rounded-md border border-input bg-background px-3 py-1 text-base shadow-xs outline-none " +
  "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50";

/** How many hits the page lists. */
const LIMIT = 50;

export default function SearchPage() {
  const input = useRef<HTMLInputElement>(null);
  // null until the address has been read, so the first render never
  // rewrites it.
  const [query, setQuery] = useState<string | null>(null);
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const given = (new URLSearchParams(window.location.search).get("q") ?? "").slice(0, MAX_QUERY);
    if (input.current && given !== "") input.current.value = given;
    setQuery(given);
  }, []);

  useEffect(() => {
    if (query === null) return undefined;
    const text = query.trim();
    const address = text === "" ? window.location.pathname : `${window.location.pathname}?q=${encodeURIComponent(text)}`;
    window.history.replaceState(null, "", address);
    if (text === "") {
      setHits(null);
      return undefined;
    }
    let current = true;
    search(text, LIMIT).then(
      (found) => {
        if (current) setHits(found);
      },
      () => {
        if (current) setFailed(true);
      },
    );
    return () => {
      current = false;
    };
  }, [query]);

  const asked = (query ?? "").trim();
  const status = failed
    ? "Search could not load. Reload the page to try again."
    : hits === null
      ? "Type to search every model, domain and problem page."
      : hits.length === 0
        ? `No results for “${asked}”.`
        : `${String(hits.length)} ${hits.length === 1 ? "result" : "results"} for “${asked}”.`;

  return (
    <div className="flex flex-col gap-6" data-search-page="">
      <form
        role="search"
        aria-label="Search the site"
        className="flex max-w-2xl flex-col gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          setQuery(input.current?.value ?? "");
        }}
      >
        <label htmlFor="search-query" className="font-medium">
          Search
        </label>
        <input
          ref={input}
          id="search-query"
          name="q"
          type="search"
          autoComplete="off"
          maxLength={MAX_QUERY}
          className={INPUT}
          onInput={(event) => setQuery(event.currentTarget.value)}
        />
      </form>
      <p aria-live="polite" data-search-status="">
        {status}
      </p>
      {hits && hits.length > 0 && <SearchResults hits={hits} />}
    </div>
  );
}
