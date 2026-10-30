// web/scripts/require-data.ts
// `npm run build` runs this first: the site builds only from the data
// scripts/web/export_site_data.py exports and the client generated from it,
// so a build without them stops here with the command that makes them,
// rather than deep inside Vite with an unresolved import.
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

const WEB = fileURLToPath(new URL("..", import.meta.url));

/** The files `npm run data` writes, relative to web/. */
export const REQUIRED = [
  "src/data/generated/registry.json",
  "src/data/generated/openapi.json",
  "src/data/generated/problems.json",
  "src/data/generated/sources.json",
  "src/data/generated/concepts.json",
  "src/client/index.ts",
] as const;

/** Return the required files missing under `root`. */
export function missing(root: string = WEB): string[] {
  // Fixed paths under the project root, never user input.
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see the line above
  return REQUIRED.filter((file) => !existsSync(`${root}/${file}`));
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const absent = missing();
  if (absent.length > 0) {
    process.stderr.write(
      `The site data is missing (${absent.join(", ")}).\n` +
        "Run `npm run data` in web/ first: it exports the registry, the OpenAPI document, the\n" +
        "error table, the sources and the concepts, and generates the TypeScript client.\n",
    );
    process.exit(1);
  }
}
