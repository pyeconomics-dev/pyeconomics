# scripts/docs/pin_wasm.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Write docs/wasm/pyodide-lock.json, which pins all the in-browser examples load.

An export of marimo 0.25.2 runs Pyodide 314.0.0 and asks wasm.marimo.app for its
package list. Neither suits these pages: that Pyodide bundles SciPy 1.17, below
the wheel's floor, and a list fetched from a third party decides what a reader's
browser runs. So the pages name this lockfile instead (`export_wasm.py`), served
from their own origin:

- the packages are those of the Pyodide `ci.yml`'s pyodide job proves, whose
  wheels carry the same `pyemscripten_2026_0` ABI as the interpreter marimo loads;
- what Pyodide lacks comes from PyPI, at the versions uv.lock holds;
- every entry names one URL and its SHA-256, which Pyodide checks, so `micropip`
  resolves the notebooks' pin of pyeconomics here and asks no package index.

The closure is pyeconomics, at the version the notebooks pin, and what marimo
itself loads in the browser. Run this by hand, with the network, after moving that
pin, marimo or Pyodide, and commit the result; the documentation build reads it
offline:

    uv run --no-config --group docs python scripts/docs/pin_wasm.py
"""

from __future__ import annotations

import json
import re
import tomllib
import urllib.request
from pathlib import Path
from typing import Any, Final

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT: Final = Path(__file__).resolve().parents[2]
NOTEBOOKS: Final = ROOT / "docs" / "wasm"
LOCKFILE: Final = NOTEBOOKS / "pyodide-lock.json"

#: The Pyodide of ci.yml's pyodide job (tests/docs/test_in_browser.py).
PYODIDE: Final = "314.0.7"
_PACKAGES: Final = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE}/full/"
_PYPI: Final = "https://pypi.org/pypi"

#: What marimo's worker loads before a notebook runs, and what its code imports.
_MARIMO_DEPENDS: Final = (
    "docutils",
    "jedi",
    "markdown",
    "micropip",
    "msgspec",
    "narwhals",
    "packaging",
    "pygments",
    "pymdown-extensions",
    "pyodide-http",
)
#: The browser's environment, for the markers of a wheel's requirements.
_BROWSER: Final = {
    "extra": "",
    "implementation_name": "cpython",
    "platform_system": "Emscripten",
    "python_full_version": "3.14.0",
    "python_version": "3.14",
    "sys_platform": "emscripten",
}
_PIN: Final = re.compile(r'^# dependencies = \["pyeconomics==([^"]+)"\]$', re.MULTILINE)


def _read(url: str) -> Any:  # noqa: ANN401 - parsed JSON
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310  # nosec B310 # fixed https URLs
        return json.load(response)


def _pinned_core() -> str:
    """Return the version every notebook pins; they must agree."""
    pins = {
        match
        for notebook in NOTEBOOKS.glob("*.py")
        for match in _PIN.findall(notebook.read_text(encoding="utf-8"))
    }
    if len(pins) != 1:
        message = f"the notebooks should pin one pyeconomics, not {sorted(pins)}"
        raise SystemExit(message)
    return pins.pop()


def _uv_locked() -> dict[str, str]:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    return {package["name"]: package.get("version", "") for package in lock["package"]}


def _from_pypi(name: str, version: str) -> tuple[dict[str, Any], list[str]]:
    """Return a pure wheel's entry and the requirements that apply in the browser."""
    release = _read(f"{_PYPI}/{name}/{version}/json")
    wheel = next(
        file
        for file in release["urls"]
        if file["filename"].endswith(("-py3-none-any.whl", "-py2.py3-none-any.whl"))
    )
    entry = {
        "depends": [],
        "file_name": wheel["url"],
        "imports": [],
        "install_dir": "site",
        "name": name,
        "package_type": "package",
        "sha256": wheel["digests"]["sha256"],
        "version": version,
    }
    required = [Requirement(text) for text in release["info"]["requires_dist"] or ()]
    return entry, [
        canonicalize_name(requirement.name)
        for requirement in required
        if requirement.marker is None or requirement.marker.evaluate(_BROWSER)
    ]


def build() -> dict[str, Any]:
    """Build the lockfile from Pyodide's own, PyPI and uv.lock."""
    pyodide = _read(f"{_PACKAGES}pyodide-lock.json")
    locked = _uv_locked()
    core = _pinned_core()
    packages: dict[str, dict[str, Any]] = {}

    marimo, _ = _from_pypi("marimo-base", locked["marimo"])
    # The worker asks for this key, and marimo's own lockfile names it so.
    marimo |= {"depends": list(_MARIMO_DEPENDS), "name": "marimo"}
    packages["marimo-base"] = marimo
    pending = [*_MARIMO_DEPENDS, "pyeconomics"]
    while pending:
        name = canonicalize_name(pending.pop())
        if name in packages:
            continue
        if name in pyodide["packages"]:
            entry = dict(pyodide["packages"][name])
            entry["file_name"] = _PACKAGES + entry["file_name"]
            depends = list(entry["depends"])
        else:
            entry, depends = _from_pypi(
                name, core if name == "pyeconomics" else locked[name]
            )
            entry["depends"] = depends
        packages[name] = entry
        pending.extend(depends)
    return {"info": pyodide["info"], "packages": packages}


def main() -> int:
    """Write the lockfile."""
    text = json.dumps(build(), indent=1, sort_keys=True) + "\n"
    LOCKFILE.write_bytes(text.encode("utf-8"))
    print(f"{LOCKFILE.relative_to(ROOT).as_posix()}: pinned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
