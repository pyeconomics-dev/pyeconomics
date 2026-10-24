# tests/surfaces/test_problem_canary.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""No key, path, host or upstream URL survives into a problem (ADR-0012 decision 4).

Every error the table maps is raised with a planted key, a planted file path (in
Windows, POSIX and home forms) and a planted upstream URL in its message. The
problem's detail, its JSON body, the command line's message, the traceback the
command line's ``--debug`` prints and the record ``report`` logs are searched
for each of them. A failing assertion names the sinks, never the planted values
(tests/data/leakcheck.py).
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field

import pytest
import toy_models as toys
from leakcheck import Canary, LeakCheck, canary

from pyeconomics.core import (
    ConvergenceError,
    DomainError,
    InputError,
    MissingOptionalDependencyError,
    ModelNotFoundError,
    PyeconomicsError,
    RegistryError,
)
from pyeconomics.core.provenance import LicenceClass
from pyeconomics.data import (
    ConceptNotFoundError,
    ConfigError,
    CredentialError,
    DataError,
    LicenceError,
    OfflineError,
    ProviderNotFoundError,
    RateLimitError,
    ResponseError,
    SeriesNotFoundError,
    TransportError,
)
from pyeconomics.surfaces.budgets import BudgetExceededError
from pyeconomics.surfaces.codec import InputTooLargeError
from pyeconomics.surfaces.problems import ROWS, problem_for, report


@dataclass(frozen=True)
class Plants:
    """A key, three file paths and an upstream URL, each with a random part."""

    key: Canary
    folder: str = field(default_factory=lambda: f"u{secrets.token_hex(6)}")
    host: str = field(default_factory=lambda: f"h{secrets.token_hex(6)}")

    @property
    def text(self) -> str:
        """A message holding every planted value."""
        return (
            f"reading C:\\Users\\{self.folder}\\pyeconomics.toml, "
            f"/home/{self.folder}/.config/pyeconomics.toml and "
            f"~/{self.folder}/.env through "
            f"https://api.{self.host}.example.org/v1/series?api_key={self.key.value} "
            f"(HTTPSConnectionPool(host='api.{self.host}.example.org', port=443)) "
            f"with {self.key.value}"
        )

    def needles(self) -> tuple[str, ...]:
        """The key's forms and the random parts of the paths and the host."""
        return (*self.key.needles(), self.folder, self.host)


@pytest.fixture
def plants() -> Plants:
    return Plants(key=canary())


def _errors(text: str) -> list[BaseException]:
    """One error of every class the table maps, each carrying ``text``."""
    library_only = LicenceClass.LIBRARY_ONLY
    return [
        InputError(text),
        InputTooLargeError(len(text), 1),
        DomainError(text),
        ConvergenceError(text),
        ModelNotFoundError(text, close_matches=(text,)),
        ProviderNotFoundError(text, close_matches=(text,)),
        ConceptNotFoundError(text, close_matches=(text,)),
        SeriesNotFoundError("toy", text),
        LicenceError(text, provider="toy", licence=library_only),
        LicenceError(
            text,
            provider="toy",
            licence=library_only,
            terms_url="https://www.example.org/terms",
        ),
        CredentialError(text, provider="toy"),
        TransportError(text, provider="toy"),
        ResponseError(text, provider="toy"),
        RateLimitError(text, provider="toy", retry_after=1.0),
        OfflineError(text, provider="toy"),
        DataError(text),
        MissingOptionalDependencyError("toy_library", note=text),
        BudgetExceededError(text, 2.0),
        RegistryError(text, problems=(text,)),
        ConfigError(text),
        PyeconomicsError(text),
        RuntimeError(text),
    ]


def _validation_error(plants: Plants) -> InputError:
    """An invalid-input error whose values, and one field name, hold the plants."""
    try:
        toys.zero_coupon.validate_inputs(
            {"face_value": plants.text, "rate": plants.text, "years": 1, plants.text: 1}
        )
    except InputError as error:
        return error
    msg = "the inputs validated"
    raise AssertionError(msg)


def _throw(error: BaseException) -> None:
    raise error


def _raised(error: BaseException) -> BaseException:
    """Return the error after raising it, so its traceback has frames."""
    try:
        _throw(error)
    except BaseException as caught:  # noqa: BLE001 - every planted error is caught
        return caught
    raise AssertionError  # pragma: no cover - _throw always raises


def test_no_planted_value_reaches_a_debug_traceback(plants: Plants) -> None:
    from pyeconomics.cli.app import debug_traceback  # noqa: PLC0415 - loads Cyclopts

    check = LeakCheck(plants)
    for error in [*_errors(plants.text), _validation_error(plants)]:
        lines = debug_traceback(_raised(error))
        assert any(line.startswith("Traceback") for line in lines)
        check.add(f"debug:{problem_for(error).slug}", "\n".join(lines))
    check.assert_clean()


def test_every_row_is_planted() -> None:
    planted = {problem_for(error).slug for error in _errors("x")}
    assert planted == {row.slug for row in ROWS}


def test_no_planted_value_reaches_a_problem_a_cli_message_or_a_log(
    plants: Plants,
) -> None:
    check = LeakCheck(plants)
    errors = [*_errors(plants.text), _validation_error(plants)]
    with check.logs("pyeconomics.surfaces"):
        for error in errors:
            problem = report(error)
            check.add(f"detail:{problem.slug}", problem.detail)
            check.add(f"body:{problem.slug}", problem.to_json())
            check.add(f"cli:{problem.slug}", problem.cli_message)
    assert len(check.sinks) > 3 * len(ROWS)
    check.assert_clean()


def test_the_harness_sees_each_planted_value(plants: Plants) -> None:
    check = LeakCheck(plants)
    check.add("raw", plants.text)
    assert check.leaks() == ["raw"]
    for needle in plants.needles():
        probe = LeakCheck(plants)
        probe.add("probe", f"around {needle} here")
        assert probe.leaks() == ["probe"]
