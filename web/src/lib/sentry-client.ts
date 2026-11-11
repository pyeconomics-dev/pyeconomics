// web/src/lib/sentry-client.ts
// The part of @sentry/browser the islands' error reporting uses, imported by
// name so the bundler keeps nothing else: no replay, feedback or tracing code
// ships. src/lib/error-reporting.ts imports this module only on an island's
// first report (Phase 5 Step 14).
export { captureException, dedupeIntegration, init, linkedErrorsIntegration } from "@sentry/browser";
