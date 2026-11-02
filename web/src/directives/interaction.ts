// web/src/directives/interaction.ts
// `client:interaction`, a client directive of the site's own (Phase 5 Step
// 7): it hydrates an island the first time a visitor focuses it, points at
// it or touches it, and never before. The header's search box uses it, so no
// page loads a script until someone reaches for search; the island's
// server-rendered form works in the meantime. Astro inlines this directive
// into each page that uses it and hashes it into the page's policy, as it
// does its own directives.
import type { ClientDirective } from "astro";

const EVENTS = ["focusin", "pointerover", "touchstart"] as const;

const interaction: ClientDirective = (load, _options, element) => {
  let started = false;
  const hydrate = (): void => {
    if (started) return;
    started = true;
    for (const name of EVENTS) element.removeEventListener(name, hydrate);
    void load().then((run) => run());
  };
  for (const name of EVENTS) element.addEventListener(name, hydrate, { passive: true });
};

export default interaction;
