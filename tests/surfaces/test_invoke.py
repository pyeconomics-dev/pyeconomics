# tests/surfaces/test_invoke.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The one invocation path: the same bytes as ``pyeconomics.run`` (ADR-0012 2).

Data-free runs use the toy catalog (tests/registry/toy_models.py) and bound runs
the scripted providers (tests/data/bindings/bound_support.py), each installed as
the registry an entry point would give. Whatever form the inputs arrive in, and
whether or not data is bound first, ``invoke`` returns a result whose canonical
JSON equals ``pyeconomics.run``'s.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import TYPE_CHECKING

import bound_support as bs
import pytest
import toy_models as toys

import pyeconomics
from pyeconomics.core import (
    InputError,
    LicenceClass,
    ModelNotFoundError,
    PyeconomicsDeprecationWarning,
    VintagePolicy,
)
from pyeconomics.core import registry as core_registry
from pyeconomics.data import Mode, cache
from pyeconomics.surfaces import BindRequest, invoke
from pyeconomics.surfaces.codec import InputTooLargeError
from pyeconomics.surfaces.envelope import canonical_bytes

if TYPE_CHECKING:
    from collections.abc import Iterator

ZERO = "fixed_income.toy_zero_coupon"
UNEMPLOYMENT = "macro.toy_unemployment"
PAST = dt.date(2024, 3, 20)


@pytest.fixture
def toy_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the toy models the installed registry."""
    monkeypatch.setattr(core_registry._CACHE, "registry", toys.toy_registry())  # noqa: SLF001


@pytest.fixture
def bound_world(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Make the toy bound models and the scripted providers the installed ones.

    The cache is bypassed, so a second bind of a series the terms let the cache
    keep reads the source as the first did, and the two manifests compare equal.
    """
    from pyeconomics.data import registry as provider_registry  # noqa: PLC0415

    monkeypatch.setattr(core_registry._CACHE, "registry", bs.model_registry())  # noqa: SLF001
    monkeypatch.setattr(provider_registry._CACHE, "registry", bs.world())  # noqa: SLF001
    with cache.bypass():
        yield


# --- data-free runs -------------------------------------------------------------------


@pytest.mark.usefixtures("toy_catalog")
@pytest.mark.parametrize(
    "inputs",
    [
        {"face_value": 100, "rate": 0.05, "years": 10},
        '{"face_value": 100, "rate": 0.05, "years": 10}',
        b'{"years": 10, "rate": 0.05, "face_value": 100}',
        ["face_value=100", "rate=0.05", "years=10"],
    ],
    ids=["mapping", "text", "bytes", "pairs"],
)
def test_every_input_form_gives_pyeconomics_runs_bytes(inputs: object) -> None:
    expected = pyeconomics.run(ZERO, {"face_value": 100, "rate": 0.05, "years": 10})
    assert canonical_bytes(invoke(ZERO, inputs)) == expected.to_json().encode()


@pytest.mark.usefixtures("toy_catalog")
def test_a_family_and_a_warning_round_trip() -> None:
    family = ["calculation=future_value", "present_value=100", "rate=0.05", "years=2"]
    expected = pyeconomics.run(
        "foundations.toy_time_value",
        {"calculation": "future_value", "present_value": 100, "rate": 0.05, "years": 2},
    )
    assert invoke("foundations.toy_time_value", family).to_json() == expected.to_json()
    flat = invoke("foundations.toy_mean_return", {"returns": [0, 0]})
    assert [w.code for w in flat.warnings] == ["all_zero"]


@pytest.mark.usefixtures("toy_catalog")
def test_an_alias_warns_at_the_caller_and_runs_the_canonical_model() -> None:
    inputs = {"calculation": "present_value", "future_value": 100, "rate": 0.05}
    with pytest.warns(PyeconomicsDeprecationWarning) as caught:
        result = invoke("foundations.toy_tvm", {**inputs, "years": 1})
    assert result.model_id == "foundations.toy_time_value"
    assert caught[0].filename == __file__


@pytest.mark.usefixtures("toy_catalog")
def test_no_inputs_are_validated_by_the_model() -> None:
    with pytest.raises(InputError) as caught:
        invoke(ZERO)
    assert {e["loc"][0] for e in caught.value.errors} == {"face_value", "rate", "years"}


@pytest.mark.usefixtures("toy_catalog")
def test_failures_surface_as_the_table_expects() -> None:
    with pytest.raises(ModelNotFoundError):
        invoke("fixed_income.no_such_model", {})
    with pytest.raises(InputError, match="takes a number, not a boolean"):
        invoke(ZERO, ["rate=true"])
    with pytest.raises(InputError, match="mapping, JSON text or bytes"):
        invoke(ZERO, bs.bound_to("us.unemployment.rate"))
    huge = json.dumps({"face_value": 100, "pad": "x" * (17 * 1024 * 1024)})
    with pytest.raises(InputTooLargeError):
        invoke(ZERO, huge)


# --- bound runs -----------------------------------------------------------------------


@pytest.mark.usefixtures("bound_world")
def test_a_bound_run_gives_the_bytes_of_run_after_bind() -> None:
    expected = pyeconomics.run(
        UNEMPLOYMENT, pyeconomics.bind(UNEMPLOYMENT, as_of=PAST, weight=2.0)
    )
    result = invoke(UNEMPLOYMENT, {"weight": 2.0}, bind=BindRequest(as_of="2024-03-20"))
    assert canonical_bytes(result) == expected.to_json().encode()
    assert [record.provider for record in result.manifest.data_sources] == ["fred"]


@pytest.mark.usefixtures("bound_world")
def test_a_bound_window_and_a_supplied_value_round_trip() -> None:
    window = "macro.toy_unemployment_window"
    expected = pyeconomics.run(window, pyeconomics.bind(window))
    assert invoke(window, None, bind=BindRequest()).to_json() == expected.to_json()
    supplied = invoke(UNEMPLOYMENT, ["unemployment=0.05"], bind=BindRequest())
    (record,) = supplied.manifest.data_sources
    assert record.licence is LicenceClass.USER_SUPPLIED
    assert supplied.inputs.unemployment == 0.05


@pytest.mark.usefixtures("bound_world")
def test_every_bind_option_reaches_the_bind() -> None:
    request = BindRequest(
        as_of=PAST,
        vintage="latest",
        profile="default",
        concepts={"unemployment": "us.unemployment.rate"},
    )
    expected = pyeconomics.run(
        UNEMPLOYMENT,
        pyeconomics.bind(
            UNEMPLOYMENT,
            as_of=PAST,
            vintage=VintagePolicy.LATEST,
            concepts={"unemployment": "us.unemployment.rate"},
        ),
    )
    assert invoke(UNEMPLOYMENT, {}, bind=request).to_json() == expected.to_json()
    uk = invoke(UNEMPLOYMENT, {}, bind=BindRequest(profile="uk"))
    assert uk.manifest.data_sources[0].provider == "oecd"


@pytest.mark.usefixtures("bound_world")
def test_hosted_mode_reaches_the_bind() -> None:
    expected = pyeconomics.run(
        UNEMPLOYMENT, pyeconomics.bind(UNEMPLOYMENT, as_of=PAST, mode=Mode.HOSTED)
    )
    hosted = invoke(UNEMPLOYMENT, {}, bind=BindRequest(as_of=PAST), mode="hosted")
    assert hosted.to_json() == expected.to_json()
    assert hosted.manifest.data_sources[0].provider == "bls"
    with pytest.raises(InputError, match="mode"):
        invoke(UNEMPLOYMENT, {}, bind=BindRequest(), mode="public")


# --- the bind request -----------------------------------------------------------------


def test_a_bind_request_normalizes_its_fields() -> None:
    request = BindRequest(
        as_of="2019-06-28", vintage="real_time", parameters={"meeting": "2019-06"}
    )
    assert request.as_of == dt.date(2019, 6, 28)
    assert request.vintage is VintagePolicy.REAL_TIME
    assert request.to_dict() == {
        "as_of": "2019-06-28",
        "vintage": "real_time",
        "profile": "default",
        "concepts": {},
        "parameters": {"meeting": "2019-06"},
    }
    assert BindRequest().to_dict()["as_of"] is None
    with pytest.raises(TypeError):
        request.parameters["meeting"] = "2020-01"  # type: ignore[index] # ty: ignore[invalid-assignment]


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"as_of": "28/06/2019"}, "YYYY-MM-DD"),
        ({"as_of": dt.datetime(2019, 6, 28, tzinfo=dt.UTC)}, "a date, not datetime"),
        ({"as_of": 20190628}, "a date, not int"),
        ({"vintage": "newest"}, "vintage"),
        ({"profile": ""}, "profile"),
        ({"concepts": {"unemployment": 5}}, "concept ids"),
        ({"concepts": ["unemployment"]}, "concept ids"),
        ({"parameters": {1: "x"}}, "parameter names"),
    ],
)
def test_a_bad_bind_request_is_refused(fields: dict[str, object], message: str) -> None:
    with pytest.raises(InputError, match=message):
        BindRequest(**fields)  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]
