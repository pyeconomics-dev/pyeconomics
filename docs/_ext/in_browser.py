# docs/_ext/in_browser.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Export the in-browser examples beside the page that lists them.

After an HTML build, scripts/docs/export_wasm.py writes docs/wasm/'s notebooks
into the output's `wasm/` directory, so they are served as static files and
Sphinx never reads them.
"""

from __future__ import annotations

import subprocess  # nosec B404 # runs our own script with a fixed argument list
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from sphinx.application import Sphinx

_EXPORT: Final = Path(__file__).resolve().parents[2] / "scripts/docs/export_wasm.py"


def _export(app: Sphinx, exception: Exception | None) -> None:
    if exception is None and app.builder.format == "html":
        subprocess.run(  # noqa: S603  # nosec B603 # our script, the build's directory
            [sys.executable, str(_EXPORT), str(Path(app.outdir) / "wasm")],
            check=True,
        )


def setup(app: Sphinx) -> dict[str, Any]:
    """Export the notebooks when the build finishes."""
    app.connect("build-finished", _export)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
