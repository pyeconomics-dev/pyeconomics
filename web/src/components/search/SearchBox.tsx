// web/src/components/search/SearchBox.tsx
// The header's search box (Phase 5 Step 7), an island hydrated only when a
// visitor reaches for it (client:interaction, src/directives/interaction.ts):
// until then it is a plain form that submits to /search/, and no page loads a
// script for it, so a model page still loads none until its calculator is in
// view. Once hydrated it searches as the visitor types, through Pagefind on
// the site's own origin (src/lib/search.ts), and lists the first hits below
// the box; Enter opens /search/ with every hit. Escape closes the list.
import { useEffect, useRef, useState } from "react";

import SearchResults from "@/components/search/SearchResults";
import { MAX_QUERY, search, type SearchHit } from "@/lib/search";

const INPUT =
  "h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs outline-none " +
  "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50";

/** How long typing pauses before a search runs, in milliseconds. */
const PAUSE = 120;

export default function SearchBox() {
  const form = useRef<HTMLFormElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    // What the visitor typed before the island hydrated.
    const typed = input.current?.value ?? "";
    if (typed !== "") {
      setQuery(typed);
      setOpen(true);
    }
  }, []);

  useEffect(() => {
    if (query.trim() === "") {
      setHits(null);
      return undefined;
    }
    let current = true;
    const timer = setTimeout(() => {
      search(query, 6).then(
        (found) => {
          if (current) setHits(found);
        },
        () => {
          if (current) setFailed(true);
        },
      );
    }, PAUSE);
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [query]);

  useEffect(() => {
    // While the list is open, Escape closes it, and so does focus or a click
    // that leaves the form.
    if (!open) return undefined;
    const escape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      input.current?.focus();
    };
    const away = (event: Event) => {
      if (event.target instanceof Node && !form.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener("keydown", escape);
    document.addEventListener("focusin", away);
    document.addEventListener("pointerdown", away);
    return () => {
      document.removeEventListener("keydown", escape);
      document.removeEventListener("focusin", away);
      document.removeEventListener("pointerdown", away);
    };
  }, [open]);

  const status = failed
    ? "Search could not load."
    : hits === null
      ? ""
      : `${String(hits.length)} ${hits.length === 1 ? "result" : "results"} shown.`;

  return (
    <form ref={form} role="search" aria-label="Site" action="/search/" method="get" className="relative w-full sm:w-64">
      <label htmlFor="site-search" className="sr-only">
        Search models and pages
      </label>
      <input
        ref={input}
        id="site-search"
        name="q"
        type="search"
        placeholder="Search models"
        autoComplete="off"
        maxLength={MAX_QUERY}
        className={INPUT}
        onInput={(event) => {
          setQuery(event.currentTarget.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
      />
      <p className="sr-only" aria-live="polite">
        {open ? status : ""}
      </p>
      {open && (failed || (hits !== null && query.trim() !== "")) && (
        <div className="absolute right-0 z-20 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-md border bg-background p-3 shadow-lg">
          {failed ? (
            <p className="text-sm">Search could not load. Press Enter to open the search page.</p>
          ) : hits && hits.length > 0 ? (
            <SearchResults hits={hits} compact />
          ) : (
            <p className="text-sm">No results.</p>
          )}
          <p className="mt-2 border-t pt-2 text-sm">
            <a href={`/search/?q=${encodeURIComponent(query.trim())}`}>All results</a>
          </p>
        </div>
      )}
    </form>
  );
}
