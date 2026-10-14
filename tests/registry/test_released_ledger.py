# tests/registry/test_released_ledger.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The released-id ledger: a released id is never deleted or reused (ADR-0003)."""

from __future__ import annotations

import dataclasses

import pytest
import toy_models as tm

from pyeconomics import registry
from pyeconomics.core import RegistryError
from pyeconomics.core._released import RELEASED, Released
from pyeconomics.core._rules import check_released

TOY = tm.toy_registry()
VALUE = "foundations.toy_time_value"
ZERO = "fixed_income.toy_zero_coupon"
OLD = "foundations.toy_tvm"


def problems(ledger: dict[str, Released]) -> list[str]:
    return [str(p) for p in TOY.problems(released=ledger)]


def test_the_shipped_ledger_covers_the_alpha_catalog() -> None:
    assert len(RELEASED) == 32
    assert set(RELEASED) == set(registry.ids())
    assert all(entry.first_version == "1.0.0a1" for entry in RELEASED.values())
    registry.validate()


def test_the_ledger_is_read_only() -> None:
    with pytest.raises(TypeError):
        RELEASED["x.y"] = Released("x.y", "1.0.0a1")  # type: ignore[index]


def test_a_record_is_immutable() -> None:
    record = Released(VALUE, "1.0.0a1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.first_version = "1.0.0"  # type: ignore[misc]


def test_a_ledger_of_ids_that_resolve_passes() -> None:
    ledger = {
        VALUE: Released(VALUE, "1.0.0a1"),
        ZERO: Released(ZERO, "1.0.0a1"),
        OLD: Released(VALUE, "1.0.0a1"),  # shipped as an alias, still one
    }
    assert problems(ledger) == []
    TOY.validate(released=ledger)


def test_a_renamed_model_keeps_its_old_id_as_an_alias() -> None:
    # The old id shipped as a model id; the model is now VALUE with OLD as alias.
    ledger = {OLD: Released(OLD, "1.0.0a1")}
    assert problems(ledger) == []


def test_a_deleted_id_is_reported() -> None:
    ledger = {"fixed_income.deleted": Released("fixed_income.deleted", "1.0.0a1")}
    [line] = problems(ledger)
    assert line.startswith("fixed_income.deleted: [released] ")
    assert "never deleted" in line


def test_a_reused_id_is_reported() -> None:
    # ZERO shipped as an alias of VALUE; it is now a different model's own id.
    ledger = {ZERO: Released(VALUE, "1.0.0a1")}
    [line] = problems(ledger)
    assert line.startswith(f"{ZERO}: [released] ")
    assert "never reused" in line


def test_a_released_model_that_has_gone_is_reported() -> None:
    ledger = {OLD: Released("foundations.toy_vanished", "1.0.0a1")}
    [line] = problems(ledger)
    assert "foundations.toy_vanished" in line
    assert "no longer resolves" in line


@pytest.mark.parametrize(
    "record",
    [
        Released("Not An Id", "1.0.0a1"),
        Released(VALUE, "v1"),
        Released(VALUE, ""),
        Released(VALUE, "1.0.0.dev1"),
    ],
)
def test_a_malformed_record_is_reported(record: Released) -> None:
    [line] = problems({VALUE: record})
    assert "malformed" in line


def test_validate_raises_with_the_ledger_problems() -> None:
    ledger = {"fixed_income.deleted": Released("fixed_income.deleted", "1.0.0")}
    with pytest.raises(RegistryError) as caught:
        TOY.validate(released=ledger)
    expected = (
        "fixed_income.deleted: [released] no longer resolves; "
        "a released id is never deleted (ADR-0003)"
    )
    assert caught.value.problems == (expected,)


def test_the_facade_accepts_a_ledger() -> None:
    ledger = {"fixed_income.deleted": Released("fixed_income.deleted", "1.0.0")}
    with pytest.raises(RegistryError, match="never deleted"):
        registry.validate(TOY, released=ledger)


def test_check_released_works_on_plain_collections() -> None:
    ledger = {VALUE: Released(VALUE, "1.0.0a1")}
    assert check_released(ledger, {VALUE}, {}) == []
    [problem] = check_released(ledger, set(), {})
    assert problem.model == VALUE
    assert problem.rule == "released"


def test_problems_come_out_in_id_order() -> None:
    ledger = {
        "risk.b": Released("risk.b", "1.0.0"),
        "risk.a": Released("risk.a", "1.0.0"),
    }
    assert [p.model for p in check_released(ledger, set(), {})] == ["risk.a", "risk.b"]


def test_a_retargeted_alias_is_reported() -> None:
    # macro.x shipped as an alias of macro.y; it now points at macro.z.
    ledger = {"macro.x": Released("macro.y", "1.0.0a1")}
    [problem] = check_released(ledger, {"macro.y", "macro.z"}, {"macro.x": "macro.z"})
    assert problem.rule == "released"
    assert "retargeted" in problem.detail
    assert "'macro.z'" in problem.detail
    assert "'macro.y'" in problem.detail


def test_a_renamed_target_keeps_its_aliases_valid() -> None:
    # macro.y was renamed macro.y2 with macro.y as an alias, and macro.x, which
    # shipped as an alias of macro.y, moved with it.
    ledger = {
        "macro.x": Released("macro.y", "1.0.0a1"),
        "macro.y": Released("macro.y", "1.0.0a1"),
    }
    aliases = {"macro.x": "macro.y2", "macro.y": "macro.y2"}
    assert check_released(ledger, {"macro.y2"}, aliases) == []
