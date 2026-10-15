# tests/providers/test_record_cassettes.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The recorder (scripts/record_cassettes.py), driven by replay instead of the network.

A replay transport stands in for the live source, so the recorder runs offline: it
must reproduce each toy cassette byte for byte from the very responses that cassette
holds, scrub what it records, refuse what the Recording rule forbids and never run
inside a test of its own accord.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import secrets
import sys
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from fakes import FakePool
from leakcheck import LeakCheck, canary
from provider_contract import CASSETTES, load_cassette, replay
from toys import ToyJson, ToyVintage

from pyeconomics.data import LicenceClass, Query, SeriesNotFoundError, registry
from pyeconomics.data.registry import ProviderRegistry
from pyeconomics.data.transport.base import Request, Response
from pyeconomics.data.transport.http import HttpTransport

if TYPE_CHECKING:
    from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "record_cassettes.py"
NOW = dt.datetime(2026, 10, 15, 18, 0, tzinfo=dt.UTC)


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("record_cassettes", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["record_cassettes"] = module
    spec.loader.exec_module(module)
    return module


recorder = load_script()
EVERY_CASE = [
    pytest.param(provider, case, id=f"{provider.info.id}-{case.name}")
    for provider in (ToyJson, ToyVintage)
    for case in provider.cases
]


def case_named(provider: Any, name: str) -> Any:
    return next(c for c in provider.cases if c.name == name)


def library_only(provider: Any) -> Any:
    terms = replace(provider.info.terms, licence=LicenceClass.LIBRARY_ONLY)
    return type("Library", (provider,), {"info": replace(provider.info, terms=terms)})


@pytest.fixture(autouse=True)
def _toys_are_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    toys = ProviderRegistry.from_providers(ToyJson, ToyVintage)
    monkeypatch.setattr(registry, "installed", lambda: toys)


class Dispatch:
    """Answers each request from whichever toy_json cassette records it."""

    def send(self, info: Any, request: Request, *, key: Any = None) -> Response:
        for case in ToyJson.cases:
            if load_cassette("toy_json", case).lookup(request) is not None:
                return replay("toy_json", case).send(info, request)
        raise AssertionError


@pytest.mark.parametrize(("provider", "case"), EVERY_CASE)
def test_recording_a_case_reproduces_its_committed_cassette(
    provider: Any, case: Any
) -> None:
    committed = load_cassette(provider.info.id, case)
    made = recorder.record_case(
        provider(), case, replay(provider.info.id, case), committed.recorded_on
    )
    path = CASSETTES / provider.info.id / f"{case.name}.json"
    assert made.document() == path.read_bytes()
    assert made.synthetic is committed.synthetic


def test_the_recording_time_is_the_given_time_to_the_second() -> None:
    case = case_named(ToyJson, "describe_ok")
    when = dt.datetime(2026, 10, 15, 9, 8, 7, 654321, tzinfo=dt.UTC)
    made = recorder.record_case(ToyJson(), case, replay("toy_json", case), when)
    assert made.recorded_on == when.replace(microsecond=0)


def test_a_library_only_source_is_recorded_through_its_synthesize_hook() -> None:
    case = case_named(ToyVintage, "fetch_all")
    live = Response(
        200,
        json.dumps(
            {
                "series": "TOYGDP",
                "title": "Toy real GDP growth",
                "observations": [
                    {
                        "date": "2008-06-30",
                        "value": "9.99",
                        "realtime_start": "2008-07-30",
                        "realtime_end": "9999-12-31",
                    }
                ],
            }
        ).encode(),
        NOW,
        (("content-type", "application/json"),),
    )

    class Live:
        def send(self, info: Any, request: Request, *, key: Any = None) -> Response:
            return live

    made = recorder.record_case(ToyVintage(), case, Live(), NOW)
    assert made.synthetic is True
    assert "9.99" not in made.document().decode()


def test_a_non_synthetic_source_keeps_its_values() -> None:
    case = case_named(ToyJson, "fetch_ok")
    made = recorder.record_case(ToyJson(), case, replay("toy_json", case), NOW)
    assert made.synthetic is False
    assert "4.50" in made.document().decode()


def test_the_recording_rule_decides_when_a_cassette_is_synthetic() -> None:
    assert recorder.needs_synthetic(ToyVintage)
    assert not recorder.needs_synthetic(ToyJson)
    assert recorder.needs_synthetic(library_only(ToyJson))


def test_a_source_that_must_be_synthetic_but_cannot_synthesize_is_refused() -> None:
    case = case_named(ToyJson, "fetch_ok")
    with pytest.raises(recorder.RecordingError, match="implement synthesize"):
        recorder.record_case(
            library_only(ToyJson)(), case, replay("toy_json", case), NOW
        )


def test_a_case_that_asks_for_too_many_observations_is_refused() -> None:
    greedy = replace(
        case_named(ToyJson, "fetch_ok"),
        argument=Query(series=("TOYRATE",), max_observations=25),
    )
    with pytest.raises(recorder.RecordingError, match="at most 24"):
        recorder.record_case(ToyJson(), greedy, Dispatch(), NOW)


def test_an_error_case_that_does_not_fail_is_refused() -> None:
    ok = case_named(ToyJson, "fetch_ok")
    wrong = replace(ok, expect=SeriesNotFoundError)
    with pytest.raises(
        recorder.RecordingError, match="should have raised SeriesNotFoundError"
    ):
        recorder.record_case(ToyJson(), wrong, replay("toy_json", ok), NOW)


def test_a_success_case_that_fails_is_refused() -> None:
    failing = case_named(ToyJson, "error_not_found")
    unexpected = replace(failing, expect=None)
    with pytest.raises(recorder.RecordingError, match="raised SeriesNotFoundError"):
        recorder.record_case(ToyJson(), unexpected, replay("toy_json", failing), NOW)
    other = replace(failing, expect=SeriesNotFoundError.__mro__[-3])
    with pytest.raises(recorder.RecordingError):
        recorder.record_case(
            ToyJson(),
            replace(other, expect=ValueError),
            replay("toy_json", failing),
            NOW,
        )


def test_a_cassette_that_fails_the_scan_or_the_size_cap_is_not_written(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = case_named(ToyJson, "fetch_ok")
    with monkeypatch.context() as patch:
        patch.setattr(recorder, "scan_text", lambda _text: ["json-web-token"])
        with pytest.raises(recorder.RecordingError, match="json-web-token"):
            recorder.record_case(ToyJson(), case, replay("toy_json", case), NOW)
    with monkeypatch.context() as patch:
        patch.setattr(recorder, "MAX_CASSETTE_BYTES", 100)
        with pytest.raises(recorder.RecordingError, match="at most 100"):
            recorder.record_case(ToyJson(), case, replay("toy_json", case), NOW)


def test_an_invalid_key_case_sends_a_made_up_key_that_is_not_recorded() -> None:
    case = case_named(ToyJson, "error_unauthorized")
    assert case.invalid_key
    seen: list[Any] = []

    class Spy:
        def send(self, info: Any, request: Request, *, key: Any = None) -> Response:
            seen.append(key)
            return replay("toy_json", case).send(info, request)

    made = recorder.record_case(ToyJson(), case, Spy(), NOW)
    assert isinstance(seen[0], str)
    assert len(seen[0]) == 32
    check = LeakCheck(canary("toy_json"))
    check.add("cassette", made.document())
    check.assert_clean()
    assert seen[0] not in made.document().decode()


# --- the command line ---------------------------------------------------------


def test_it_refuses_to_record_inside_a_test(capsys: pytest.CaptureFixture[str]) -> None:
    assert recorder.main(["toy_json"]) == 2
    assert "never part of a test run" in capsys.readouterr().err


def test_it_lists_a_providers_cases(capsys: pytest.CaptureFixture[str]) -> None:
    assert recorder.main(["toy_vintage", "--list"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert "fetch_all\tfetch\tok" in lines
    assert "error_not_found\tfetch\tSeriesNotFoundError" in lines


def test_it_records_the_named_cases_into_a_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = recorder.main(
        ["toy_json", "fetch_ok", "search_ok", "--directory", str(tmp_path)],
        transport=Dispatch(),
    )
    assert status == 0
    written = sorted(p.name for p in (tmp_path / "toy_json").iterdir())
    assert written == ["fetch_ok.json", "search_ok.json"]
    assert (tmp_path / "toy_json" / "fetch_ok.json").read_bytes().endswith(b"}\n")
    out = capsys.readouterr().out
    assert "recorded fetch_ok (1 request(s)" in out
    assert "https://" not in out


def test_it_records_every_case_by_default(tmp_path: Path) -> None:
    assert (
        recorder.main(["toy_json", "--directory", str(tmp_path)], transport=Dispatch())
        == 0
    )
    assert len(list((tmp_path / "toy_json").iterdir())) == len(ToyJson.cases)


def test_it_reports_a_failed_case_and_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TOY_JSON_API_KEY", secrets.token_hex(16))
    pool = FakePool(*[OSError("down")] * 5)
    wire = HttpTransport(pool=pool, sleep=lambda _s: None)
    status = recorder.main(
        ["toy_json", "fetch_ok", "--directory", str(tmp_path)], transport=wire
    )
    assert status == 1
    assert "fetch_ok raised TransportError" in capsys.readouterr().err
    assert not (tmp_path / "toy_json").exists()


def test_a_missing_key_is_reported_without_a_value(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    wire = HttpTransport(pool=FakePool(), sleep=lambda _s: None)
    status = recorder.main(
        ["toy_json", "fetch_ok", "--directory", str(tmp_path)], transport=wire
    )
    assert status == 1
    assert "TOY_JSON_API_KEY" in capsys.readouterr().err


def test_it_refuses_an_unknown_provider_or_case(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    assert recorder.main(["nope", "--list"]) == 2
    assert "no data provider is registered" in capsys.readouterr().err
    assert recorder.main(["toy_json", "no_such_case"], transport=Dispatch()) == 2
    assert "has no case no_such_case" in capsys.readouterr().err
