# tests/checks/test_web_licences.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for scripts/checks/web_licences.py, the web app's licence check."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "checks" / "web_licences.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("web_licences_check", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


web_licences = load_script()


def lock(**packages: dict[str, Any]) -> dict[str, Any]:
    """A lockfile with the build tools present and the given packages."""
    entries: dict[str, Any] = {
        "": {"name": "pyeconomics-web"},
        "node_modules/astro": {"version": "7.4.4", "license": "MIT", "dev": True},
        "node_modules/@astrojs/react": {
            "version": "7.1.2",
            "license": "MIT",
            "dev": True,
        },
    }
    entries.update({f"node_modules/{name}": entry for name, entry in packages.items()})
    return {"lockfileVersion": 3, "packages": entries}


@pytest.mark.parametrize(
    ("expression", "allowed"),
    [
        ("MIT", True),
        ("0BSD", True),
        ("(MIT OR Apache-2.0)", True),
        ("MIT OR GPL-3.0-only", True),
        ("MIT AND BSD-3-Clause", True),
        ("MIT AND GPL-3.0-only", False),
        ("MPL-2.0", False),
        ("CC-BY-4.0", False),
        ("Apache-2.0 WITH LLVM-exception", False),
        ("(MIT OR (Apache-2.0 AND LGPL-3.0-or-later))", True),
    ],
)
def test_spdx_expressions(expression: str, *, allowed: bool) -> None:
    assert web_licences.spdx_allowed(expression) is allowed


@pytest.mark.parametrize(
    "expression", ["", "MIT OR", "(MIT", "MIT)", "SEE LICENSE IN LICENSE.md"]
)
def test_spdx_refuses_what_does_not_parse(expression: str) -> None:
    with pytest.raises(ValueError, match="in "):
        web_licences.spdx_allowed(expression)


def test_package_names_follow_nesting() -> None:
    assert web_licences.package_name("node_modules/react") == "react"
    assert web_licences.package_name("node_modules/a/node_modules/@x/y") == "@x/y"


def test_production_tree_omits_dev_and_links_but_keeps_dev_optional() -> None:
    found = web_licences.production(
        lock(
            react={"version": "19.3.1", "license": "MIT"},
            vitest={"version": "5.0.5", "license": "MIT", "dev": True},
            csstype={"version": "3.2.3", "license": "MIT", "devOptional": True},
            local={"link": True},
        )
    )
    assert sorted(web_licences.package_name(path) for path in found) == [
        "csstype",
        "react",
    ]


def test_production_tree_needs_a_modern_lockfile() -> None:
    with pytest.raises(ValueError, match="lockfile version"):
        web_licences.production({"lockfileVersion": 1, "packages": {}})


def test_a_permissive_tree_passes() -> None:
    report, failures = web_licences.check(
        lock(
            react={"version": "19.3.1", "license": "MIT"},
            cva={"version": "0.7.1", "license": "Apache-2.0"},
            tslib={"version": "2.8.1", "license": "0BSD"},
        )
    )
    assert failures == []
    assert report[0] == "web licences: 3 production packages in web/package-lock.json"
    assert (
        "  astro 7.4.4: MIT ok (the island runtime Astro inlines into pages)" in report
    )


def test_dev_tools_sit_outside_the_allowlist() -> None:
    _, failures = web_licences.check(
        lock(**{"axe-core": {"version": "4.14.0", "license": "MPL-2.0", "dev": True}})
    )
    assert failures == []


def test_a_shipped_package_outside_the_allowlist_fails() -> None:
    _, failures = web_licences.check(
        lock(
            gpl={"version": "1.0.0", "license": "GPL-3.0-only"},
            bare={"version": "2.0.0"},
            odd={"version": "3.0.0", "license": "SEE LICENSE IN LICENSE"},
        )
    )
    assert failures == [
        "bare 2.0.0: no licence in the lockfile",
        "gpl 1.0.0: GPL-3.0-only is outside the allowlist",
        "odd 3.0.0: 'SEE LICENSE IN LICENSE' is not an SPDX expression",
    ]


def test_build_output_tools_need_a_permissive_licence_of_their_own() -> None:
    entries = lock()
    entries["packages"]["node_modules/astro"]["license"] = "BUSL-1.1"
    del entries["packages"]["node_modules/@astrojs/react"]
    _, failures = web_licences.check(entries)
    assert failures == [
        (
            "astro 7.4.4 (the island runtime Astro inlines into pages): BUSL-1.1 is "
            "outside the allowlist"
        ),
        (
            "@astrojs/react: not in the lockfile, though the React client renderer "
            "in the client bundle ships"
        ),
    ]


def test_the_shipped_bundle_holds_only_production_packages() -> None:
    entries = lock(
        react={"version": "19.3.1", "license": "MIT"},
        katex={"version": "0.19.1", "license": "MIT", "dev": True},
    )
    report, failures = web_licences.check(entries, ["react", "@astrojs/react"])
    assert failures == []
    assert "  shipped @astrojs/react: build output, its licence checked" in report
    _, failures = web_licences.check(entries, ["react", "katex"])
    assert failures == [
        (
            "katex ships in the client bundle but is a development dependency: "
            "move it to dependencies in web/package.json"
        )
    ]


def test_main_reads_the_lockfile_and_the_shipped_list(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "package-lock.json"
    path.write_text(json.dumps(lock(react={"version": "1", "license": "MIT"})))
    shipped = tmp_path / "shipped.json"
    shipped.write_text(json.dumps({"format": 1, "packages": ["left-pad"]}))
    assert web_licences.main(["--lock", str(path)]) == 0
    assert web_licences.main(["--lock", str(path), "--shipped", str(shipped)]) == 1
    assert "left-pad ships in the client bundle" in capsys.readouterr().err
    shipped.write_text(json.dumps({"format": 2, "packages": []}))
    with pytest.raises(ValueError, match="format 1"):
        web_licences.main(["--lock", str(path), "--shipped", str(shipped)])


def test_the_committed_lockfile_passes() -> None:
    report, failures = web_licences.check(
        json.loads(web_licences.LOCKFILE.read_text(encoding="utf-8"))
    )
    assert failures == []
    assert len(report) > 1
