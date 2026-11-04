# scripts/docs/export_wasm.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Export the in-browser examples with `marimo export html-wasm`.

Each notebook in docs/wasm/ becomes one page, and the pages share marimo's assets.
Every page names docs/wasm/pyodide-lock.json, copied beside it, so a reader's
browser loads only what that lockfile pins, by SHA-256 (`pin_wasm.py` explains
why). The export reads that lockfile too, so it needs no network.

The documentation build runs this (docs/_ext/in_browser.py); so can you:

    uv run --group docs python scripts/docs/export_wasm.py docs/_build/html/wasm
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess  # nosec B404 # runs marimo with a fixed argument list
import sys
from importlib.metadata import distribution
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[2]
NOTEBOOKS: Final = ROOT / "docs" / "wasm"
LOCKFILE: Final = "pyodide-lock.json"

#: marimo's runtime reads its lockfile from this element's data attributes.
_MOUNT: Final = '<marimo-wasm hidden=""></marimo-wasm>'
_PINNED: Final = (
    f'<marimo-wasm hidden="" data-pyodide-lockfile-url="./{LOCKFILE}"></marimo-wasm>'
)
#: A note marimo leaves for coding assistants, not for a reader.
_NOT_PUBLISHED: Final = "CLAUDE.md"


def page_name(notebook: Path) -> str:
    """Return the page a notebook exports to."""
    return f"{notebook.stem.replace('_', '-')}.html"


def pin(html: str) -> str:
    """Point a page at the pinned lockfile, or fail if marimo's page has changed."""
    if html.count(_MOUNT) != 1:
        message = f"expected one {_MOUNT} in marimo's page: read pin_wasm.py"
        raise SystemExit(message)
    return html.replace(_MOUNT, _PINNED)


def export(output: Path) -> list[Path]:
    """Export every notebook into ``output`` and return their pages."""
    environment = {
        **os.environ,
        "MARIMO_PYODIDE_LOCK_FILE": str(NOTEBOOKS / LOCKFILE),
    }
    pages = []
    for notebook in sorted(NOTEBOOKS.glob("*.py")):
        page = output / page_name(notebook)
        subprocess.run(  # noqa: S603  # nosec B603 # our notebooks, a fixed command
            [
                sys.executable,
                "-m",
                "marimo",
                "export",
                "html-wasm",
                str(notebook),
                "--output",
                str(page),
                "--mode",
                "run",
                "--no-show-code",
                "--no-sandbox",
                "--force",
            ],
            check=True,
            env=environment,
        )
        page.write_bytes(pin(page.read_text(encoding="utf-8")).encode("utf-8"))
        pages.append(page)
    (output / _NOT_PUBLISHED).unlink(missing_ok=True)
    shutil.copyfile(NOTEBOOKS / LOCKFILE, output / LOCKFILE)
    # marimo's frontend is redistributed in these assets, under its Apache-2.0.
    licence = distribution("marimo").read_text("licenses/LICENSE")
    if licence is None:
        message = (
            "marimo's wheel carries no licenses/LICENSE to publish with its assets"
        )
        raise SystemExit(message)
    (output / "marimo-LICENSE.txt").write_bytes(licence.encode("utf-8"))
    return pages


def main() -> int:
    """Export the notebooks into the directory named on the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="where the pages go")
    export(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
