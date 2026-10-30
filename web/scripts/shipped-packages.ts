// web/scripts/shipped-packages.ts
// A Vite plugin that records which npm packages the client bundle holds
// (Phase 5 Step 3's licence check of the shipped bundle). The site's
// `dependencies` are meant to be exactly what reaches browsers; this makes
// that checkable. In the client environment's build (Astro 7 builds through
// Vite's environment API) it reads every output chunk's modules, keeps those
// under node_modules/, and writes their package names, sorted, to
// .astro/shipped-packages.json; scripts/checks/web_licences.py --shipped then
// fails on a shipped package that is not in the production tree.
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import type { Plugin } from "vite";

export const SHIPPED = fileURLToPath(new URL("../.astro/shipped-packages.json", import.meta.url));

/** The npm package a bundled module came from, or null for the site's own code. */
export function packageOf(id: string): string | null {
  const parts = id.replaceAll("\\", "/").split("?")[0]?.split("/node_modules/") ?? [];
  if (parts.length < 2) return null;
  const [first = "", second = ""] = (parts.at(-1) ?? "").split("/");
  if (!first.startsWith("@")) return first || null;
  return second ? `${first}/${second}` : null;
}

/** Every package the modules of a bundle came from, sorted. */
export function packagesOf(moduleIds: Iterable<string>): string[] {
  const names = new Set<string>();
  for (const id of moduleIds) {
    const name = packageOf(id);
    if (name) names.add(name);
  }
  return [...names].sort();
}

export default function shippedPackages(): Plugin {
  return {
    name: "pyeconomics:shipped-packages",
    apply: "build",
    applyToEnvironment: (environment) => environment.name === "client",
    generateBundle(_options, bundle) {
      const ids = Object.values(bundle).flatMap((output) =>
        output.type === "chunk" ? Object.keys(output.modules) : [],
      );
      const document = { format: 1, packages: packagesOf(ids) };
      // A fixed path under web/.astro/.
      // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
      mkdirSync(dirname(SHIPPED), { recursive: true });
      // eslint-disable-next-line security/detect-non-literal-fs-filename -- the same fixed path
      writeFileSync(SHIPPED, `${JSON.stringify(document, null, 2)}\n`);
    },
  };
}
