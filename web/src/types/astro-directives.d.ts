// web/src/types/astro-directives.d.ts
// The site's own client directive (src/directives/interaction.ts), for the
// type checker.
import "astro";

declare module "astro" {
  interface AstroClientDirectives {
    "client:interaction"?: boolean;
  }
}
