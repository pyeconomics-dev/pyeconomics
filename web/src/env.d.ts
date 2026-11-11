// web/src/env.d.ts
// What import.meta.env holds beside Astro's own: the browser DSN and release a
// production build defines for the islands' error reporting (astro.config.ts;
// src/lib/error-reporting.ts). Every other build defines both as empty.
interface ImportMetaEnv {
  readonly PUBLIC_SENTRY_DSN?: string;
  readonly PUBLIC_SENTRY_RELEASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
