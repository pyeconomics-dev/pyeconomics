// web/src/lib/structured-data.ts
// schema.org JSON-LD for the generated pages (Phase 5 Step 5): a model page is
// a WebPage about the model, with its citations, free access and a
// BreadcrumbList. The JSON is written into a non-executed
// <script type="application/ld+json">, so jsonLdText escapes every character
// that could end that element or start markup: model text can never close the
// script and inject HTML.
import { ORIGIN, referenceLink } from "@/lib/models";
import type { Model } from "@/lib/registry-schema";

/** One step of a breadcrumb trail; the last is the page itself. */
export interface Crumb {
  name: string;
  path: string;
}

/** A BreadcrumbList over the trail, each item on the production origin. */
export function breadcrumbList(trail: readonly Crumb[]): Record<string, unknown> {
  return {
    "@type": "BreadcrumbList",
    itemListElement: trail.map((crumb, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: crumb.name,
      item: new URL(crumb.path, ORIGIN).href,
    })),
  };
}

/** A WebPage at `path` with its breadcrumb trail. */
export function webPage(
  path: string,
  name: string,
  description: string,
  trail: readonly Crumb[],
): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    "@id": new URL(path, ORIGIN).href,
    url: new URL(path, ORIGIN).href,
    name,
    description,
    inLanguage: "en",
    isAccessibleForFree: true,
    isPartOf: { "@type": "WebSite", name: "pyeconomics", url: `${ORIGIN}/` },
    breadcrumb: breadcrumbList(trail),
  };
}

/** A model page's WebPage: about the model, citing its references. */
export function modelPage(model: Model, path: string, trail: readonly Crumb[]): Record<string, unknown> {
  return {
    ...webPage(path, model.title, model.summary, trail),
    about: {
      "@type": "Thing",
      name: model.title,
      description: model.summary,
      identifier: model.id,
    },
    citation: model.references.map((reference) => {
      const link = referenceLink(reference);
      return {
        "@type": "CreativeWork",
        name: reference.citation,
        ...(link ? { url: link } : {}),
        ...(reference.isbn ? { isbn: reference.isbn } : {}),
      };
    }),
  };
}

/**
 * JSON for a <script type="application/ld+json">: `<`, `>` and `&` and the
 * line and paragraph separators are written as \u escapes, which JSON reads
 * back unchanged, so no value can end the element.
 */
export function jsonLdText(value: unknown): string {
  return JSON.stringify(value)
    .replaceAll("<", "\\u003c")
    .replaceAll(">", "\\u003e")
    .replaceAll("&", "\\u0026")
    .replaceAll("\u2028", "\\u2028")
    .replaceAll("\u2029", "\\u2029");
}
