// web/src/lib/build-info.ts
// The build's git commit for /version.json. The pages read no environment
// variable at build time but this one: GIT_SHA, which a deploy sets to the
// commit it builds; without it, the checkout's HEAD. (The post-build
// scripts/headers.ts reads SITE_FLAVOUR, the deployment the build is for.)
import { execFileSync } from "node:child_process";

const SHA = /^[0-9a-f]{40}$/;

/** Return the 40-character commit SHA the site is built from. */
export function gitSha(given: string | undefined = process.env.GIT_SHA): string {
  if (given !== undefined && given !== "") {
    if (!SHA.test(given)) {
      throw new Error("GIT_SHA must be a full 40-character lowercase commit SHA");
    }
    return given;
  }
  // A fixed command with fixed arguments, run without a shell.
  const head = execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf8" }).trim();
  if (!SHA.test(head)) {
    throw new Error("git rev-parse HEAD did not print a commit SHA; set GIT_SHA");
  }
  return head;
}
