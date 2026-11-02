// web/tests/parity/serve.ts
// The web parity suite's global setup (vitest.parity.config.ts): a real
// `pyeconomics serve` from the locked environment with every extra, on a free
// loopback port, which every test reaches through `inject("api")`. It is
// stopped, with its whole process tree, when the suite ends.
import { execFileSync, spawn, type ChildProcess } from "node:child_process";
import { createServer } from "node:net";
import { fileURLToPath } from "node:url";

import type { TestProject } from "vitest/node";

const WEB = fileURLToPath(new URL("../..", import.meta.url));

declare module "vitest" {
  export interface ProvidedContext {
    api: string;
  }
}

async function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      server.close(() => (typeof address === "object" && address ? resolve(address.port) : reject(new Error("no port"))));
    });
  });
}

function stop(server: ChildProcess): void {
  if (server.pid === undefined || server.exitCode !== null) return;
  if (process.platform === "win32") {
    // A fixed command; the pid is our own child's.
    execFileSync("taskkill", ["/pid", String(server.pid), "/T", "/F"], { stdio: "ignore" });
  } else {
    process.kill(-server.pid, "SIGTERM");
  }
}

export default async function setup(project: TestProject): Promise<() => void> {
  const port = await freePort();
  const origin = `http://127.0.0.1:${String(port)}`;
  const server = spawn(
    "uv",
    ["run", "--project", "..", "--locked", "--all-extras", "pyeconomics", "serve", "--port", String(port), "--workers", "2"],
    // Its own process group, so stop() can end the server with its workers.
    { cwd: WEB, stdio: ["ignore", "ignore", "pipe"], detached: process.platform !== "win32" },
  );
  // Its log (a line per request) is kept, and shown only if it fails to start.
  let log = "";
  server.stderr?.on("data", (chunk: Buffer) => {
    log = `${log}${chunk.toString("utf8")}`.slice(-8000);
  });
  const deadline = Date.now() + 300_000;
  for (;;) {
    if (server.exitCode !== null) throw new Error(`pyeconomics serve exited with ${String(server.exitCode)}:\n${log}`);
    try {
      if ((await fetch(`${origin}/healthz`)).ok) break;
    } catch {
      // Not listening yet.
    }
    if (Date.now() > deadline) {
      stop(server);
      throw new Error(`pyeconomics serve did not answer on ${origin}`);
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  project.provide("api", origin);
  return () => stop(server);
}
