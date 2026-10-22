# tests/checks/test_release_ledger.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Permanent history, renamed ids, deterministic output and read-only checks."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import toy_models as tm

from pyeconomics.core import RegistryError
from pyeconomics.core._released import Released

if TYPE_CHECKING:
    from types import ModuleType

REPO = Path(__file__).resolve().parents[2]


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "release_ledger_script", REPO / "scripts/release_ledger.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ledger = load_script()


@pytest.fixture(autouse=True)
def isolated_data_target(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ledger, "DATA_TARGET", tmp_path / "data_released.py")


def test_history_is_preserved_and_aliases_are_recorded() -> None:
    old = Released(tm.time_value.id, "1.0.0a1")
    released = {tm.time_value.id: old}
    result = ledger.extend(tm.toy_registry(), released, "1.0.0a2")
    assert result[tm.time_value.id] == old
    assert result[tm.time_value.spec.aliases[0].id] == Released(
        tm.time_value.id, "1.0.0a2"
    )
    assert result[tm.zero_coupon.id] == Released(tm.zero_coupon.id, "1.0.0a2")
    assert released == {tm.time_value.id: old}
    assert list(result) == sorted(result)


def test_a_renamed_canonical_id_keeps_its_original_history() -> None:
    alias = tm.time_value.spec.aliases[0].id
    original = Released(alias, "1.0.0a1")
    result = ledger.extend(tm.toy_registry(), {alias: original}, "1.0.0a2")
    assert result[alias] == original


def test_a_missing_released_id_is_never_silently_removed() -> None:
    with pytest.raises(RegistryError, match="never deleted"):
        ledger.extend(
            tm.toy_registry(),
            {"risk.deleted": Released("risk.deleted", "1.0.0a1")},
            "1.0.0a2",
        )


@pytest.mark.parametrize("version", ["v1.0.0a1", "1.0.0a1.dev3", "0.2.6", '1.0.0"', ""])
def test_invalid_release_versions_are_refused(version: str) -> None:
    with pytest.raises(ValueError, match="version"):
        ledger.extend(tm.toy_registry(), {}, version)


def test_render_is_deterministic_and_importable() -> None:
    records = {
        "risk.b": Released("risk.b", "1.0.0a1"),
        "risk.a": Released("risk.a", "1.0.0a2"),
    }
    rendered = ledger.render(records)
    assert rendered == ledger.render(dict(reversed(list(records.items()))))
    assert b"\r" not in rendered
    assert rendered.startswith(b"# src/pyeconomics/core/_released.py\n# Copyright")
    assert b"scripts/release_ledger.py" in rendered
    assert b'"risk.a": Released("risk.a", "1.0.0a2")' in rendered
    compile(rendered, "_released.py", "exec")


def test_the_committed_ledger_is_the_reproducible_script_output() -> None:
    assert ledger.render(ledger.RELEASED) == ledger.TARGET.read_bytes()
    target = REPO / "src/pyeconomics/data/_released.py"
    assert ledger.render_data(ledger.PROVIDERS, ledger.CONCEPTS) == target.read_bytes()


def test_check_fails_on_missing_ids_without_writing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "_released.py"
    target.write_bytes(b"untouched\n")
    monkeypatch.setattr(ledger, "TARGET", target)
    monkeypatch.setattr(ledger, "installed", tm.toy_registry)
    monkeypatch.setattr(ledger, "RELEASED", {})
    assert ledger.main(["--check"]) == 1
    assert "missing ids" in capsys.readouterr().err
    assert target.read_bytes() == b"untouched\n"


def test_check_passes_with_complete_history(monkeypatch: pytest.MonkeyPatch) -> None:
    released = ledger.extend(tm.toy_registry(), {}, "1.0.0a1")
    monkeypatch.setattr(ledger, "installed", tm.toy_registry)
    monkeypatch.setattr(ledger, "RELEASED", released)
    assert ledger.main(["--check"]) == 0


def test_write_is_repeatable_and_changes_only_the_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "_released.py"
    target.write_bytes(ledger.TARGET.read_bytes())
    monkeypatch.setattr(ledger, "TARGET", target)
    monkeypatch.setattr(ledger, "installed", tm.toy_registry)
    monkeypatch.setattr(ledger, "RELEASED", {})
    assert ledger.main(["1.0.0a1"]) == 0
    first = target.read_bytes()
    assert ledger.main(["1.0.0a1"]) == 0
    assert target.read_bytes() == first
    assert set(tmp_path.iterdir()) == {target, ledger.DATA_TARGET}
    assert ledger.DATA_TARGET.read_bytes() == ledger.render_data(
        ledger.PROVIDERS, ledger.CONCEPTS
    )


def test_write_error_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(ledger, "TARGET", tmp_path / "absent" / "_released.py")
    monkeypatch.setattr(ledger, "installed", tm.toy_registry)
    monkeypatch.setattr(ledger, "RELEASED", {})
    assert ledger.main(["1.0.0a1"]) == 1
    assert "release-ledger:" in capsys.readouterr().err


def test_write_requires_a_version() -> None:
    with pytest.raises(SystemExit, match="2"):
        ledger.main([])


def test_data_history_is_preserved_and_output_is_deterministic() -> None:
    original = Released("fred", "1.0.0a2")
    released = {"fred": original}
    result = ledger.extend_ids(["fred", "bls"], released, "1.0.0b1")
    assert result == {"bls": Released("bls", "1.0.0b1"), "fred": original}
    assert released == {"fred": original}
    rendered = ledger.render_data(
        result, {"us.test.rate": Released("us.test.rate", "1.0.0a2")}
    )
    assert rendered == ledger.render_data(
        dict(reversed(list(result.items()))),
        {"us.test.rate": Released("us.test.rate", "1.0.0a2")},
    )
    assert b"\r" not in rendered
    assert rendered.startswith(b"# src/pyeconomics/data/_released.py\n# Copyright")
    assert b"scripts/release_ledger.py" in rendered
    compile(rendered, "data_released.py", "exec")


@pytest.mark.parametrize("kind", ["provider", "concept"])
def test_check_requires_every_data_id_without_writing(
    kind: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "models.py"
    target.write_bytes(b"untouched\n")
    ledger.DATA_TARGET.write_bytes(b"data untouched\n")
    monkeypatch.setattr(ledger, "TARGET", target)
    monkeypatch.setattr(ledger, "installed", tm.toy_registry)
    monkeypatch.setattr(
        ledger, "RELEASED", ledger.extend(tm.toy_registry(), {}, "1.0.0a2")
    )
    monkeypatch.setattr(ledger, "PROVIDERS" if kind == "provider" else "CONCEPTS", {})
    assert ledger.main(["--check"]) == 1
    assert f"{kind}:" in capsys.readouterr().err
    assert target.read_bytes() == b"untouched\n"
    assert ledger.DATA_TARGET.read_bytes() == b"data untouched\n"


@pytest.mark.parametrize("kind", ["provider", "concept"])
def test_a_deleted_data_id_blocks_both_writes(
    kind: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "models.py"
    target.write_bytes(b"untouched\n")
    ledger.DATA_TARGET.write_bytes(b"data untouched\n")
    monkeypatch.setattr(ledger, "TARGET", target)
    name = "removed" if kind == "provider" else "us.removed.rate"
    monkeypatch.setattr(
        ledger,
        "PROVIDERS" if kind == "provider" else "CONCEPTS",
        {name: Released(name, "1.0.0a1")},
    )
    assert ledger.main(["1.0.0a2"]) == 1
    assert name in capsys.readouterr().err
    assert target.read_bytes() == b"untouched\n"
    assert ledger.DATA_TARGET.read_bytes() == b"data untouched\n"


def test_invalid_data_version_is_refused() -> None:
    with pytest.raises(ValueError, match="version"):
        ledger.extend_ids(["fred"], {}, "1.0.0a2.dev1")
