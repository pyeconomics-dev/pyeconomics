// web/tests/unit/model-page.test.ts
// The model page (src/components/models/ModelPage.astro), rendered through
// Astro's container API with a toy model whose every text field plants a
// <script> element and an onerror= attribute: the page holds neither, only
// their escaped text, because card text reaches HTML through Astro's escaping
// alone. A formula that plants HTML fails instead of rendering.
import { experimental_AstroContainer as AstroContainer } from "astro/container";
import { describe, expect, it } from "vitest";

import ModelPage from "@/components/models/ModelPage.astro";
import type { Model } from "@/lib/registry-schema";
import { attributes, startTags } from "../../scripts/headers.ts";

const SCRIPT = "<script>alert(1)</script>";
const IMAGE = '<img src="x" onerror="alert(2)">';
const HOSTILE = `${SCRIPT} ${IMAGE}`;

const TOY: Model = {
  id: "toy.hostile",
  version: 1,
  domain: "toy",
  title: `Hostile ${HOSTILE}`,
  summary: `A summary ${HOSTILE}`,
  tags: [HOSTILE],
  formula: [String.raw`x = \frac{a}{b}`],
  assumptions: [`An assumption ${HOSTILE}`],
  limitations: [`A limitation ${HOSTILE}`],
  evidence: "standard",
  cost: "instant",
  references: [
    { key: "k", citation: `A citation ${HOSTILE}`, doi: null, url: "https://example.org/", locator: HOSTILE, isbn: null },
  ],
  invariants: [],
  no_invariants_reason: HOSTILE,
  examples: [{ name: `example ${HOSTILE}`, note: `A note ${HOSTILE}`, inputs: { rate: HOSTILE } }],
  charts: [],
  aliases: [],
  bindings: [],
  extra: null,
  changelog: [{ version: 1, note: `A change ${HOSTILE}` }],
  input_schema: {
    type: "object",
    properties: { rate: { type: "number", "x-unit": `rate ${HOSTILE}`, description: `The rate ${HOSTILE}` } },
  },
  output_schema: { type: "object", properties: { value: { type: "number", description: HOSTILE } } },
  card: `# Hostile\n\n${HOSTILE}\n`,
  example_result: {
    model_id: "toy.hostile",
    model_version: 1,
    inputs: { rate: HOSTILE },
    outputs: { value: HOSTILE },
    warnings: [{ code: "toy", message: HOSTILE }],
    manifest: {},
  },
  example_figure: null,
};

const SURFACE = {
  id: "toy.hostile",
  rest: "/v1/models/toy.hostile/run",
  methods: ["GET", "POST"],
  mcp_tool: null,
  cli: "pyeconomics models run toy.hostile",
};

async function render(model: Model): Promise<string> {
  const container = await AstroContainer.create();
  return container.renderToString(ModelPage, {
    props: { model, surface: SURFACE },
    request: new Request("https://pyeconomics.dev/models/toy/hostile/"),
  });
}

/** Every start tag of the page, with the JSON-LD block's text left out. */
function tags(html: string): string[] {
  return startTags(html.replace(/(<script type="application\/ld\+json">)[\s\S]*?<\/script>/g, "$1"));
}

describe("the model page", () => {
  it("holds no <script> element and no event-handler attribute from card text", async () => {
    const html = await render(TOY);
    const found = tags(html);
    expect(found.filter((tag) => /^<script\b/i.test(tag))).toEqual(['<script type="application/ld+json">']);
    for (const tag of found) {
      expect(tag.toLowerCase().startsWith("<img") && attributes(tag).get("src") === "x", tag).toBe(false);
      for (const name of attributes(tag).keys()) expect(name, tag).not.toMatch(/^on/);
    }
    expect(html).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
    expect(html).toContain("&lt;img");
  });

  it("writes the JSON-LD so no text can close its element", async () => {
    const html = await render(TOY);
    const block = /<script type="application\/ld\+json">([\s\S]*?)<\/script>/.exec(html)?.[1] ?? "";
    expect(block).not.toMatch(/[<>]/);
    const data = JSON.parse(block) as { name: string; citation: { name: string }[] };
    expect(data.name).toBe(TOY.title);
    expect(data.citation[0]?.name).toBe(`A citation ${HOSTILE}`);
  });

  it("renders every section of a model without bindings, in order", async () => {
    const html = await render(TOY);
    const sections = [...html.matchAll(/data-section="([a-z-]+)"/g)].map((match) => match[1]);
    expect(sections).toEqual([
      "summary",
      "formula",
      "variables",
      "worked-example",
      "assumptions",
      "limitations",
      "evidence",
      "citations",
      "changelog",
      "use-it-elsewhere",
    ]);
    expect(html).toContain("<math");
    expect(html).not.toContain("MCP tool");
  });

  it("fails on a formula that plants HTML rather than rendering it", async () => {
    await expect(render({ ...TOY, formula: [String.raw`\href{javascript:alert(1)}{x}`] })).rejects.toThrow(
      /not allowed in a formula/,
    );
    await expect(render({ ...TOY, formula: [String.raw`\htmlClass{x}{y}`] })).rejects.toThrow(/strict mode|not allowed/);
  });
});
