// web/src/pages/version.json.ts
// /version.json (ADR-0013 decision 2): the pyeconomics version the site data
// was exported from and the commit the site was built from. Prerendered to a
// file at build time, like every route.
import type { APIRoute } from "astro";

import { gitSha } from "@/lib/build-info";
import { version } from "@/lib/site-data";

export const GET: APIRoute = () =>
  new Response(JSON.stringify({ pyeconomics: version, git_sha: gitSha() }), {
    headers: { "Content-Type": "application/json" },
  });
