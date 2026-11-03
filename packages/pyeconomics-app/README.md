# pyeconomics-app

The pyeconomics web app, built: every model page, calculator, the data explorer
and search, as static files. Install it through the library's extra, which pins
it to the library's own version:

```console
pip install "pyeconomics[app]"
pyeconomics serve
```

Then open <http://127.0.0.1:8000>. The local server answers only on this
machine, reads every data source your installation can reach, with your own keys
where a source needs one, and offers the whole data catalog. It loads no
analytics and no error tracking.

This package holds only the static site and one function, `site_path()`, which
`pyeconomics serve` reads; it has no dependencies and runs no code of its own.
The library, its documentation and its source are at
<https://github.com/pyeconomics-dev/pyeconomics>.

Licensed under the Apache License, Version 2.0 (see LICENSE and NOTICE).
