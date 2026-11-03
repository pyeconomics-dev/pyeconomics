# tests/checks/test_app_contents.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for scripts/checks/app_contents.py, the app wheel's allowlist."""

from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "checks" / "app_contents.py"
VERSION = "1.0.0rc1.dev1"
INFO = f"pyeconomics_app-{VERSION}.dist-info"
SITE = "pyeconomics_app/site"
METADATA = (
    "Metadata-Version: 2.4\nName: pyeconomics-app\n"
    f"Version: {VERSION}\nLicense-Expression: Apache-2.0\n\nThe web app.\n"
)

WHEEL_FILES: dict[str, bytes] = {
    "pyeconomics_app/__init__.py": b"",
    "pyeconomics_app/py.typed": b"",
    f"{SITE}/index.html": b"<h1>home</h1>",
    f"{SITE}/404.html": b"<h1>not here</h1>",
    f"{SITE}/_headers": b"/*\n  Content-Security-Policy: default-src 'self'\n",
    f"{SITE}/_redirects": b"",
    f"{SITE}/version.json": json.dumps({"pyeconomics": VERSION}).encode(),
    f"{SITE}/_astro/app.js": b"export const a = 1;",
    f"{SITE}/pagefind/index/en_1.pf_index": b"\x1f\x8b gzip data",
    f"{SITE}/og/home.png": b"\x89PNG\r\n",
    f"{INFO}/METADATA": METADATA.encode(),
    f"{INFO}/WHEEL": b"Wheel-Version: 1.0\n",
    f"{INFO}/RECORD": b"",
    f"{INFO}/licenses/LICENSE": b"",
    f"{INFO}/licenses/NOTICE": b"",
}


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("app_contents_check", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


app_contents = load_script()


def project(root: Path, version: str = VERSION, member: str = VERSION) -> Path:
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


def write_wheel(
    dist: Path,
    files: dict[str, bytes],
    *,
    name: str = f"pyeconomics_app-{VERSION}-py3-none-any.whl",
    modes: dict[str, int] | None = None,
) -> Path:
    dist.mkdir(exist_ok=True)
    path = dist / name
    with zipfile.ZipFile(path, "w") as wheel:
        for member, data in files.items():
            info = zipfile.ZipInfo(member)
            info.external_attr = (modes or {}).get(member, 0o644) << 16
            wheel.writestr(info, data)
        wheel.writestr("pyeconomics_app/", b"")  # a directory entry, as uv_build writes
    return path


def check(
    tmp_path: Path,
    files: dict[str, bytes],
    *,
    name: str = f"pyeconomics_app-{VERSION}-py3-none-any.whl",
    modes: dict[str, int] | None = None,
) -> list[str]:
    path = write_wheel(tmp_path / "dist", files, name=name, modes=modes)
    problems: list[str] = app_contents.check_wheel(path, VERSION)
    return problems


def test_a_static_site_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_wheel(tmp_path / "dist-app", WHEEL_FILES)
    assert app_contents.main(project(tmp_path), tmp_path / "dist-app") == 0
    assert "holds only the static site" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("member", "data", "why"),
    [
        ("pyeconomics_app/server.py", b"", "outside pyeconomics_app/site/"),
        ("pyeconomics_app-x.dist-info/entry_points.txt", b"", "outside"),
        ("secrets.txt", b"", "outside"),
        (f"{SITE}/.env", b"KEY=1", "hidden"),
        (f"{SITE}/.astro/data-store.json", b"{}", "hidden"),
        (f"{SITE}/node_modules/a/index.js", b"", "dependency"),
        (f"{SITE}/run.sh", b"echo", "not a kind of file"),
        (f"{SITE}/tool.exe", b"", "not a kind of file"),
        (f"{SITE}/data.zip", b"", "not a kind of file"),
        (f"{SITE}/page.py", b"", "not a kind of file"),
        (f"{SITE}/a.js", b"#!/usr/bin/env node\n", "shebang"),
        (f"{SITE}/a.png", b"\x7fELF\x02", "ELF"),
        (f"{SITE}/a.txt", b"MZ\x90\x00", "PE"),
        (f"{SITE}/a.json", b"\xcf\xfa\xed\xfe", "Mach-O"),
        (f"{SITE}/a.css", b"PK\x03\x04", "ZIP"),
        (
            f"{SITE}/_astro/a.js.map",
            b'{"version":3,"sources":["C:\\\\Users\\\\me\\\\web\\\\a.ts"]}',
            "local path",
        ),
        (
            f"{SITE}/_astro/b.js.map",
            b'{"version":3,"sources":["/home/runner/work/a.ts"]}',
            "local path",
        ),
        (
            f"{SITE}/_astro/c.js.map",
            b'{"version":3,"sourceRoot":"file:///repo/","sources":["a.ts"]}',
            "local path",
        ),
        (f"{SITE}/_astro/d.js.map", b"not json", "not a source map"),
    ],
)
def test_anything_but_the_static_site_fails(
    tmp_path: Path, member: str, data: bytes, why: str
) -> None:
    problems = check(tmp_path, {**WHEEL_FILES, member: data})
    assert len(problems) == 1, problems
    assert member in problems[0]
    assert why in problems[0]


def test_a_relative_source_map_passes(tmp_path: Path) -> None:
    source_map = b'{"version":3,"sources":["../../src/lib/a.ts"]}'
    assert check(tmp_path, {**WHEEL_FILES, f"{SITE}/_astro/a.js.map": source_map}) == []


def test_an_executable_member_fails(tmp_path: Path) -> None:
    member = f"{SITE}/_astro/app.js"
    problems = check(tmp_path, WHEEL_FILES, modes={member: 0o755})
    assert problems == [
        f"pyeconomics_app-{VERSION}-py3-none-any.whl: {member} is marked executable"
    ]


@pytest.mark.parametrize(
    "missing", ["index.html", "404.html", "_headers", "version.json"]
)
def test_a_wheel_without_the_built_site_fails(tmp_path: Path, missing: str) -> None:
    files = {k: v for k, v in WHEEL_FILES.items() if k != f"{SITE}/{missing}"}
    problems = check(tmp_path, files)
    assert any(f"{SITE}/{missing} is missing" in problem for problem in problems)


def test_a_wheel_of_only_the_package_fails(tmp_path: Path) -> None:
    files = {k: v for k, v in WHEEL_FILES.items() if not k.startswith(f"{SITE}/")}
    assert len(check(tmp_path, files)) == len(app_contents.REQUIRED)


def test_a_site_built_from_another_version_fails(tmp_path: Path) -> None:
    stale = json.dumps({"pyeconomics": "1.0.0b1"}).encode()
    problems = check(tmp_path, {**WHEEL_FILES, f"{SITE}/version.json": stale})
    wheel = f"pyeconomics_app-{VERSION}-py3-none-any.whl"
    assert problems == [f"{wheel}: the site was built from '1.0.0b1', not '{VERSION}'"]


@pytest.mark.parametrize(
    ("metadata", "why"),
    [
        (METADATA.replace("Name: pyeconomics-app", "Name: other"), "METADATA names"),
        (METADATA.replace(VERSION, "1.0.0"), "METADATA version"),
        (METADATA.replace("Apache-2.0", "MIT"), "licence"),
        (METADATA.replace("\n\n", "\nRequires-Dist: requests\n\n"), "requires"),
    ],
)
def test_bad_metadata_fails(tmp_path: Path, metadata: str, why: str) -> None:
    problems = check(tmp_path, {**WHEEL_FILES, f"{INFO}/METADATA": metadata.encode()})
    assert any(why in problem for problem in problems), problems


def test_a_missing_metadata_fails(tmp_path: Path) -> None:
    files = {k: v for k, v in WHEEL_FILES.items() if k != f"{INFO}/METADATA"}
    assert any("METADATA is missing" in p for p in check(tmp_path, files))


def test_a_wrongly_named_wheel_fails(tmp_path: Path) -> None:
    problems = check(
        tmp_path, WHEEL_FILES, name="pyeconomics_app-1.0.0-py3-none-any.whl"
    )
    assert any("expected pyeconomics_app-" in problem for problem in problems)


def test_a_wheel_over_pypis_limit_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_contents, "MAX_BYTES", 10)
    assert any("file limit" in p for p in check(tmp_path, WHEEL_FILES))


@pytest.mark.parametrize("extra", ["pyeconomics-1.0.0-py3-none-any.whl", "app.tar.gz"])
def test_the_directory_holds_the_one_wheel(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], extra: str
) -> None:
    dist = tmp_path / "dist-app"
    write_wheel(dist, WHEEL_FILES)
    (dist / extra).write_bytes(b"")
    assert app_contents.main(project(tmp_path), dist) == 1
    assert "expected one pyeconomics-app wheel" in capsys.readouterr().err


def test_an_empty_directory_fails(tmp_path: Path) -> None:
    (tmp_path / "dist-app").mkdir()
    assert app_contents.main(project(tmp_path), tmp_path / "dist-app") == 1


def test_a_member_at_another_version_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_wheel(tmp_path / "dist-app", WHEEL_FILES)
    root = project(tmp_path, member="1.0.0")
    assert app_contents.main(root, tmp_path / "dist-app") == 1
    assert "pyeconomics-app is 1.0.0" in capsys.readouterr().err
