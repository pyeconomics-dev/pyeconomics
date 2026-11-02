// web/src/lib/search.ts
// Search through Pagefind's own JavaScript API (Phase 5 Step 7; ADR-0013
// decision 10). scripts/search-index.ts writes the index into dist/pagefind/
// after the build; the islands load /pagefind/pagefind.js from the site's own
// origin only when a visitor searches, and Pagefind fetches its WebAssembly
// and index chunks from the same directory: no query leaves the page, and no
// third party is called. The policy allows the WebAssembly ('wasm-unsafe-eval')
// and Pagefind's same-origin worker (worker-src 'self'), as decision 9 says.
//
// A result's excerpt comes from Pagefind as HTML: the page's text escaped,
// with <mark> around each match. It never reaches the page as HTML:
// excerptParts reads it into plain text runs, keeping only which runs were
// marked, and React renders them as text.

/** Where the build writes Pagefind's bundle (scripts/search-index.ts). */
export const BUNDLE = "/pagefind/pagefind.js";

/** The longest query sent to the index; a longer one is cut. */
export const MAX_QUERY = 100;

/** What a result shows. */
export interface SearchHit {
  url: string;
  title: string;
  /** "Model", "Domain" or "Problem" (data-pagefind-meta="kind"). */
  kind: string | null;
  /** A model's domain. */
  domain: string | null;
  /** A model's summary. */
  summary: string | null;
  excerpt: ExcerptPart[];
}

/** A run of excerpt text, and whether it matched the query. */
export interface ExcerptPart {
  text: string;
  marked: boolean;
}

interface PagefindData {
  url: string;
  excerpt: string;
  meta: Record<string, string | undefined>;
}

interface PagefindResult {
  data: () => Promise<PagefindData>;
}

/** The part of Pagefind's API the islands use. */
export interface Pagefind {
  options: (options: Record<string, unknown>) => Promise<void>;
  init: () => Promise<void>;
  search: (query: string) => Promise<{ results: PagefindResult[] } | null>;
}

let loading: Promise<Pagefind> | null = null;

/** Load Pagefind once, from the site's own origin. */
export function loadPagefind(importer: (url: string) => Promise<unknown> = (url) => import(/* @vite-ignore */ url)): Promise<Pagefind> {
  loading ??= importer(BUNDLE).then(async (module) => {
    const pagefind = module as Pagefind;
    await pagefind.options({ excerptLength: 24 });
    await pagefind.init();
    return pagefind;
  });
  return loading;
}

/** Forget the loaded bundle (tests). */
export function resetPagefind(): void {
  loading = null;
}

const ENTITIES: ReadonlyMap<string, string> = new Map([
  ["amp", "&"],
  ["lt", "<"],
  ["gt", ">"],
  ["quot", '"'],
  ["#39", "'"],
  ["#x27", "'"],
  ["nbsp", " "],
]);

function decode(text: string): string {
  return text.replace(/&(#x?[0-9a-fA-F]+|[a-z]+);/g, (whole, name: string) => {
    const known = ENTITIES.get(name);
    if (known !== undefined) return known;
    if (/^#x[0-9a-fA-F]+$/.test(name)) return String.fromCodePoint(Number.parseInt(name.slice(2), 16));
    if (/^#\d+$/.test(name)) return String.fromCodePoint(Number(name.slice(1)));
    return whole;
  });
}

/**
 * Read an excerpt's HTML into text runs: <mark> and </mark> toggle the
 * marked state, every other tag is dropped, and entities are decoded into
 * the characters a text node then holds.
 */
export function excerptParts(html: string): ExcerptPart[] {
  const parts: ExcerptPart[] = [];
  let marked = false;
  for (const piece of html.split(/(<[^>]*>)/)) {
    if (piece.startsWith("<")) {
      const tag = piece.toLowerCase().replace(/\s+/g, "");
      if (tag === "<mark>") marked = true;
      else if (tag === "</mark>") marked = false;
      continue;
    }
    const text = decode(piece);
    if (text === "") continue;
    const last = parts.at(-1);
    if (last && last.marked === marked) last.text += text;
    else parts.push({ text, marked });
  }
  return parts;
}

/** A Pagefind result's URL as a same-origin path; anything else is refused. */
export function resultPath(url: string): string | null {
  return url.startsWith("/") && !url.startsWith("//") ? url : null;
}

/** Search the index: up to `limit` hits, in Pagefind's order. */
export async function search(query: string, limit = 8, pagefind?: Pagefind): Promise<SearchHit[]> {
  const text = query.trim().slice(0, MAX_QUERY);
  if (text === "") return [];
  const index = pagefind ?? (await loadPagefind());
  const response = await index.search(text);
  const data = await Promise.all((response?.results ?? []).slice(0, limit).map((result) => result.data()));
  return data.flatMap((item) => {
    const url = resultPath(item.url);
    if (url === null) return [];
    return [
      {
        url,
        title: item.meta.title ?? url,
        kind: item.meta.kind ?? null,
        domain: item.meta.domain ?? null,
        summary: item.meta.summary ?? null,
        excerpt: excerptParts(item.excerpt),
      },
    ];
  });
}
