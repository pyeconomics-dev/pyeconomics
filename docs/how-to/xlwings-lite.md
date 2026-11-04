# Use pyeconomics inside xlwings Lite

[xlwings Lite](https://lite.xlwings.org/) is an Excel add-in that runs Python
inside the workbook, with [Pyodide](https://pyodide.org/) (Python compiled to
WebAssembly) and no local install. pyeconomics runs there too, so a cell can call
a model, or a script can read values from a sheet and write results back.

```{warning}
**No live data in the add-in.** The data layer's network transport and its
cache have not been proven under Pyodide
([#114](https://github.com/pyeconomics-dev/pyeconomics/issues/114),
[#116](https://github.com/pyeconomics-dev/pyeconomics/issues/116)). Until those
close, use data-free models with values from the sheet. Live data needs a local
install of pyeconomics: {doc}`pandas` and {doc}`excel` show how to get it into a
workbook from there.
```

## Install it

1. In the add-in, open **Settings > Workbook > Pyodide Version** and choose
   314 or later. pyeconomics needs NumPy 2.4 and pandas 3.0, which only those
   versions provide.
2. Add this line to `requirements.txt`, beside what is already there:

   ```text
   pyeconomics>=1.0.0b1,<2
   ```

Name the range, as xlwings Lite advises, rather than an exact version: it records
the exact versions it installed in `requirements-pinned.txt` for you. Do not write
a bare `pyeconomics`: until 1.0.0 is released that picks 0.2.6, which does not
install there. A lower bound that names a pre-release is what lets the installer
take one.

This installs the core wheel, with every data-free model but the ones that need
an extra. The OLS, GARCH and time-series models need the `econometrics` extra, and
stop with an error that names it.

## Call a model from a cell

A function marked `@func` becomes an Excel function. Put this in `main.py`:

```python
from xlwings import func

import pyeconomics


@func
def present_value(rate: float, periods: float, future_value: float) -> float:
    """Return the present value of a future amount."""
    result = pyeconomics.run(
        "foundations.time_value",
        calculation="present_value",
        rate=rate,
        periods=periods,
        future_value=future_value,
    )
    return result.outputs.present_value
```

% invisible-code-block: python
%
% assert round(present_value(0.05, 10.0, 100.0), 2) == 61.39

Then, in any cell, `=PRESENT_VALUE(0.05, 10, 100)` answers 61.39. A cell holds a
percentage as a decimal, which is how pyeconomics reads a rate: `5%` and `0.05`
are the same value.

## Read values from a sheet

A function marked `@script` gets the whole workbook, so it can read a block of
inputs and write its results elsewhere. This one takes four values from a sheet
named `Rule` and writes the rate the Taylor rule prescribes:

```python
import xlwings as xw
from xlwings import script

import pyeconomics


@script
def taylor_rule(book: xw.Book) -> None:
    """Write the Taylor (1993) rule's rate for the values on the sheet."""
    sheet = book.sheets["Rule"]
    inflation, unemployment, natural, neutral = sheet["B1:B4"].value
    result = pyeconomics.run(
        "macro.policy_rule",
        calculation="taylor_1993",
        inflation=inflation,
        unemployment=unemployment,
        natural_unemployment=natural,
        neutral_real_rate=neutral,
    )
    sheet["B6"].value = result.outputs.prescribed_rate
```

% invisible-code-block: python
%
% class Cell:
%     def __init__(self, value=None):
%         self.value = value
%
% class Book:
%     def __init__(self):
%         self.cells = {
%             "B1:B4": Cell([0.03, 0.04, 0.042, 0.01]),
%             "B6": Cell(),
%         }
%         self.sheets = {"Rule": self.cells}
%
% book = Book()
% taylor_rule(book)
% assert round(book.cells["B6"].value, 4) == 0.047

With 3% inflation, 4% unemployment, a 4.2% natural rate and a 1% neutral real
rate, cell `B6` shows 4.7%.

These numbers are yours, so they carry no source's terms. If they came from a data
source, its attribution and notices still belong beside them.

## What to expect

- **Never put a key in a workbook or in `main.py`.** A workbook travels. No
  data-free model needs one.
- **The last bit of a float can differ between platforms.** Each has its own math
  library, and Pyodide's is one more: the present value above is
  `61.39132535407593` here and on Linux, and `61.391325354075946` on Windows, so
  the two `result_sha256` values differ. Compare numbers with a tolerance, not
  exactly.
- **Each model runs on its own.** The add-in supports no threads or extra
  processes, and no model needs them.
