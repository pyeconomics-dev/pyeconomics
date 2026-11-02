// web/tests/unit/structured-data.test.ts
// A model page's JSON-LD is a WebPage about the model with its citations,
// free access and a BreadcrumbList, every URL on the production origin, and
// its text can never end the <script> element it is written into.
import { describe, expect, it } from "vitest";

import { modelPath } from "@/lib/models";
import { parseModels } from "@/lib/registry-schema";
import { registryData } from "@/lib/site-data";
import { breadcrumbList, jsonLdText, modelPage, webPage } from "@/lib/structured-data";

const [model] = parseModels(registryData);

describe("modelPage", () => {
  it("describes a WebPage about the model, citing each reference", () => {
    if (!model) throw new Error("no model");
    const path = modelPath(model.id);
    const page = modelPage(model, path, [
      { name: "Home", path: "/" },
      { name: model.title, path },
    ]);
    expect(page["@context"]).toBe("https://schema.org");
    expect(page["@type"]).toBe("WebPage");
    expect(page.url).toBe(`https://pyeconomics.dev${path}`);
    expect(page.isAccessibleForFree).toBe(true);
    expect(page.about).toMatchObject({ "@type": "Thing", identifier: model.id });
    expect((page.citation as unknown[]).length).toBe(model.references.length);
    expect(page.breadcrumb).toMatchObject({ "@type": "BreadcrumbList" });
  });

  it("numbers breadcrumbs from one on the production origin", () => {
    expect(breadcrumbList([{ name: "Home", path: "/" }, { name: "Models", path: "/models/" }])).toEqual({
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Home", item: "https://pyeconomics.dev/" },
        { "@type": "ListItem", position: 2, name: "Models", item: "https://pyeconomics.dev/models/" },
      ],
    });
  });
});

describe("jsonLdText", () => {
  it("escapes what could end the element, and reads back unchanged", () => {
    const hostile = webPage("/x/", "</script><script>alert(1)</script>", "a & b <!-- \u2028 \u2029", []);
    const text = jsonLdText(hostile);
    expect(text).not.toMatch(/[<>&\u2028\u2029]/);
    expect(JSON.parse(text)).toEqual(hostile);
  });
});
