# In-browser examples

These pages run pyeconomics entirely in your browser, and there is nothing to
install. Python and the library load as WebAssembly, every number is worked out on
your own machine, and nothing you type leaves the page. Change an input and the
answer follows.

- <a href="time-value.html">The time value of money</a>: discount a sum and a
  stream of payments.
- <a href="bond-price-duration.html">A bond's price and duration</a>: see how a
  bond's price answers to its yield.
- <a href="mean-variance-frontier.html">A mean-variance frontier</a>: change what
  you assume about three assets and watch the frontier move.

The first visit downloads about 50 MB, because it brings a whole Python and its
numerical libraries into the browser, and your browser keeps that for next time.
Allow a little while, and use a desktop browser if you can.

## What these pages load

They load what is pinned and nothing else:

- the Pyodide runtime, which is Python compiled to WebAssembly, at a fixed version,
  from jsDelivr;
- Pyodide's packages, also from jsDelivr, and the `pyeconomics` wheel and the other
  pure-Python wheels it needs, from PyPI. Each one's SHA-256 is listed in the
  page's lockfile and checked as it arrives, so a changed file is refused.

They use models that need no data: every input is a number you type, so these pages
call no data source and hold no key. They run the published `pyeconomics` release
named at the top of each notebook, which can be a little behind this documentation.
To run a model on live data, {doc}`install the library </tutorials/install>`.

The pages are [marimo](https://marimo.io) notebooks, and the source of each is in
the repository's
[`docs/wasm/`](https://github.com/pyeconomics-dev/pyeconomics/tree/main/docs/wasm)
directory. marimo's frontend ships with these pages under its
<a href="marimo-LICENSE.txt">Apache-2.0 licence</a>.

These examples are educational, not investment advice.
