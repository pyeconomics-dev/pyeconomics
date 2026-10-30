// web/src/lib/math.ts
// Formulas rendered at build time (ADR-0013 decision 9): KaTeX writes MathML
// only, which carries no script and no inline style, so the page policy needs
// no 'unsafe-inline'. A formula KaTeX cannot parse fails the build rather than
// shipping red error text. No command is trusted: KaTeX's `trust: false` would
// still ship an untrusted command (\href, \url, \includegraphics, \htmlId) as
// red text, so the trust check refuses each one by failing the build instead.
import katex from "katex";

/** Refuse every command KaTeX asks to trust. */
function refuse(context: { command: string }): never {
  throw new Error(`${context.command} is not allowed in a formula: no command is trusted`);
}

/** Render one LaTeX formula as MathML markup. */
export function renderMath(latex: string, display = false): string {
  return katex.renderToString(latex, {
    displayMode: display,
    output: "mathml",
    throwOnError: true,
    trust: refuse,
    strict: "error",
  });
}
