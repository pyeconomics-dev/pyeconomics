// tools/node/smoke.mjs
// The generated TypeScript client's smoke test (ci.yml's clients job): one run
// of a data-free model through the generated SDK, built to dist/ by `tsc`,
// against a local `pyeconomics serve`. It writes the answer's bytes as they
// came, and the job compares them with the Python API's Result.to_json().
//
//   node smoke.mjs http://127.0.0.1:8765 ts-run.json
import { writeFileSync } from "node:fs";

import { client } from "./dist/client.gen.js";
import { runFoundationsTimeValue } from "./dist/sdk.gen.js";

const [baseUrl, out] = process.argv.slice(2);
if (!baseUrl || !out) {
  console.error("usage: node smoke.mjs BASE_URL OUT_FILE");
  process.exit(2);
}
client.setConfig({ baseUrl });
const { data, response } = await runFoundationsTimeValue({
  body: {
    calculation: "present_value",
    rate: 0.05,
    periods: 10,
    future_value: 100,
  },
  parseAs: "arrayBuffer",
});
if (!response.ok) {
  console.error(`the run answered HTTP ${response.status}`);
  process.exit(1);
}
writeFileSync(out, Buffer.from(data));
console.log(`wrote ${data.byteLength} bytes to ${out}`);
