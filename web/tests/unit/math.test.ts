// web/tests/unit/math.test.ts
// Every formula in the registry renders as MathML with no script and no
// inline style, and a formula that would ship error text or an untrusted
// command fails instead.
import { describe, expect, it } from "vitest";

import { renderMath } from "@/lib/math";
import { registryData } from "@/lib/site-data";

/** What the page policy forbids or a formula must never carry. */
function expectSafe(markup: string): void {
  expect(markup).toMatch(/^<span class="katex(-display)?">/);
  expect(markup).toContain("<math");
  expect(markup).not.toMatch(/<script|<style|\sstyle=|\son[a-z]+=|javascript:|<a\s|href=/i);
}

describe("renderMath", () => {
  const formulas = registryData.models.flatMap((model) =>
    model.formula.map((latex, index) => ({ id: `${model.id} #${index + 1}`, latex })),
  );

  it("has formulas to render", () => {
    expect(formulas.length).toBeGreaterThanOrEqual(registryData.models.length);
  });

  it.each(formulas)("renders $id as MathML, inline and displayed", ({ latex }) => {
    expectSafe(renderMath(latex));
    expectSafe(renderMath(latex, true));
  });

  it("fails on a formula it cannot parse", () => {
    expect(() => renderMath(String.raw`\frac{1}{`)).toThrow(/KaTeX parse error/);
  });

  it.each([
    String.raw`\href{https://example.com}{x}`,
    String.raw`\url{javascript:alert(1)}`,
    String.raw`\includegraphics{x.png}`,
  ])("refuses the untrusted command in %s", (latex) => {
    expect(() => renderMath(latex)).toThrow(/is not allowed in a formula/);
  });

  it("refuses the HTML extensions in strict mode", () => {
    expect(() => renderMath(String.raw`\htmlStyle{color:red}{x}`)).toThrow(/strict mode/);
  });
});
