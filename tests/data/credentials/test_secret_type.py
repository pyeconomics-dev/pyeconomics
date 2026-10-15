# tests/data/credentials/test_secret_type.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Secret: a mask when printed, refused by pickling and JSON, constant-time equal.

No assertion here compares a key in a way pytest could print: comparisons are
computed first, and texts are checked with LeakCheck.found_in, which reports
names only.
"""

from __future__ import annotations

import copy
import json
import secrets
from typing import TYPE_CHECKING

import pytest
from leakcheck import LeakCheck, canary

from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.errors import InputError
from pyeconomics.data import CredentialError, Secret, redaction
from pyeconomics.data.credentials import (
    MAX_KEY_LENGTH,
    MIN_KEY_LENGTH,
    key_problem,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def test_every_printed_form_is_the_mask_naming_the_provider() -> None:
    held = canary("fred")
    mask = "<Secret fred: redacted>"
    shown = {
        "repr": [repr(held.held)],
        "str": [str(held.held)],
        "format": [f"{held.held}", f"{held.held:>60}", f"{held.held!s}"],
        "percent": ["%s %r" % (held.held, held.held)],  # noqa: UP031 - the old operator too
        "str.format": ["{} {!r}".format(held.held, held.held)],  # noqa: UP032 - str.format too
    }
    assert LeakCheck(held).found_in(shown) == []
    assert {text for texts in shown.values() for text in texts} <= {
        mask,
        f"{mask} {mask}",
    }


def test_reveal_returns_the_key_and_forget_keeps_it() -> None:
    planted = secrets.token_hex(20)
    held = Secret("fred", planted)
    revealed = held.reveal()  # nosemgrep: secret-reveal - the test of reveal itself
    same = revealed == planted
    assert same
    held.forget()
    still = held.reveal() == planted  # nosemgrep: secret-reveal - forget keeps the key
    assert still
    assert held.provider == "fred"


def test_equality_compares_provider_and_key() -> None:
    planted = secrets.token_hex(20)
    first, second = Secret("fred", planted), Secret("fred", planted)
    other_key = Secret("fred", secrets.token_hex(20))
    other_provider = Secret("bls", planted)
    outcomes = (
        first == second,
        first != other_key,
        first != other_provider,
        first != planted,
        hash(first) == hash(second) == hash(other_key),
    )
    assert outcomes == (True, True, True, True, True)


def test_pickling_is_refused_under_every_protocol() -> None:
    held = canary()
    refusals = []
    for protocol in range(6):
        with pytest.raises(TypeError, match="cannot be pickled"):
            held.held.__reduce_ex__(protocol)
        refusals.append(protocol)
    with pytest.raises(TypeError, match="cannot be pickled"):
        held.held.__reduce__()
    with pytest.raises(TypeError, match="cannot be pickled"):
        held.held.__getstate__()
    assert refusals == [0, 1, 2, 3, 4, 5]


def test_copies_are_the_same_object() -> None:
    held = canary().held
    assert copy.copy(held) is held
    assert copy.deepcopy({"key": held})["key"] is held


def test_json_and_canonical_json_refuse_it_without_the_key() -> None:
    held = canary()
    messages = {}
    with pytest.raises(TypeError) as plain:
        json.dumps({"key": held.held})
    messages["json"] = [str(plain.value)]
    with pytest.raises(TypeError, match="cannot represent a Secret") as canonical:
        canonical_json({"key": held.held})
    messages["canonical"] = [str(canonical.value)]
    assert LeakCheck(held).found_in(messages) == []


def test_it_is_immutable_and_cannot_be_subclassed() -> None:
    held = canary().held
    with pytest.raises(AttributeError, match="immutable"):
        held._value = "x"  # noqa: SLF001  # ty: ignore[invalid-assignment]
    with pytest.raises(AttributeError, match="immutable"):
        del held._provider  # noqa: SLF001  # ty: ignore[invalid-assignment]
    with pytest.raises(TypeError):
        vars(held)
    with pytest.raises(TypeError, match="cannot be subclassed"):
        type("Unmasked", (Secret,), {})  # ty: ignore[subclass-of-final-class]


@pytest.mark.parametrize(
    ("make", "problem"),
    [
        (lambda: "", "is empty"),
        (lambda: secrets.token_hex(3)[:7], "shorter than 8"),
        (lambda: "a" * (MAX_KEY_LENGTH + 1), "longer than"),
        (lambda: secrets.token_hex(6) + " " + secrets.token_hex(6), "space"),
        (lambda: secrets.token_hex(6) + "\t" + secrets.token_hex(6), "control"),
        (lambda: secrets.token_hex(6) + "é" + secrets.token_hex(6), "non-ASCII"),
    ],
)
def test_unusable_keys_are_refused_without_the_value(
    make: Callable[[], str], problem: str
) -> None:
    value = make()
    with pytest.raises(CredentialError, match=problem) as refused:
        Secret("fred", value)
    assert isinstance(refused.value, PermissionError)
    assert refused.value.provider == "fred"
    if len(value) >= MIN_KEY_LENGTH:
        texts = {"message": [str(refused.value)]}
        leaked = [name for name, found in texts.items() if value in found[0]]
        assert leaked == []


def test_key_problem_names_the_type_and_accepts_a_key() -> None:
    assert key_problem(12345678) == "must be text, not int"
    assert key_problem(secrets.token_hex(4)) is None
    assert key_problem("!" * MIN_KEY_LENGTH) is None


def test_a_bad_provider_id_is_an_input_error() -> None:
    with pytest.raises(InputError, match="snake_case"):
        Secret("Not An Id", secrets.token_hex(8))


def test_creating_registers_the_key_and_forget_withdraws_it() -> None:
    planted = secrets.token_hex(20)
    text = f"GET /v1/series?id=GDP&k={planted}"
    before = redaction.scrub_text(text) == text
    held = Secret("fred", planted)
    masked = redaction.scrub_text(text) == "GET /v1/series?id=GDP&k=[redacted]"
    held.forget()
    held.forget()
    after = redaction.scrub_text(text) == text
    assert (before, masked, after) == (True, True, True)


def test_two_secrets_with_one_key_are_withdrawn_independently() -> None:
    planted = secrets.token_hex(20)
    first, second = Secret("fred", planted), Secret("fred", planted)
    first.forget()
    still_masked = planted not in redaction.scrub_text(planted)
    second.forget()
    unmasked = redaction.scrub_text(planted) == planted
    assert (still_masked, unmasked) == (True, True)
