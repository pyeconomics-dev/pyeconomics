// web/src/types/plotly.d.ts
// The plotly.js package's prebuilt basic bundle, which ships no types of its
// own; src/lib/plotly.ts describes the part the calculator calls.
declare module "plotly.js/dist/plotly-basic.min.js" {
  const Plotly: unknown;
  export default Plotly;
}
