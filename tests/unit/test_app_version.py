# tests/unit/test_app_version.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""pyeconomics and pyeconomics-app move together (ADR-0002; ADR-0013 16).

The repository is a uv workspace whose second member, packages/pyeconomics-app,
builds the wheel that carries the built site. The two distributions are released
in lockstep at one version, so every place that names it must agree: the
project's version, the member's, the ``[app]`` extra's pin, CITATION.cff and
server.json. ``uv version`` moves only the root project's, so a bump that forgets
one of the others fails here. The member also shares the root's licence, Python
support and classifiers, ships the root's LICENSE and NOTICE byte for byte, and
``[app]`` stays out of ``[all]`` (ADR-0002) while carrying the ``server`` extra's
requirements, which ``pyeconomics serve`` needs.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from packaging.requirements import Requirement

if TYPE_CHECKING:
    import pytest

ROOT: Final = Path(__file__).resolve().parents[2]
MEMBER: Final = ROOT / "packages" / "pyeconomics-app"
MEMBER_PATH: Final = "packages/pyeconomics-app"
APP: Final = "pyeconomics-app"


def _toml(path: Path) -> dict[str, Any]:
    document: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    return document


def _root() -> dict[str, Any]:
    return _toml(ROOT / "pyproject.toml")


def _member() -> dict[str, Any]:
    return _toml(MEMBER / "pyproject.toml")


def _extra(name: str) -> list[Requirement]:
    extras = _root()["project"]["optional-dependencies"]
    return [Requirement(line) for line in extras[name]]


def _citation_version() -> str:
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    found: list[str] = re.findall(r'^version:\s*"?([^"\s]+)"?\s*$', text, re.MULTILINE)
    assert len(found) == 1, found
    return found[0]


def test_every_version_field_is_the_projects() -> None:
    version = _root()["project"]["version"]
    (pin,) = [r for r in _extra("app") if r.name == APP]
    entry = json.loads((ROOT / "server.json").read_bytes())
    found = {
        "packages/pyeconomics-app/pyproject.toml": _member()["project"]["version"],
        "[app]'s pin": str(pin.specifier),
        "CITATION.cff": _citation_version(),
        "server.json version": entry["version"],
        "server.json package": entry["packages"][0]["version"],
    }
    assert found == {
        "packages/pyeconomics-app/pyproject.toml": version,
        "[app]'s pin": f"=={version}",
        "CITATION.cff": version,
        "server.json version": version,
        "server.json package": version,
    }


def test_the_app_extra_pins_the_app_and_carries_the_server_extra() -> None:
    app = _extra("app")
    (pin,) = [r for r in app if r.name == APP]
    assert pin.marker is None
    assert not pin.extras
    rest = sorted(str(r) for r in app if r.name != APP)
    assert rest == sorted(str(r) for r in _extra("server"))


def test_all_includes_neither_app_nor_its_package() -> None:
    extras = _root()["project"]["optional-dependencies"]
    assert APP not in {r.name for r in _extra("all")}
    assert not any("pyeconomics" in line for line in extras["all"])


def test_the_member_is_the_workspace_and_the_app_s_source() -> None:
    uv = _root()["tool"]["uv"]
    assert uv["workspace"]["members"] == [MEMBER_PATH]
    assert uv["sources"][APP] == {"workspace": True}
    lock = _toml(ROOT / "uv.lock")
    assert lock["manifest"]["members"] == ["pyeconomics", APP]
    (locked,) = [p for p in lock["package"] if p["name"] == APP]
    assert locked["source"] == {"editable": MEMBER_PATH}
    assert locked["version"] == _root()["project"]["version"]


def test_the_member_shares_the_roots_terms() -> None:
    root, member = _root(), _member()
    for key in ("requires-python", "license", "license-files", "authors"):
        assert member["project"][key] == root["project"][key], key
    assert member["project"]["classifiers"] == root["project"]["classifiers"]
    assert member["project"]["name"] == APP
    assert member["project"]["dependencies"] == []
    assert member["build-system"] == root["build-system"]
    assert member["tool"]["uv"]["build-backend"]["module-name"] == "pyeconomics_app"
    for name in ("LICENSE", "NOTICE"):
        assert (MEMBER / name).read_bytes() == (ROOT / name).read_bytes(), name
    assert (MEMBER / "README.md").is_file()


def test_the_package_exposes_only_site_path(monkeypatch: pytest.MonkeyPatch) -> None:
    # From the checkout, whether or not the [app] extra is installed.
    path = MEMBER / "src" / "pyeconomics_app" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "pyeconomics_app", path, submodule_search_locations=[str(path.parent)]
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "pyeconomics_app", module)
    spec.loader.exec_module(module)
    assert module.__all__ == ["site_path"]
    site = module.site_path()
    assert site.name == "site"
    assert Path(str(site)).parent == path.parent
