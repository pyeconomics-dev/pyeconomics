# Exports and reproducibility bundles

Any result, batch of results or data frame can be written in a format other
software reads: CSV, XLSX, Parquet, Arrow or JSON. Each export carries the
attribution and every required notice of the data it holds ({doc}`notices`),
and the manifest that says how the result was produced ({doc}`results`). A
*reproducibility bundle* goes one step further: one zip file from which anyone
can check a result and rerun it.

```python
import io
import tempfile
from pathlib import Path

import pandas as pd

from pyeconomics import run
from pyeconomics.exports import FORMATS, export, export_bytes

inputs = {"calculation": "irr", "cash_flows": [-100, 30, 40, 50]}
result = run("foundations.time_value", inputs)
assert FORMATS == ("csv", "xlsx", "parquet", "arrow", "json")

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "irr.csv"
    export(result, "csv", path)
    frame = pd.read_csv(path, comment="#", float_precision="round_trip")

assert frame.loc[0, "outputs.irr"] == result.outputs.irr
assert frame.loc[0, "inputs.cash_flows"] == "[-100,30,40,50]"
assert export_bytes(result, "json") == result.to_json().encode()
```

`export(value, format, target)` writes to a path or a binary stream, and
`export_bytes(value, format)` returns the bytes. The value is a `Result`, a
`BatchResult`, a `Series` or `Table`, what `data.get` resolved (the frame with
its source records) or identifier `Records`.

## The formats

| Format | What it holds |
|--------|---------------|
| `csv` | A `#` metadata block, then a header row and one row per result, observation or record (RFC 4180, UTF-8, LF line ends) |
| `xlsx` | A `data` sheet, and a `manifest` sheet listing the attributions and notices first, then the manifest's fields and each data record |
| `parquet` | The same columns, with the manifest and attributions in the schema metadata; needs pyarrow |
| `arrow` | An Arrow IPC file (Feather version 2) with the same metadata; needs pyarrow |
| `json` | Canonical JSON with the manifest embedded: a result's own canonical bytes |

A result's columns are those of `Result.to_pandas()`: `inputs.<field>`, then
`outputs.<field>`, then `result_sha256`, one row per run. A frame's are `date`,
then `realtime_start` and `realtime_end` when it carries vintages, then `value`
or the table's columns. A missing value is an empty cell, a date is its ISO 8601
text and an array its canonical JSON (in Parquet and Arrow it stays a list). A
number is written as its shortest round-trip text, so it reads back equal; pass
`float_precision="round_trip"` to `pandas.read_csv`, whose default parser can
miss a value's last bit.

## The CSV metadata block

A CSV export starts with one `# label: text` line per item: the pyeconomics
version, the model and its version (or the data's provider and id), the hashes,
then every attribution, notice and terms page of the data:

```text
# pyeconomics: 1.0.0b1
# data: fred:UNRATE
# title: Unemployment Rate
# frame_sha256: 6f1c…
# attribution: Source: Federal Reserve Bank of St. Louis, FRED®.
# notice: This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.
# terms: https://fred.stlouisfed.org/legal/
"date","value"
"2024-01-31",0.037
```

`pandas.read_csv(path, comment="#")` skips the block and reads the rest; a line
read on its own is split at the first `": "`. The block is part of the data's
terms: keep it with the data, or show its attributions and notices wherever the
data appears.

## Formula escaping

A spreadsheet runs a cell that starts with `=`, `+`, `-` or `@` as a formula, so
a hostile text could run code when a CSV is opened. Every text cell that starts
with one of those characters, a tab or a carriage return is written with a
leading `'`, in CSV and XLSX alike; numbers are never escaped, so `-3` stays a
number while the text `"-3"` becomes `'-3`. XLSX stores every string as a string
and never a formula, and every CSV text cell is quoted.

```python
from pyeconomics.exports.layout import escape_text

assert escape_text("=HYPERLINK(1)") == "'=HYPERLINK(1)"
assert escape_text("-0.5") == "'-0.5"
assert escape_text("net debt") == "net debt"
```

An XLSX cell holds at most 32,767 characters, so a longer text (a long array's
JSON, say) is refused with exit code 3 rather than cut: export it as CSV,
Parquet, Arrow or JSON instead. openpyxl writes each sheet to a temporary file of
its own, owner-only, which it deletes as soon as the workbook is saved.

## Parquet and Arrow

pyarrow is never a dependency of pyeconomics, not even through an extra; install
it beside pyeconomics (`pip install pyarrow`) to write Parquet or Arrow. Without
it, both raise `MissingOptionalDependencyError` naming pyarrow (exit code 8 on
the command line). The schema metadata holds three keys:

| Key | Value |
|-----|-------|
| `pyeconomics.manifest` | The manifest as canonical JSON (the key `Result.to_arrow()` uses) |
| `pyeconomics.attributions` | The attributions and notices, a canonical JSON list |
| `pyeconomics.version` | The pyeconomics version that wrote the file |

```python
import json

import pyarrow.parquet as pq

data = export_bytes(result, "parquet")
metadata = pq.read_schema(io.BytesIO(data)).metadata
manifest = json.loads(metadata[b"pyeconomics.manifest"])
assert manifest["result_sha256"] == result.manifest.result_sha256
assert json.loads(metadata[b"pyeconomics.attributions"]) == []
```

## Reproducibility bundles

`write_bundle(result, target, request=None)` writes a zip of eight members:

| Member | What it holds |
|--------|---------------|
| `result.json` | The result's canonical bytes |
| `inputs.json` | The validated inputs the model ran on |
| `request.json` | The bind request (`as_of`, `vintage`, `profile`, `concepts`, `parameters`) of a run that read data, else `null` |
| `manifest.json` | The manifest: versions, data records and hashes |
| `ATTRIBUTION.txt` | The attribution, notice and terms page of each source |
| `requirements.txt` | `pyeconomics==<version>`, with the extras the model and its data need |
| `reproduce.py` | Reruns the model and compares `result_sha256` |
| `README.txt` | What the members are, and how to check and rerun them |

The zip is deterministic: every member stored (not compressed), in sorted order,
dated 1980-01-01 and with the same permissions, so equal results give equal
bytes on every operating system.

```python
import subprocess
import sys
import zipfile

from pyeconomics.exports import check_bundle, write_bundle

with tempfile.TemporaryDirectory() as directory:
    bundle = Path(directory) / "irr.zip"
    write_bundle(result, bundle)
    report = check_bundle(bundle)
    with zipfile.ZipFile(bundle) as archive:
        archive.extractall(Path(directory) / "irr")
    script = Path(directory) / "irr" / "reproduce.py"
    done = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, check=False
    )

assert report.result_sha256 == result.manifest.result_sha256
assert done.returncode == 0
assert "identical to result.json" in done.stdout
```

`reproduce.py` uses only the standard library until it imports pyeconomics. It
checks that the installed version is the recorded one (exit code 2, with the
install command, when it is not), reruns `pyeconomics.run(model_id, inputs)` and
compares the rerun's `result_sha256` with the recorded one: exit code 0 when
they agree, 1 when not. It also says whether the rerun's bytes equal
`result.json`, or which parts of the manifest differ: the dependency versions of
another environment, or the data records, which a rerun from the recorded inputs
never reads. A run that read revised data carries the `revised_data` warning its
bind added; the script adds that recorded warning back before it compares the
hashes, and says so. `--out FILE` writes the rerun's canonical bytes.

`python reproduce.py --refetch` binds the model's data again from
`request.json`, at the recorded date, vintage policy and profile, and reports
for each bound field whether the value read now agrees with the recorded input,
labelling revised data. It needs the network and the providers' keys, as the
first run did.

```{warning}
`reproduce.py` is a program. Read it before you run a bundle someone else
made, as you would any script. `pyeconomics bundle check` verifies a bundle
without running anything from it.
```

## Checking a bundle

`check_bundle(path)` (and `pyeconomics bundle check FILE`) verifies a bundle
while executing nothing from it. Before it reads any member it refuses an
archive larger than 64 MiB, more than 64 members, a member name with a path
separator or `..`, a member the format does not have or the lack of one it
has, and a compressed or encrypted member. It then reads the four JSON members
only, strictly (no repeated key, no NaN), and checks that each is canonical
JSON, that the result's `result_sha256` and `inputs_sha256` are the hashes of
its body and inputs, and that `inputs.json` and `manifest.json` are the
result's own. It never reads `reproduce.py`. A failure says what is wrong and
exits with code 3.

## On the command line

`models run` and `data get` take `--format csv`, `xlsx`, `parquet` or `arrow`
beside `json` and `table` ({doc}`cli`). A binary format (`xlsx`, `parquet`,
`arrow`) is written to standard output only when it is not a terminal: name a
file with `--out`, redirect the output or pipe it.

```text
pyeconomics models run foundations.time_value --calculation irr --cash-flows "[-100, 30, 40, 50]" --format csv
pyeconomics models run foundations.time_value --calculation irr --cash-flows "[-100, 30, 40, 50]" --format parquet > irr.parquet
pyeconomics data get fred:UNRATE --format xlsx --out unrate.xlsx
pyeconomics models run macro.recession_probability --as-of 2024-06-28 --bundle recession.zip
pyeconomics bundle check recession.zip
```

`models run ID --batch FILE` runs the model once per row of a file: CSV with a
header row of field names (an empty cell leaves that field out), or JSON Lines
with one object per line. The file is read within the 16 MiB input limit and a
batch holds at most 100,000 rows; `--format` then writes the batch, one row per
run.

```text
pyeconomics models run foundations.time_value --batch rows.csv --format csv --out results.csv
```

No export or bundle holds a key, a file path, a host name or anything else of
the machine that wrote it: the manifest records versions, data records and
hashes only.
