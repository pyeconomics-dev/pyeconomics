# tests/surfaces/test_problems.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The error table: one row per error class, and problems that hold no secret.

ADR-0012 decision 4. The walking test fails on any ``PyeconomicsError`` subclass
in core, the data layer or the surfaces without its own row; the mapping is the
one the maintainer accepted; and every detail is fixed text or a scrubbed message.
"""

from __future__ import annotations

import importlib
import inspect
import json
import logging
import sys
from typing import TYPE_CHECKING

import pytest
import toy_models as toys
from leakcheck import canary

import pyeconomics.surfaces
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
    ConfigError,
    DataError,
    LicenceError,
    RateLimitError,
    ResponseError,
    TransportError,
)
from pyeconomics.surfaces import problems
from pyeconomics.surfaces.budgets import BudgetExceededError
from pyeconomics.surfaces.codec import InputTooLargeError
from pyeconomics.surfaces.problems import (
    MAX_DETAIL_LENGTH,
    MAX_FIELD_ERRORS,
    ROWS,
    Problem,
    problem_for,
    report,
    row_for,
    scrub,
)

if TYPE_CHECKING:
    from types import ModuleType

#: The modules whose error classes the table must name, one row each.
ERROR_MODULES = ("pyeconomics.core.errors", "pyeconomics.data.errors")

#: The mapping ADR-0012 decision 4 records: slug, HTTP status, exit code.
ACCEPTED = {
    "InputError": ("invalid-input", 422, 3),
    "InputTooLargeError": ("input-too-large", 413, 3),
    "DomainError": ("no-defined-result", 422, 4),
    "ConvergenceError": ("no-convergence", 422, 4),
    "ModelNotFoundError": ("model-not-found", 404, 5),
    "ProviderNotFoundError": ("provider-not-found", 404, 5),
    "ConceptNotFoundError": ("concept-not-found", 404, 5),
    "SeriesNotFoundError": ("series-not-found", 404, 5),
    "LicenceError": ("licence-refused", 403, 6),
    "CredentialError": ("credential-unavailable", 503, 7),
    "TransportError": ("upstream-unavailable", 502, 7),
    "ResponseError": ("upstream-invalid-response", 502, 7),
    "RateLimitError": ("upstream-rate-limited", 503, 7),
    "OfflineError": ("offline-cache-miss", 503, 7),
    "DataError": ("data-unavailable", 422, 7),
    "MissingOptionalDependencyError": ("missing-extra", 501, 8),
    "BudgetExceededError": ("budget-exceeded", 422, 1),
    "RegistryError": ("registry-error", 500, 1),
    "ConfigError": ("invalid-configuration", 500, 1),
    "PyeconomicsError": ("pyeconomics-error", 500, 1),
    "Exception": ("internal-error", 500, 1),
}


def _surface_modules() -> list[ModuleType]:
    package = pyeconomics.surfaces
    names = ("budgets", "codec", "envelope", "invoke", "problems")
    return [importlib.import_module(f"{package.__name__}.{name}") for name in names]


def _error_classes() -> list[type[PyeconomicsError]]:
    modules = [importlib.import_module(name) for name in ERROR_MODULES]
    modules += _surface_modules()
    found: dict[str, type[PyeconomicsError]] = {}
    for module in modules:
        for _, value in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(value, PyeconomicsError)
                and value.__module__ == module.__name__
            ):
                found[f"{value.__module__}.{value.__qualname__}"] = value
    return [found[key] for key in sorted(found)]


# --- the table ------------------------------------------------------------------------


def test_every_error_class_has_its_own_row() -> None:
    classes = _error_classes()
    assert len(classes) >= 19
    rows = {row.error for row in ROWS}
    missing = [
        f"{cls.__module__}.{cls.__qualname__}"
        for cls in classes
        if f"{cls.__module__}.{cls.__qualname__}" not in rows
    ]
    assert missing == []


def test_every_row_names_a_class_that_exists() -> None:
    for row in ROWS:
        module, _, name = row.error.rpartition(".")
        assert inspect.isclass(getattr(importlib.import_module(module), name)), row


def test_the_table_is_the_accepted_mapping() -> None:
    table = {row.error_name: (row.slug, row.status, row.exit_code) for row in ROWS}
    assert table == ACCEPTED


def test_slugs_are_unique_and_types_are_their_uris() -> None:
    slugs = [row.slug for row in ROWS]
    assert len(set(slugs)) == len(slugs)
    for row in ROWS:
        assert row.type_uri == f"https://pyeconomics.dev/problems/{row.slug}"
        assert 400 <= row.status <= 599
        assert 1 <= row.exit_code <= 8
        assert row.title


def test_an_error_takes_the_row_of_its_nearest_class() -> None:
    class ProviderQuirkError(DataError):
        pass

    class Interrupted(KeyboardInterrupt):
        pass

    assert row_for(ProviderQuirkError("odd")).slug == "data-unavailable"
    assert row_for(
        LicenceError("no", provider="x", licence=LicenceClass.BYOK)
    ).slug == ("licence-refused")
    assert row_for(PermissionError("x")).slug == "internal-error"
    assert row_for(Interrupted()).slug == "internal-error"


# --- problems -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "slug", "detail"),
    [
        (DomainError("growth must be below the return"), "no-defined-result", None),
        (ConvergenceError("no sign change"), "no-convergence", None),
        (ModelNotFoundError("a.b"), "model-not-found", None),
        (RegistryError("a duplicate id"), "registry-error", None),
        (
            MissingOptionalDependencyError("statsmodels", extra="econometrics"),
            "missing-extra",
            (
                "this feature needs statsmodels; install it with: pip install "
                "'pyeconomics[econometrics]'"
            ),
        ),
        (ConfigError("mode must be library or hosted"), "invalid-configuration", None),
        (InputTooLargeError(20, 10), "input-too-large", None),
        (BudgetExceededError("risk.toy", 30.0), "budget-exceeded", None),
        (InputError("rate must be positive"), "invalid-input", "rate must be positive"),
        (
            PyeconomicsError(),
            "pyeconomics-error",
            "pyeconomics could not complete the request",
        ),
    ],
)
def test_a_known_error_keeps_its_message_as_the_detail(
    error: PyeconomicsError, slug: str, detail: str | None
) -> None:
    problem = problem_for(error)
    assert problem.slug == slug
    assert problem.detail == (detail or str(error))
    assert problem.errors == ()
    assert (problem.licence, problem.terms, problem.retry_after) == (None, None, None)


def test_an_unknown_exception_gets_a_fixed_detail() -> None:
    problem = problem_for(ValueError("C:/Users/someone/data.csv holds 42"))
    assert problem.slug == "internal-error"
    assert problem.detail == "An unexpected error stopped the request."
    assert (problem.status, problem.exit_code) == (500, 1)


def test_an_upstream_failure_names_only_the_provider() -> None:
    transport = problem_for(
        TransportError(
            "HTTPSConnectionPool(host='api.x.org', port=443)", provider="bls"
        )
    )
    assert transport.detail == "The request to bls failed; try again later."
    response = problem_for(ResponseError("<html>gateway</html>"))
    assert (
        response.detail == "the data source sent a response pyeconomics could not read."
    )
    limited = problem_for(RateLimitError("daily limit", provider="bls", retry_after=30))
    assert limited.detail == "bls's rate limit still held after the permitted retries."
    assert limited.retry_after == 30.0
    assert problem_for(RateLimitError("limit", provider="bls")).retry_after is None


def test_a_licence_refusal_carries_the_class_and_the_terms_page() -> None:
    terms = "https://fred.stlouisfed.org/docs/api/terms_of_use.html"
    error = LicenceError(
        "hosted mode serves only hosted-safe and user-supplied data",
        provider="fred",
        licence=LicenceClass.LIBRARY_ONLY,
        terms_url=terms,
    )
    problem = problem_for(error)
    assert (problem.status, problem.exit_code) == (403, 6)
    assert problem.detail == (
        "fred is library-only: hosted mode serves only hosted-safe and "
        "user-supplied data"
    )
    assert (problem.licence, problem.terms) == ("library-only", terms)


@pytest.mark.parametrize(
    "terms",
    [
        "http://example.org/terms",
        "https://example.org/terms?x=1",
        "https://someone@example.org/terms",
        "https://example.org:8443/terms",
        "https://example.org:99999/terms",
        "https:///terms",
    ],
)
def test_a_terms_url_that_is_not_a_plain_page_is_dropped(terms: str) -> None:
    error = LicenceError(
        "no", provider="x", licence=LicenceClass.PREMIUM_LOCAL, terms_url=terms
    )
    problem = problem_for(error)
    assert problem.terms is None
    assert "example.org" not in problem.detail


def test_invalid_inputs_list_their_field_errors_without_values() -> None:
    with pytest.raises(InputError) as caught:
        toys.zero_coupon.validate_inputs(
            {"face_value": "C:/Users/someone/x", "rate": 5, "years": 10, "extra": 1}
        )
    problem = problem_for(caught.value)
    assert problem.slug == "invalid-input"
    assert [error.location for error in problem.errors] == [
        ("face_value",),
        ("rate",),
        ("extra",),
    ]
    assert problem.detail.startswith("The inputs failed validation: face_value: ")
    assert problem.detail.endswith(".")
    body = json.dumps(problem.to_dict())
    assert "someone" not in body
    listed = problem.to_dict()["errors"]
    assert isinstance(listed, list)
    assert {key for error in listed for key in error} == {"loc", "msg", "type"}
    assert "errors.pydantic.dev" not in body


def test_many_field_errors_are_capped_and_counted() -> None:
    returns = ["not a number"] * (MAX_FIELD_ERRORS + 20)
    with pytest.raises(InputError) as caught:
        toys.mean_return.validate_inputs({"returns": returns})
    problem = problem_for(caught.value)
    total = len(caught.value.errors)
    assert total > MAX_FIELD_ERRORS
    assert len(problem.errors) == MAX_FIELD_ERRORS
    assert problem.detail.endswith(f"; and {total - 3} more.")
    assert problem.errors[0].location == ("returns", 0)


def test_a_union_error_without_a_field_is_located_at_the_inputs() -> None:
    with pytest.raises(InputError) as caught:
        toys.time_value.validate_inputs({})
    problem = problem_for(caught.value)
    assert problem.errors
    assert problem.detail.startswith("The inputs failed validation: ")


def test_an_error_that_cannot_print_gets_its_title() -> None:
    class UnprintableError(DataError):
        def __str__(self) -> str:
            raise RuntimeError

    problem = problem_for(UnprintableError("x"))
    assert problem.detail == "The data cannot answer this request"


def test_the_problem_body_is_rfc_9457_with_extensions_only_when_set() -> None:
    plain = problem_for(DomainError("no result"))
    assert plain.to_dict() == {
        "type": "https://pyeconomics.dev/problems/no-defined-result",
        "title": "The inputs have no defined result",
        "status": 422,
        "detail": "no result",
    }
    assert json.loads(plain.to_json()) == plain.to_dict()
    assert plain.to_json().startswith(b'{"detail":')
    assert plain.cli_message == "no-defined-result: no result"
    limited = problem_for(RateLimitError("x", provider="bls", retry_after=2.5))
    assert limited.to_dict()["retry_after"] == 2.5
    assert isinstance(limited, Problem)


# --- scrubbing ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("GET https://api.example.org/v1?id=1 failed", "GET <url> failed"),
        ("(see ftp://files.example.org/a.zip).", "(see <url>)."),
        (
            "set it (https://pyeconomics.readthedocs.io/en/main/data/keys.html)",
            "set it (https://pyeconomics.readthedocs.io/en/main/data/keys.html)",
        ),
        (
            "https://pyeconomics.dev/problems/x#top?a=1",
            "https://pyeconomics.dev/problems/x",
        ),
        ("https://someone@pyeconomics.dev/x", "<url>"),
        ("http://pyeconomics.dev/x", "<url>"),
        ("https://pyeconomics.dev:99999/x", "<url>"),
        ("Pool(host='api.example.org', port=443)", "Pool(host=<host>, port=443)"),
        ('host="10.0.0.1" refused', "host=<host> refused"),
        ("read C:\\Users\\someone\\x.toml", "read <path>"),
        ("read c:/Users/someone/x.toml", "read <path>"),
        ("read \\\\server\\share\\x.toml", "read <path>"),
        ("read /home/someone/.config/x.toml", "read <path>"),
        ("read ~/x.toml now", "read <path> now"),
        ("read ./x.toml and ../y", "read <path> and <path>"),
        ("'/etc/passwd'", "'<path>'"),
        ("debt/equity and 1/2 and a / b", "debt/equity and 1/2 and a / b"),
        ("oecd:OECD.SDD/DSD@DF/GBR.M", "oecd:OECD.SDD/DSD@DF/GBR.M"),
        ("a\n\tb   c", "a b c"),
    ],
)
def test_scrub(text: str, expected: str) -> None:
    assert scrub(text) == expected


def test_scrub_cuts_a_long_detail() -> None:
    assert scrub("x" * (MAX_DETAIL_LENGTH + 5)) == "x" * MAX_DETAIL_LENGTH + "..."


def test_scrub_replaces_registered_secrets_and_credential_parameters() -> None:
    planted = canary()
    text = scrub(f"key {planted.value} and /v1?api_key=abc&id=2")
    assert planted.value not in text
    assert "abc" not in text


def test_scrub_needs_no_data_layer_when_none_is_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A secret is registered only in pyeconomics.data.redaction, so without it
    # loaded there is none to replace; URLs and paths are still removed.
    monkeypatch.delitem(sys.modules, "pyeconomics.data.redaction")
    assert scrub("GET https://api.example.org/x for /home/someone/y") == (
        "GET <url> for <path>"
    )


# --- report ---------------------------------------------------------------------------


def test_report_logs_one_scrubbed_record(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG, logger="pyeconomics.surfaces"):
        problem = report(ValueError("/home/someone/x"))
        report(DomainError("no result"))
    assert problem.slug == "internal-error"
    internal = "internal-error (500, ValueError): An unexpected error stopped the"
    assert [(r.levelno, r.getMessage()) for r in caplog.records] == [
        (logging.ERROR, f"{internal} request."),
        (logging.INFO, "no-defined-result (422, DomainError): no result"),
    ]
    assert all(r.exc_info is None for r in caplog.records)


def test_report_logs_on_a_given_logger(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("pyeconomics.test_report")
    with caplog.at_level(logging.INFO, logger=logger.name):
        report(ModelNotFoundError("a.b"), logger=logger)
    assert [r.name for r in caplog.records] == [logger.name]
    assert problems.TYPE_BASE in problem_for(DomainError("x")).type_uri
