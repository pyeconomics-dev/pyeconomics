# tests/surfaces/test_registry_export.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""registry.json: every model, deterministic, valid, with no trace of the machine.

The installed catalog is exported once per module, since an export runs every
model's first example. The rules for a failing example, a missing extra and a
missing chart use the toy catalogs (tests/registry/), installed as the registry
an entry point would give; a bound model uses the scripted providers
(tests/data/bindings/bound_support.py) and must bind nothing.
"""

from __future__ import annotations

import getpass
import json
import re
import socket
import sys
import time
from pathlib import Path
from typing import Any

import bound_support as bs
import pytest
import toy_models as tm
import toy_results_models as rm
from extra_gaps import excluded_gap
from jsonschema import Draft202012Validator, ValidationError
from leakcheck import LeakCheck, canary

import pyeconomics
from pyeconomics import registry
from pyeconomics.core import (
    Example,
    MissingOptionalDependencyError,
    Model,
    RegistryError,
)
from pyeconomics.core import registry as core_registry
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.describe import DESCRIPTION_KEYS
from pyeconomics.surfaces.registry_export import (
    REGISTRY_FORMAT,
    registry_document,
    write_registry,
)
from pyeconomics.surfaces.registry_schema import REGISTRY_SCHEMA

ENTRY_KEYS = (*DESCRIPTION_KEYS, "example_result", "example_figure")
#: A generous bound on one export: it runs each model's first example once, and
#: describes each model (whose card runs it again). Locally it takes seconds.
EXPORT_SECONDS = 120.0
#: Account names that are also ordinary words in the cards ("user-supplied"); the
#: home-directory check still finds a path that holds them.
GENERIC_USERS = frozenset({"root", "user"})


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    """The installed catalog's document, exported once for the module."""
    return registry_document()


def install(monkeypatch: pytest.MonkeyPatch, *models: Model[Any, Any]) -> None:
    """Make these toy models the installed registry."""
    monkeypatch.setattr(core_registry._CACHE, "registry", tm.toy_registry(*models))  # noqa: SLF001


def without_figures(document: dict[str, Any]) -> dict[str, Any]:
    models = [{**entry, "example_figure": None} for entry in document["models"]]
    return {**document, "models": models}


# --- the installed catalog ----------------------------------------------------


def test_every_registered_model_is_described_in_id_order(
    document: dict[str, Any],
) -> None:
    assert document["format"] == REGISTRY_FORMAT == 1
    assert document["pyeconomics"] == pyeconomics.__version__
    ids = [entry["id"] for entry in document["models"]]
    assert ids == sorted(ids) == list(registry.ids())
    for entry in document["models"]:
        assert tuple(entry) == ENTRY_KEYS, entry["id"]


def test_each_entry_holds_describe_and_its_first_example_run(
    document: dict[str, Any],
) -> None:
    for entry in document["models"]:
        model_id = entry["id"]
        described = registry.describe(model_id)
        assert {key: entry[key] for key in DESCRIPTION_KEYS} == described, model_id
        result = entry["example_result"]
        if result is None:
            # Only where an extra's marker leaves its library out (the Wheel rule).
            assert excluded_gap(registry.get(model_id)) is not None, model_id
            continue
        assert result["model_id"] == model_id
        assert result["inputs"] == entry["examples"][0]["inputs"]
        assert result["manifest"]["data_sources"] == [], model_id


def test_the_document_validates_against_the_registry_schema(
    document: dict[str, Any],
) -> None:
    Draft202012Validator.check_schema(REGISTRY_SCHEMA)
    Draft202012Validator(REGISTRY_SCHEMA).validate(document)
    # The document is canonical JSON as it stands.
    assert json.loads(canonical_json(document)) == document


def test_a_figure_has_no_template_and_draws_the_result(
    document: dict[str, Any],
) -> None:
    drawn = [entry for entry in document["models"] if entry["example_figure"]]
    assert drawn, "no catalog model drew its first example"
    for entry in drawn:
        figure = entry["example_figure"]
        assert "template" not in figure["layout"]
        outputs = entry["example_result"]["outputs"]
        names = {trace["name"] for trace in figure["data"]}
        assert names <= set(outputs), entry["id"]


def test_figures_false_omits_the_figures_and_nothing_else(
    document: dict[str, Any],
) -> None:
    plain = registry_document(figures=False)
    assert all(entry["example_figure"] is None for entry in plain["models"])
    assert canonical_json(plain) == canonical_json(without_figures(document))


# --- the file -------------------------------------------------------------------


def test_two_exports_from_different_directories_are_byte_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = tmp_path / "first" / "deeper", tmp_path / "second"
    for directory in (first, second):
        directory.mkdir(parents=True)
    monkeypatch.chdir(first)
    write_registry(first / "registry.json")
    monkeypatch.chdir(second)
    write_registry("registry.json")
    one = (first / "registry.json").read_bytes()
    assert one == (second / "registry.json").read_bytes()
    assert b"\r" not in one
    assert not one.endswith(b"\n")
    assert one == canonical_json(json.loads(one, parse_int=float))


def _needles(directory: Path) -> dict[str, str]:
    """Name each machine value an export must not hold, without printing it."""
    found = {
        "directory": str(directory),
        "directory (posix)": directory.as_posix(),
        "directory (JSON)": json.dumps(str(directory))[1:-1],
        "home": str(Path.home()),
        "home (posix)": Path.home().as_posix(),
        "working directory": str(Path.cwd()),
    }
    host = socket.gethostname()
    if host:
        found["hostname"] = rf"\b{re.escape(host)}\b"
    user = getpass.getuser()
    if user and user not in GENERIC_USERS:
        found["user name"] = rf"\b{re.escape(user)}\b"
    return {
        name: value if name in {"hostname", "user name"} else re.escape(value)
        for name, value in found.items()
    }


def test_the_file_holds_no_path_hostname_or_user_name(tmp_path: Path) -> None:
    target = tmp_path / "export" / "registry.json"
    target.parent.mkdir()
    write_registry(target)
    text = target.read_bytes().decode("utf-8")
    # Names only: pytest must not print a path or an account in a failure.
    present = [
        name
        for name, pattern in _needles(target.parent).items()
        if re.search(pattern, text)
    ]
    assert present == []


def test_the_export_binds_nothing_and_reads_no_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pyeconomics.data import bindings  # noqa: PLC0415
    from pyeconomics.data.transport import http  # noqa: PLC0415

    def refuse(*_args: object, **_kwargs: object) -> None:
        msg = "the registry export must not reach the data layer's sources"
        raise AssertionError(msg)

    monkeypatch.setattr(bindings, "bind_model", refuse)
    monkeypatch.setattr(http, "resolve_key", refuse)
    key = canary("fred")
    monkeypatch.setenv("FRED_API_KEY", key.value)
    write_registry(tmp_path / "registry.json")
    check = LeakCheck(key)
    check.add("registry.json", (tmp_path / "registry.json").read_bytes())
    check.assert_clean()


def test_the_export_time_is_recorded_and_bounded(
    tmp_path: Path,
    record_property: Any,  # noqa: ANN401 - pytest's callable
) -> None:
    start = time.perf_counter()
    write_registry(tmp_path / "registry.json")
    seconds = time.perf_counter() - start
    record_property("registry_export_seconds", round(seconds, 3))
    assert seconds < EXPORT_SECONDS


# --- the rules, on toy catalogs ---------------------------------------------------


def test_a_failing_first_example_fails_the_export_naming_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken = tm.variant(
        rm.failing,
        examples=(Example(name="bad", inputs={"x": 0.5, "mode": "domain"}),),
    )
    install(monkeypatch, rm.one_chart, broken)
    with pytest.raises(
        RegistryError, match=r"^foundations\.toy_failing: .*DomainError"
    ):
        registry_document()


def test_a_missing_extra_of_the_models_own_leaves_no_example_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(monkeypatch, tm.needs_extra, tm.zero_coupon)
    entries = {entry["id"]: entry for entry in registry_document()["models"]}
    gap = entries["econometrics.toy_extra"]
    assert gap["example_result"] is None
    assert gap["example_figure"] is None
    assert entries["fixed_income.toy_zero_coupon"]["example_result"] is not None
    Draft202012Validator(REGISTRY_SCHEMA).validate(registry_document())


def test_another_extra_missing_is_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def needs_other(_inputs: tm.ZeroCouponInputs) -> tm.ZeroCouponOutputs:
        library = "other_library"
        raise MissingOptionalDependencyError(library, extra="other")

    install(monkeypatch, Model(tm.needs_extra.spec, needs_other))
    with pytest.raises(RegistryError, match=r"^econometrics\.toy_extra: .*other"):
        registry_document()


def test_the_first_applicable_chart_is_drawn_without_its_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(monkeypatch, rm.growth, rm.no_chart, rm.one_chart)
    entries = {entry["id"]: entry for entry in registry_document()["models"]}
    figure = entries["foundations.toy_growth"]["example_figure"]
    assert figure["layout"]["title"]["text"] == rm.growth.spec.charts[0].title
    assert "template" not in figure["layout"]
    assert entries["foundations.toy_no_chart"]["example_figure"] is None
    assert entries["foundations.toy_one_chart"]["example_figure"] is not None


def test_without_plotly_every_figure_is_null(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, rm.growth, rm.one_chart)
    monkeypatch.setitem(sys.modules, "plotly", None)
    monkeypatch.setitem(sys.modules, "plotly.graph_objects", None)
    document = registry_document()
    assert [entry["example_figure"] for entry in document["models"]] == [None, None]
    assert all(entry["example_result"] for entry in document["models"])


def test_a_bound_model_runs_its_explicit_example_without_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pyeconomics.data import bindings  # noqa: PLC0415
    from pyeconomics.data import registry as provider_registry  # noqa: PLC0415

    def refuse(*_args: object, **_kwargs: object) -> None:
        msg = "the registry export must not bind"
        raise AssertionError(msg)

    monkeypatch.setattr(core_registry._CACHE, "registry", bs.model_registry())  # noqa: SLF001
    monkeypatch.setattr(provider_registry._CACHE, "registry", bs.world())  # noqa: SLF001
    monkeypatch.setattr(bindings, "bind_model", refuse)
    document = registry_document()
    assert any(entry["bindings"] for entry in document["models"])
    for entry in document["models"]:
        assert entry["example_result"]["manifest"]["data_sources"] == []
    Draft202012Validator(REGISTRY_SCHEMA).validate(document)


# --- the schema ---------------------------------------------------------------------


def test_the_schema_requires_every_entry_key_and_allows_no_other() -> None:
    model = REGISTRY_SCHEMA["$defs"]["model"]
    assert tuple(model["required"]) == ENTRY_KEYS
    assert model["additionalProperties"] is False
    assert REGISTRY_SCHEMA["$id"] == "https://pyeconomics.dev/schemas/registry/1.json"


@pytest.mark.parametrize(
    "spoil",
    [
        lambda entry: entry.update(surprise=True),
        lambda entry: entry.pop("card"),
        lambda entry: entry.update(
            example_figure={"data": [], "layout": {"template": {}}}
        ),
        lambda entry: entry.update(evidence="anecdotal"),
    ],
    ids=["extra-key", "missing-key", "template", "evidence"],
)
def test_a_spoiled_entry_fails_validation(
    monkeypatch: pytest.MonkeyPatch,
    spoil: Any,  # noqa: ANN401 - a test lambda
) -> None:
    install(monkeypatch, rm.one_chart)
    document = registry_document()
    spoil(document["models"][0])
    with pytest.raises(ValidationError):
        Draft202012Validator(REGISTRY_SCHEMA).validate(document)
