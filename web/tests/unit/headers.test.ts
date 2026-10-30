// web/tests/unit/headers.test.ts
// The post-build headers step (scripts/headers.ts): every way a page or a
// build can break decision 9's policy fails, and a good build gets one header
// policy holding every page's hashes.
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";

import { describe, expect, it } from "vitest";

import { DIRECTIVES, metaDirectives } from "../../csp.config.ts";
import {
  MAX_LINE,
  attributes,
  checkBuild,
  checkHeaders,
  checkPage,
  checkPolicy,
  formatPolicy,
  hashSource,
  headerPolicy,
  parsePolicy,
  renderHeaders,
} from "../../scripts/headers.ts";

const SCRIPT = "console.log(1)";
const STYLE = "astro-island{display:contents}";

/** The <meta> policy Astro writes, with the given hashes. */
function meta(scripts: string[] = [], styles: string[] = [], extra = ""): string {
  const base = metaDirectives().join(";");
  const script = ["script-src", ...(DIRECTIVES["script-src"] ?? []), ...scripts].join(" ");
  const style = ["style-src", ...(DIRECTIVES["style-src"] ?? []), ...styles].join(" ");
  return `<meta http-equiv="content-security-policy" content="${base};${extra} ${script}; ${style};">`;
}

function page(head: string, body = "<main><p>Hello</p></main>"): string {
  return `<!DOCTYPE html><html lang="en"><head>${head}</head><body>${body}</body></html>`;
}

function build(pages: Record<string, string>): string {
  const root = mkdtempSync(join(tmpdir(), "pyeconomics-headers-"));
  for (const [path, html] of Object.entries(pages)) {
    mkdirSync(dirname(join(root, path)), { recursive: true });
    writeFileSync(join(root, path), html);
  }
  return root;
}

describe("parsePolicy", () => {
  it("reads directives and sources in order", () => {
    const policy = parsePolicy("default-src 'self'; img-src 'self' data:;; upgrade-insecure-requests");
    expect([...policy]).toEqual([
      ["default-src", ["'self'"]],
      ["img-src", ["'self'", "data:"]],
      ["upgrade-insecure-requests", []],
    ]);
    expect(formatPolicy(policy)).toBe("default-src 'self'; img-src 'self' data:; upgrade-insecure-requests");
  });

  it("refuses a repeated directive", () => {
    expect(() => parsePolicy("img-src 'self'; IMG-SRC data:")).toThrow(/repeats img-src/);
  });
});

describe("attributes", () => {
  it("reads quoted, unquoted and bare attributes like the HTML tokenizer", () => {
    const found = attributes(`<a href="/x?a=1&amp;b=2" data-x='y' hidden title=plain>`);
    expect(found.get("href")).toBe("/x?a=1&b=2");
    expect(found.get("data-x")).toBe("y");
    expect(found.get("hidden")).toBe("");
    expect(found.get("title")).toBe("plain");
  });

  it("keeps the first of a repeated attribute and lowercases names", () => {
    expect(attributes(`<p STYLE="a" style="b">`).get("style")).toBe("a");
  });

  it("returns nothing for a tag without attributes", () => {
    expect(attributes("<p>").size).toBe(0);
    expect(attributes("<br").size).toBe(0);
  });
});

describe("checkPolicy", () => {
  const full = (): string => formatPolicy(headerPolicy(new Map()));

  it("accepts decision 9's policy", () => {
    expect(checkPolicy(parsePolicy(full())).problems).toEqual([]);
  });

  it.each(["'unsafe-inline'", "'unsafe-eval'", "'strict-dynamic'", "*", "https:"])(
    "refuses %s in any directive",
    (source) => {
      const text = full().replace("script-src 'self'", `script-src 'self' ${source}`);
      expect(checkPolicy(parsePolicy(text)).problems).toContain(`script-src holds ${source}`);
    },
  );

  it("refuses a third-party script origin", () => {
    const text = full().replace("script-src 'self'", "script-src 'self' https://cdn.example.com");
    expect(checkPolicy(parsePolicy(text)).problems.join()).toMatch(/does not allow/);
  });

  it("names a missing directive and a missing base source", () => {
    const text = full().replace(/frame-ancestors 'none'; /, "").replace("object-src 'none'", "object-src");
    const { problems } = checkPolicy(parsePolicy(text));
    expect(problems).toContain("frame-ancestors is missing");
    expect(problems).toContain("object-src lacks 'none'");
  });

  it("refuses a directive decision 9 does not have", () => {
    const { problems } = checkPolicy(parsePolicy(`${full()}; frame-src 'self'`));
    expect(problems).toContain("frame-src is not a directive of decision 9's policy");
  });

  it("collects the hashes of the hashed directives", () => {
    const hash = hashSource(SCRIPT);
    const text = full().replace("script-src 'self'", `script-src 'self' ${hash}`);
    expect(checkPolicy(parsePolicy(text)).hashes.get("script-src")).toEqual([hash]);
  });
});

describe("checkPage", () => {
  it("accepts a page whose inline script and style are hashed", () => {
    const head = meta([hashSource(SCRIPT)], [hashSource(STYLE)]);
    const report = checkPage(page(`${head}<style>${STYLE}</style>`, `<script>${SCRIPT}</script>`));
    expect(report.problems).toEqual([]);
    expect(report.hashes.get("script-src")).toEqual([hashSource(SCRIPT)]);
  });

  it("refuses a page with no policy, or with two", () => {
    expect(checkPage(page("")).problems).toEqual(["the page has 0 <meta> policies, not one"]);
    expect(checkPage(page(meta() + meta())).problems).toEqual(["the page has 2 <meta> policies, not one"]);
  });

  it("refuses frame-ancestors in a <meta> policy, which browsers ignore there", () => {
    const report = checkPage(page(meta([], [], "frame-ancestors 'none';")));
    expect(report.problems.join()).toMatch(/frame-ancestors is not a directive/);
  });

  it("refuses an inline script or style the policy did not hash", () => {
    const report = checkPage(page(`${meta()}<style>${STYLE}</style>`, `<script>${SCRIPT}</script>`));
    expect(report.problems).toEqual([
      `an inline script (${hashSource(SCRIPT)}) is not hashed in script-src`,
      `an inline style (${hashSource(STYLE)}) is not hashed in style-src`,
    ]);
  });

  it("ignores data blocks, comments and same-origin scripts", () => {
    const body =
      `<script type="application/ld+json">{"a":1}</script>` +
      `<!-- <script>alert(1)</script> -->` +
      `<script type="module" src="/_astro/page.js"></script>`;
    expect(checkPage(page(meta(), body)).problems).toEqual([]);
  });

  it("refuses scripts and stylesheets from another origin", () => {
    const head = `${meta()}<link rel="stylesheet" href="https://cdn.example.com/a.css">`;
    const body = `<script src="https://cdn.example.com/a.js"></script><script src="//cdn.example.com/b.js"></script>`;
    expect(checkPage(page(head, body)).problems).toEqual([
      "a script loads from https://cdn.example.com/a.js, another origin",
      "a script loads from //cdn.example.com/b.js, another origin",
      "a stylesheet link loads from https://cdn.example.com/a.css, another origin",
    ]);
  });

  it("refuses inline style attributes, event handlers and javascript: URLs", () => {
    const body = `<p style="color:red">x</p><button onclick="go()">y</button><a href=" JavaScript:go()">z</a>`;
    const problems = checkPage(page(meta(), body)).problems;
    expect(problems).toHaveLength(3);
    expect(problems[0]).toMatch(/inline style attribute/);
    expect(problems[1]).toBe("an event-handler attribute (onclick)");
    expect(problems[2]).toBe("a javascript: URL in href");
  });

  it("refuses a style attribute on MathML too", () => {
    const body = `<math><mi style="color:red">x</mi></math>`;
    expect(checkPage(page(meta(), body)).problems.join()).toMatch(/inline style attribute/);
  });
});

describe("headerPolicy and renderHeaders", () => {
  it("writes decision 9's directives in order with the sorted union of hashes", () => {
    const b = hashSource("b");
    const a = hashSource("a");
    const policy = headerPolicy(new Map([["script-src", new Set([b, a])]]));
    expect([...policy.keys()]).toEqual(Object.keys(DIRECTIVES));
    expect(policy.get("script-src")).toEqual([...(DIRECTIVES["script-src"] ?? []), ...[a, b].sort()]);
    expect(policy.get("frame-ancestors")).toEqual(["'none'"]);
  });

  it("puts the policy and security headers on every path and caches /_astro/*", () => {
    const text = renderHeaders(headerPolicy(new Map()));
    expect(text).toMatch(/^\/\*\n {2}Content-Security-Policy: default-src 'self'; /);
    for (const name of [
      "Strict-Transport-Security: max-age=63072000; includeSubDomains; preload",
      "X-Content-Type-Options: nosniff",
      "Referrer-Policy: strict-origin-when-cross-origin",
      "Permissions-Policy: ",
      "Cross-Origin-Opener-Policy: same-origin",
    ]) {
      expect(text).toContain(`\n  ${name}`);
    }
    expect(text).toContain("\n/_astro/*\n  Cache-Control: public, max-age=31536000, immutable\n");
    expect(checkHeaders(text)).toEqual([]);
  });

  it("refuses a line over Cloudflare's limit and more than 100 rules", () => {
    expect(checkHeaders(`/*\n  X-Long: ${"a".repeat(MAX_LINE)}\n`)).toEqual([
      `_headers line 2 has ${MAX_LINE + 10} characters, over ${MAX_LINE}`,
    ]);
    const rules = Array.from({ length: 101 }, (_, i) => `/p${i}\n  X-A: b`).join("\n");
    expect(checkHeaders(rules)).toEqual(["_headers has 101 rules, over 100"]);
  });
});

describe("checkBuild", () => {
  it("unions every page's hashes into one header policy", () => {
    const one = hashSource("one");
    const two = hashSource("two");
    const root = build({
      "index.html": page(meta([one])),
      "a/index.html": page(meta([two])),
      "version.json": "{}",
    });
    const report = checkBuild(root);
    expect(report.problems).toEqual([]);
    expect(report.pages).toBe(2);
    expect(report.headers).toContain(`script-src 'self' 'wasm-unsafe-eval' ${[one, two].sort().join(" ")};`);
  });

  it("names the page that breaks the policy", () => {
    const root = build({ "index.html": page(meta()), "bad/index.html": page("") });
    expect(checkBuild(root).problems).toEqual(["bad/index.html: the page has 0 <meta> policies, not one"]);
  });

  it.each(["_worker.js", "_worker.js/index.js", "_routes.json", "server/entry.mjs", "chunks/a.mjs"])(
    "refuses server-rendered output (%s)",
    (path) => {
      const root = build({ "index.html": page(meta()), [path]: "" });
      expect(checkBuild(root).problems.join()).toMatch(/server-rendered route/);
    },
  );

  it("refuses a _headers file copied from public/ and a build with no page", () => {
    expect(checkBuild(build({ "index.html": page(meta()), _headers: "" })).problems).toEqual([
      "dist/_headers already exists: headers come from csp.config.ts, never public/",
    ]);
    expect(checkBuild(build({ "favicon.svg": "<svg/>" })).problems).toEqual(["the build wrote no page"]);
  });
});
