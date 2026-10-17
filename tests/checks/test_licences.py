# tests/checks/test_licences.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for scripts/checks/licences.py, the ADR-0004 licence allowlist."""

from __future__ import annotations

import importlib.util
import re
import sys
import tomllib
from email.message import Message
from importlib import metadata
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable, Collection

Package = dict[str, Any]

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "checks" / "licences.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("licences_check", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations through it
    spec.loader.exec_module(module)
    return module


licences = load_script()
LINUX = {"sys_platform": "linux", "platform_system": "Linux", "python_version": "3.12"}
WINDOWS = {
    "sys_platform": "win32",
    "platform_system": "Windows",
    "python_version": "3.12",
}


def meta(**fields: str | list[str]) -> Message:
    message = Message()
    for field, value in fields.items():
        for item in value if isinstance(value, list) else [value]:
            message[field.replace("_", "-")] = item
    return message


def lock(
    *packages: Package,
    root_deps: Collection[Package] = (),
    extras: dict[str, list[Package]] | None = None,
) -> dict[str, list[Package]]:
    root: Package = {
        "name": "pyeconomics",
        "version": "1.0.0.dev1",
        "source": {"editable": "."},
        "dependencies": list(root_deps),
        "optional-dependencies": extras or {},
        "dev-dependencies": {"dev": [{"name": "devtool"}]},
    }
    devtool = {"name": "devtool", "version": "1.0", "source": {"registry": "x"}}
    return {"package": [root, devtool, *packages]}


def pkg(
    name: str,
    version: str = "1.0",
    deps: Collection[Package] = (),
    optional: dict[str, list[Package]] | None = None,
) -> Package:
    entry: Package = {"name": name, "version": version, "source": {"registry": "x"}}
    if deps:
        entry["dependencies"] = list(deps)
    if optional:
        entry["optional-dependencies"] = optional
    return entry


def installed(**licence_metadata: Message) -> Callable[[str], SimpleNamespace]:
    def distribution(name: str) -> SimpleNamespace:
        if name not in licence_metadata:
            raise metadata.PackageNotFoundError(name)
        return SimpleNamespace(version="1.0", metadata=licence_metadata[name])

    return distribution


@pytest.mark.parametrize(
    ("expression", "allowed"),
    [
        ("MIT", True),
        ("mit", True),
        ("Apache-2.0 OR GPL-3.0-only", True),
        ("BSD-3-Clause AND MIT", True),
        ("(MIT OR GPL-2.0-only) AND ISC", True),
        ("PSF-2.0", True),
        ("GPL-3.0-or-later", False),
        ("MIT AND GPL-3.0-only", False),
        ("BSD-3-Clause AND 0BSD", False),
        ("Apache-2.0 WITH LLVM-exception", False),
        ("LicenseRef-Proprietary", False),
    ],
)
def test_spdx_expressions(expression: str, *, allowed: bool) -> None:
    assert licences.spdx_allowed(expression) is allowed


@pytest.mark.parametrize(
    "expression", ["MIT License", "MIT AND", "(MIT", "MIT OR OR ISC", ""]
)
def test_unparseable_spdx_raises(expression: str) -> None:
    with pytest.raises(ValueError, match=re.escape(f"in {expression!r}")):
        licences.spdx_allowed(expression)


@pytest.mark.parametrize(
    ("fields", "text", "allowed"),
    [
        ({"License_Expression": "MIT"}, "MIT", True),
        (
            {"License_Expression": "GPL-3.0-only", "License": "MIT"},
            "GPL-3.0-only",
            False,
        ),
        ({"License": "Apache 2.0"}, "Apache 2.0", True),
        ({"License": "BSD-3-Clause"}, "BSD-3-Clause", True),
        ({"License": "GPLv3"}, "GPLv3", False),
        (
            {
                "License": "UNKNOWN",
                "Classifier": ["License :: OSI Approved :: MIT License"],
            },
            "MIT License",
            True,
        ),
        (
            {"Classifier": ["License :: OSI Approved :: BSD License"]},
            "BSD License",
            False,
        ),
        (
            {
                "Classifier": [
                    "License :: OSI Approved :: MIT License",
                    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
                ]
            },
            "GNU General Public License v3 (GPLv3) AND MIT License",
            False,
        ),
        ({}, "", False),
    ],
)
def test_licence_of_metadata(
    fields: dict[str, str | list[str]], text: str, *, allowed: bool
) -> None:
    licence = licences.licence_of(meta(**fields))
    assert (licence.text, licence.allowed) == (text, allowed)


def test_closure_follows_extras_and_markers_but_not_groups() -> None:
    data = lock(
        pkg("numpy"),
        pkg("click", deps=[{"name": "colorama", "marker": "sys_platform == 'win32'"}]),
        pkg("colorama"),
        pkg("httpx", optional={"http2": [{"name": "h2"}]}),
        pkg("h2"),
        root_deps=[{"name": "numpy"}],
        extras={
            "cli": [{"name": "click"}],
            "server": [{"name": "httpx", "extra": ["http2"]}],
        },
    )
    everywhere = licences.runtime_closure(data, "pyeconomics", follow_markers=False)
    on_linux = licences.runtime_closure(
        data, "pyeconomics", follow_markers=True, environment=LINUX
    )
    on_windows = licences.runtime_closure(
        data, "pyeconomics", follow_markers=True, environment=WINDOWS
    )
    assert {name for name, _ in everywhere} == {
        "numpy",
        "click",
        "colorama",
        "httpx",
        "h2",
    }
    assert ("colorama", "1.0") not in on_linux
    assert ("colorama", "1.0") in on_windows
    assert "devtool" not in {name for name, _ in everywhere}


def test_empty_closure_passes() -> None:
    report, failures = licences.check(
        lock(), "pyeconomics", {}, distribution=installed()
    )
    assert failures == []
    assert report[0].startswith("licences: 0 runtime packages")


def test_disallowed_and_missing_licences_fail() -> None:
    names = ("good", "gpl", "bare")
    data = lock(*(pkg(n) for n in names), root_deps=[{"name": n} for n in names])
    distribution = installed(
        good=meta(License_Expression="MIT"),
        gpl=meta(License_Expression="GPL-3.0-only"),
        bare=meta(),
    )
    _, failures = licences.check(data, "pyeconomics", {}, distribution=distribution)
    assert [f.split(":")[0] for f in failures] == ["bare 1.0", "gpl 1.0"]
    assert any(f.startswith("gpl 1.0: GPL-3.0-only") for f in failures)
    assert any(f.startswith("bare 1.0: - [no licence metadata]") for f in failures)


def test_uninstalled_or_stale_package_fails() -> None:
    data = lock(
        pkg("absent"),
        pkg("stale", version="2.0"),
        root_deps=[{"name": "absent"}, {"name": "stale"}],
    )
    distribution = installed(stale=meta(License_Expression="MIT"))
    _, failures = licences.check(data, "pyeconomics", {}, distribution=distribution)
    assert any("absent 1.0: not installed" in f for f in failures)
    assert any("stale 2.0: 1.0 is installed" in f for f in failures)


def test_excluded_names_fail_whatever_their_metadata_says() -> None:
    data = lock(pkg("full_fred"), root_deps=[{"name": "full_fred"}])
    exceptions = {
        "full-fred": {"package": "full_fred", "licence": "MIT", "reason": "no"}
    }
    distribution = installed(**{"full-fred": meta(License_Expression="MIT")})
    _, failures = licences.check(
        data, "pyeconomics", exceptions, distribution=distribution
    )
    assert failures == [
        "full-fred 1.0: excluded by name in ADR-0004 (conflicting licence metadata)"
    ]


def test_reviewed_exception_must_match_the_reported_licence() -> None:
    data = lock(pkg("oldlib"), root_deps=[{"name": "oldlib"}])
    distribution = installed(
        oldlib=meta(Classifier=["License :: OSI Approved :: BSD License"])
    )
    exception = {
        "package": "oldlib",
        "licence": "BSD License",
        "reason": "LICENSE is BSD-3",
    }
    _, failures = licences.check(
        data, "pyeconomics", {"oldlib": exception}, distribution=distribution
    )
    assert failures == []
    stale = {**exception, "licence": "MIT"}
    _, failures = licences.check(
        data, "pyeconomics", {"oldlib": stale}, distribution=distribution
    )
    assert len(failures) == 1
    assert "review it again" in failures[0]


def test_exceptions_file_validation(tmp_path: Path) -> None:
    path = tmp_path / "licence_exceptions.toml"
    path.write_text(
        '[[exception]]\npackage = "a"\nlicence = "X"\nreason = "ok"\n'
        '[[exception]]\npackage = "b"\nlicence = "Y"\n'
        '[[exception]]\npackage = "A"\nlicence = "Z"\nreason = "dup"\n',
        encoding="utf-8",
    )
    exceptions, problems = licences.load_exceptions(path)
    assert set(exceptions) == {"a"}
    assert problems == [
        (
            "licence_exceptions.toml: exception 2 needs exactly package, licence "
            "and reason"
        ),
        "licence_exceptions.toml: a has more than one exception",
    ]


# The reviewed exceptions the maintainer approved (Phase 2 Step 1's pull
# request; patsy, the econometrics extra's, in Step 12's; cffi, the keyring
# extra's on Linux, in Phase 3 Step 3's). The file started empty (ADR-0004); a
# new entry needs a new review, and this set changes with it.
REVIEWED_EXCEPTIONS = {
    "defusedxml",  # Maintainer approved 2026-10-16, carried from Step 7.
    "certifi",
    "sdmx1",
    "cffi",
    "numpy",
    "pandas",
    "patsy",
    "python-dateutil",
    "scipy",
}


def test_the_shipped_exceptions_are_the_reviewed_ones() -> None:
    exceptions, problems = licences.load_exceptions(licences.EXCEPTIONS_FILE)
    assert problems == []
    assert set(exceptions) == REVIEWED_EXCEPTIONS
    lock = tomllib.loads((licences.ROOT / "uv.lock").read_text(encoding="utf-8"))
    runtime = {
        name
        for name, _ in licences.runtime_closure(
            lock, licences.project_name(licences.ROOT), follow_markers=False
        )
    }
    assert set(exceptions) <= runtime
    for entry in exceptions.values():
        assert "Checked by" in entry["reason"]


def test_the_runtime_closure_passes_on_this_platform() -> None:
    # The gate-licences job runs the hook on Ubuntu only, but an extra's
    # closure differs by platform: keyring brings SecretStorage, jeepney,
    # cryptography and cffi on Linux and pywin32-ctypes on Windows. The test
    # group installs every extra's packages, so the tests matrix runs the
    # hook's own check on all three operating systems.
    exceptions, problems = licences.load_exceptions(licences.EXCEPTIONS_FILE)
    lock = tomllib.loads((licences.ROOT / "uv.lock").read_text(encoding="utf-8"))
    report, failures = licences.check(
        lock, licences.project_name(licences.ROOT), exceptions
    )
    assert (problems, failures) == ([], [])
    assert report[0].startswith("licences: ")
