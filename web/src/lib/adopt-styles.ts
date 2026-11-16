// web/src/lib/adopt-styles.ts
// Adopting an island's own stylesheet without disturbing the page's
// (Phase 5 Step 17). The calculator's form brings calculator.css, Tailwind's
// utilities for its own classes, as a constructed stylesheet, and a page
// adopts it after every stylesheet it links. A utility both sheets hold
// (`.hidden`, `.flex`) then came later in the cascade than the page's own
// responsive rules (`lg:block`), and won: once a calculator loaded, the
// header's navigation and domain row vanished on wide screens (found by the
// dogfooding harness, which scrolls every island into view). So a rule the
// page's stylesheets already hold is dropped from the adopted sheet before it
// is adopted: the page keeps its own order, and the island adds only what the
// page lacks. Constructing a sheet through the CSS object model needs no
// 'unsafe-inline' (ADR-0013 decision 9).

/** Every style rule's selector in a list of rules, through @layer, @media and @supports. */
function selectors(rules: CSSRuleList, found: Set<string>): Set<string> {
  for (const rule of Array.from(rules)) {
    if (rule instanceof CSSStyleRule) found.add(rule.selectorText);
    else if ("cssRules" in rule) selectors((rule as CSSGroupingRule).cssRules, found);
  }
  return found;
}

/** Delete, from a sheet's rules, every style rule whose selector the page already has. */
function prune(rules: CSSRuleList, owner: CSSStyleSheet | CSSGroupingRule, present: ReadonlySet<string>): void {
  for (let index = rules.length - 1; index >= 0; index -= 1) {
    const rule = rules.item(index);
    if (rule instanceof CSSStyleRule) {
      if (present.has(rule.selectorText)) owner.deleteRule(index);
    } else if (rule && "cssRules" in rule) {
      prune((rule as CSSGroupingRule).cssRules, rule as CSSGroupingRule, present);
    }
  }
}

/** Adopt `text` as a stylesheet, less the rules the document's stylesheets already hold. */
export function adoptStyles(text: string, root: Document = document): CSSStyleSheet {
  const present = new Set<string>();
  for (const sheet of Array.from(root.styleSheets)) {
    try {
      selectors(sheet.cssRules, present);
    } catch {
      // A sheet whose rules cannot be read holds nothing to keep in order.
    }
  }
  const sheet = new CSSStyleSheet();
  sheet.replaceSync(text);
  prune(sheet.cssRules, sheet, present);
  root.adoptedStyleSheets = [...root.adoptedStyleSheets, sheet];
  return sheet;
}
