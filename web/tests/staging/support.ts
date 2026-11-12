// web/tests/staging/support.ts
// The deployed-site suite's fixtures: tests/e2e/support.ts's, plus one that
// keeps every run out of the site's analytics. A production build carries
// the analytics tracker (Phase 5 Step 15), which sends nothing while
// localStorage holds "umami.disabled". Set before any page script runs, it
// keeps a deploy's checks out of the Gate G2 counts, and the network
// assertions still hold the browser to the site's own origin: if storage
// refuses the item, the tracker's request reaches the network log and the
// privacy test fails, as it should.
import { expect, test as base } from "../e2e/support.ts";

export const test = base.extend<{ untracked: undefined }>({
  untracked: [
    async ({ page }, use) => {
      await page.addInitScript(() => {
        try {
          window.localStorage.setItem("umami.disabled", "1");
        } catch {
          // Storage refused: see above.
        }
      });
      await use(undefined);
    },
    { auto: true },
  ],
});

export { expect };
