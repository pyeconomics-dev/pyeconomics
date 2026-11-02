// web/src/pages/og/[...slug].ts
// The Open Graph image of every generated page (ADR-0013 decision 2), drawn at
// build time by astro-og-canvas: 1200x630 PNG files at /og/<page path>.png
// (src/lib/pages.ts ogImagePath), each with the page's title and description
// on the brand's dark ground beside the bell-curve mark. The font is Noto Sans
// from the installed @fontsource package and the mark is the repository's own
// file, so the build fetches nothing from the network.
import { createRequire } from "node:module";
import { join } from "node:path";

import type { APIRoute, GetStaticPaths } from "astro";
import { generateOpenGraphImage } from "astro-og-canvas";

import { ogImagePath, sitePages, type SitePage } from "@/lib/pages";

const require = createRequire(join(process.cwd(), "package.json"));
const FONTS = [
  require.resolve("@fontsource/noto-sans/files/noto-sans-latin-400-normal.woff2"),
  require.resolve("@fontsource/noto-sans/files/noto-sans-latin-700-normal.woff2"),
];
const MARK = join(process.cwd(), "..", "docs", "_static", "brand", "pyeconomics-avatar.png");

/** The brand's ground and accent (src/styles/global.css --brand-ink, --brand). */
const INK: [number, number, number] = [30, 30, 30];
const BRAND: [number, number, number] = [99, 193, 255];

export const getStaticPaths = (() =>
  sitePages().map((page) => ({
    params: { slug: ogImagePath(page.path).slice("/og/".length) },
    props: { page },
  }))) satisfies GetStaticPaths;

export const GET: APIRoute<{ page: SitePage }> = async ({ props }) => {
  const image = await generateOpenGraphImage({
    title: props.page.title,
    description: props.page.description,
    bgGradient: [INK],
    border: { color: BRAND, width: 16, side: "inline-start" },
    padding: 64,
    logo: { path: MARK, size: [112] },
    fonts: FONTS,
    font: {
      title: { families: ["Noto Sans"], weight: "Bold", size: 64, color: [255, 255, 255] },
      description: { families: ["Noto Sans"], weight: "Normal", size: 32, color: [220, 220, 220], lineHeight: 1.4 },
    },
    format: "PNG",
  });
  return new Response(image, { headers: { "Content-Type": "image/png" } });
};
