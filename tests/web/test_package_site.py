# tests/web/test_package_site.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/web/package_site.py, which fills the app wheel's site."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "web" / "package_site.py"
VERSION = "1.0.0rc1.dev1"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("package_site", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


package_site = load_script()


def project(root: Path, version: str = VERSION, member: str = VERSION) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "pyeconomics"\nversion = "{version}"\n', encoding="utf-8"
    )
    app = root / "packages" / "pyeconomics-app"
    app.mkdir(parents=True)
    (app / "pyproject.toml").write_text(
        f'[project]\nname = "pyeconomics-app"\nversion = "{member}"\n',
        encoding="utf-8",
    )
    return root


def build(dist: Path, version: str = VERSION) -> Path:
    files = {
        "index.html": "<h1>home</h1>",
        "404.html": "<h1>not here</h1>",
        "_headers": "/*\n  Content-Security-Policy: default-src 'self'\n",
        "version.json": json.dumps({"pyeconomics": version}),
        "models/demo/index.html": "<h1>demo</h1>",
    }
    for name, text in files.items():
        path = dist / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return dist


def test_a_build_replaces_the_site_whole(tmp_path: Path) -> None:
    root = project(tmp_path / "repo")
    site = tmp_path / "site"
    (site / "stale").mkdir(parents=True)
    (site / "stale" / "index.html").write_text("old", encoding="utf-8")
    count = package_site.package(build(tmp_path / "dist"), site=site, root=root)
    assert count == 5
    assert (site / "models" / "demo" / "index.html").read_text(encoding="utf-8") == (
        "<h1>demo</h1>"
    )
    assert not (site / "stale").exists()


@pytest.mark.parametrize(
    "missing", ["index.html", "404.html", "_headers", "version.json"]
)
def test_a_build_without_a_required_file_is_refused(
    tmp_path: Path, missing: str
) -> None:
    root = project(tmp_path / "repo")
    dist = build(tmp_path / "dist")
    (dist / missing).unlink()
    with pytest.raises(package_site.PackageError, match=f"lacks {missing}"):
        package_site.check_build(dist, root)


def test_no_build_is_refused(tmp_path: Path) -> None:
    root = project(tmp_path / "repo")
    with pytest.raises(package_site.PackageError, match="not a build directory"):
        package_site.check_build(tmp_path / "missing", root)


@pytest.mark.parametrize(
    ("version", "member", "built"),
    [
        (VERSION, VERSION, "1.0.0b1"),
        (VERSION, "1.0.0", VERSION),
        ("1.0.0", VERSION, VERSION),
    ],
)
def test_versions_that_differ_are_refused(
    tmp_path: Path, version: str, member: str, built: str
) -> None:
    root = project(tmp_path / "repo", version=version, member=member)
    with pytest.raises(package_site.PackageError, match="versions differ"):
        package_site.check_build(build(tmp_path / "dist", built), root)


def test_a_link_in_the_build_is_refused(tmp_path: Path) -> None:
    root = project(tmp_path / "repo")
    dist = build(tmp_path / "dist")
    outside = tmp_path / "outside"
    outside.mkdir()
    link = dist / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        if sys.platform != "win32":
            pytest.skip("this platform cannot link a directory")  # pragma: no cover
        import _winapi  # noqa: PLC0415 - Windows only

        _winapi.CreateJunction(str(outside), str(link))
    with pytest.raises(package_site.PackageError, match="symbolic link"):
        package_site.check_build(dist, root)


def test_main_reports_a_refusal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert package_site.main(["--dist", str(tmp_path / "missing")]) == 1
    assert capsys.readouterr().err.startswith("package_site: ")


def test_main_packages_a_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = project(tmp_path / "repo")
    site = tmp_path / "site"
    monkeypatch.setattr(package_site, "SITE", site)
    dist = build(tmp_path / "dist")
    original = package_site.package
    monkeypatch.setattr(
        package_site, "package", lambda given: original(given, site=site, root=root)
    )
    assert package_site.main(["--dist", str(dist)]) == 0
    assert "5 files copied" in capsys.readouterr().out
    assert (site / "index.html").is_file()
