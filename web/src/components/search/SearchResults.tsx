// web/src/components/search/SearchResults.tsx
// A list of search hits, shared by the header box and /search/: each a link
// to its page, with a model's domain and summary, or the page's excerpt.
// Every string is rendered as React text; the excerpt's matches are <mark>
// elements built from excerptParts (src/lib/search.ts), never parsed HTML.
import type { ExcerptPart, SearchHit } from "@/lib/search";

function Excerpt({ parts }: { parts: readonly ExcerptPart[] }) {
  return (
    <>
      {/* The runs have no identity but their position, and they never reorder. */}
      {parts.map((part, index) =>
        part.marked ? (
          <mark key={index} className="bg-transparent font-semibold text-foreground">
            {part.text}
          </mark>
        ) : (
          <span key={index}>{part.text}</span>
        ),
      )}
    </>
  );
}

export default function SearchResults({ hits, compact = false }: { hits: readonly SearchHit[]; compact?: boolean }) {
  return (
    <ul className={compact ? "flex flex-col divide-y" : "flex flex-col gap-4"} data-search-results="">
      {hits.map((hit) => (
        <li key={hit.url} className={compact ? "py-2" : "rounded-md border px-4 py-3"} data-search-hit={hit.url}>
          <a href={hit.url} className="font-medium">
            {hit.title}
          </a>
          {hit.kind && (
            <span className="ml-2 text-xs text-muted-foreground">
              {hit.domain ? `${hit.kind} · ${hit.domain}` : hit.kind}
            </span>
          )}
          {!compact && (
            <p className="mt-1 text-sm">{hit.summary ?? <Excerpt parts={hit.excerpt} />}</p>
          )}
          {compact && hit.summary && <p className="mt-0.5 line-clamp-2 text-sm text-muted-foreground">{hit.summary}</p>}
        </li>
      ))}
    </ul>
  );
}
