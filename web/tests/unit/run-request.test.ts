// web/tests/unit/run-request.test.ts
// The calculator's request builder (src/lib/run-request.ts): the route, the
// query (a profile and date for live data, a format for a download), the
// inputs' JSON with Content-Type application/json through the generated
// client, and the answer kept byte for byte, problems and all, with its
// download name and Retry-After.
import { describe, expect, it } from "vitest";

import { filenameOf, runBody, runModel, runPath, runQuery } from "@/lib/run-request";

/** A fetch that records the request and answers what it is given. */
function answering(body: BodyInit, init: ResponseInit = {}) {
  const seen: Request[] = [];
  const fetch = (async (input: RequestInfo | URL, init2?: RequestInit) => {
    seen.push(new Request(input, init2));
    return new Response(body, init);
  }) as typeof globalThis.fetch;
  return { fetch, seen };
}

describe("the request builder", () => {
  it("names a model's run route and refuses anything that is not a model id", () => {
    expect(runPath("fixed_income.duration")).toBe("/v1/models/fixed_income.duration/run");
    for (const bad of ["fixed_income", "../x.y", "a.b/c", "A.b"]) expect(() => runPath(bad)).toThrow(/not a model id/);
  });

  it("asks for a profile, a date and a format only when given, and checks each", () => {
    expect(runQuery()).toEqual({});
    expect(runQuery({ format: "json" })).toEqual({});
    expect(runQuery({ profile: "default", asOf: "2026-03-15", format: "csv" })).toEqual({
      profile: "default",
      as_of: "2026-03-15",
      format: "csv",
    });
    expect(runQuery({ asOf: "2026-03-15" })).toEqual({});
    expect(() => runQuery({ profile: "x&y" })).toThrow(/profile/);
    expect(() => runQuery({ profile: "default", asOf: "15/03/2026" })).toThrow(/date/);
    expect(() => runQuery({ format: "pdf" as never })).toThrow(/run format/);
  });

  it("posts the inputs' JSON, and reads a download's name safely", () => {
    expect(runBody({ rate: 0.05, flag: true, none: null })).toBe('{"rate":0.05,"flag":true,"none":null}');
    expect(filenameOf('attachment; filename="fixed_income.duration.csv"')).toBe("fixed_income.duration.csv");
    expect(filenameOf('attachment; filename="../../etc/passwd"')).toBe("etc_passwd");
    expect(filenameOf(null)).toBeNull();
  });
});

describe("runModel", () => {
  it("posts to the run route with Content-Type application/json and keeps the bytes as received", async () => {
    const body = new TextEncoder().encode('{"model_id":"a.b","outputs":{"x":1.0}}');
    const { fetch, seen } = answering(body, { status: 200, headers: { "Content-Type": "application/json" } });
    const answer = await runModel("a.b", { rate: 0.05 }, { profile: "default" }, { baseUrl: "http://127.0.0.1:1", fetch });
    const [request] = seen;
    expect(request?.method).toBe("POST");
    expect(request?.url).toBe("http://127.0.0.1:1/v1/models/a.b/run?profile=default");
    expect(request?.headers.get("Content-Type")).toBe("application/json");
    expect(await request?.text()).toBe('{"rate":0.05}');
    expect(answer.ok).toBe(true);
    expect(answer.bytes).toEqual(body);
    expect(answer.filename).toBeNull();
  });

  it("answers a problem with its status, bytes and Retry-After", async () => {
    const problem = '{"status":429,"title":"Too many requests","type":"https://pyeconomics.dev/problems/too-many-requests"}';
    const { fetch } = answering(problem, {
      status: 429,
      headers: { "Content-Type": "application/problem+json", "Retry-After": "7" },
    });
    const answer = await runModel("a.b", {}, {}, { baseUrl: "http://127.0.0.1:1", fetch });
    expect(answer.ok).toBe(false);
    expect(answer.status).toBe(429);
    expect(answer.retryAfter).toBe(7);
    expect(new TextDecoder().decode(answer.bytes)).toBe(problem);
  });

  it("names a download from its Content-Disposition", async () => {
    const { fetch, seen } = answering("a,b\n", {
      status: 200,
      headers: { "Content-Type": "text/csv", "Content-Disposition": 'attachment; filename="a.b.csv"' },
    });
    const answer = await runModel("a.b", {}, { format: "csv" }, { baseUrl: "http://127.0.0.1:1", fetch });
    expect(seen[0]?.url).toBe("http://127.0.0.1:1/v1/models/a.b/run?format=csv");
    expect(answer.filename).toBe("a.b.csv");
  });
});
