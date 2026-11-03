// web/src/lib/parse-file.ts
// How the calculator reads a user's file (Phase 5 Step 9; ADR-0013 decision
// 11): in a Web Worker of its own (src/workers/parse-file.ts), served from
// the site's origin as worker-src 'self' allows, one worker per file,
// terminated once it answers or after 30 seconds. The file goes to the worker
// by structured clone and comes back as cells; it is never sent anywhere.
import { MAX_FILE_BYTES, type ParsedRows } from "@/lib/user-data";
import type { ParseReply } from "@/workers/parse-file";

/** How long a file may take to read before the worker is stopped. */
export const PARSE_TIMEOUT_MS = 30_000;

/** Read a CSV or XLSX file's cells in a worker, at most `maxRows` data rows. */
export function parseUserFile(file: File, maxRows: number): Promise<ParsedRows> {
  if (file.size > MAX_FILE_BYTES) return Promise.reject(new Error("the file is larger than 5 MB"));
  return new Promise((resolve, reject) => {
    const worker = new Worker(new URL("../workers/parse-file.ts", import.meta.url), { type: "module" });
    const stop = (error?: Error, parsed?: ParsedRows) => {
      clearTimeout(timer);
      worker.terminate();
      if (parsed) resolve(parsed);
      else reject(error ?? new Error("the file could not be read"));
    };
    const timer = setTimeout(() => stop(new Error("reading the file took too long")), PARSE_TIMEOUT_MS);
    worker.addEventListener("message", (event: MessageEvent<ParseReply>) => {
      const reply = event.data;
      if (reply.ok) stop(undefined, reply.parsed);
      else stop(new Error(reply.reason));
    });
    worker.addEventListener("error", () => stop(new Error("the file reader stopped")));
    worker.postMessage({ file, maxRows });
  });
}
