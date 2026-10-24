# tests/exports/test_bundle.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Reproducibility bundles: deterministic, complete and checked safely (Step 5).

A bundle is a stored zip with sorted members, fixed dates and fixed modes, so
equal results give equal bytes on every operating system: a pinned digest of a
fixed set of members proves it on every cell of the test matrix.
``check_bundle`` must refuse unsafe member names, oversized archives and
tampered results before or while reading only the JSON members, and must never
run, or even read, ``reproduce.py`` (ADR-0012 decision 7; Step 5 security).
"""

from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import zipfile
from typing import TYPE_CHECKING, Any

import pytest
from cli_support import install_world

from pyeconomics import run
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.errors import InputError
from pyeconomics.core.manifest import result_sha256
from pyeconomics.data import cache
from pyeconomics.exports import bundle as bundle_module
from pyeconomics.exports import check_bundle, write_bundle
from pyeconomics.exports.bundle import (
    BUNDLE_MEMBERS,
    FIXED_TIMESTAMP,
    JSON_MEMBERS,
    MEMBER_MODE,
    bundle_bytes,
    bundle_members,
)
from pyeconomics.exports.reproduction import REPRODUCE_SCRIPT
from pyeconomics.surfaces.invoke import BindRequest, invoke

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from pyeconomics.core.results import Result

PV = {"calculation": "present_value", "rate": 0.05, "periods": 10, "future_value": 100}
#: The SHA-256 of bundle_bytes(FIXED): any change to the zip layout (a date, a
#: mode, the order, compression, the "made by" system) changes it on some OS.
FIXED: dict[str, bytes] = {name: f"{name}\n".encode() for name in BUNDLE_MEMBERS}
FIXED_SHA256 = "3e34a43d9e14464bdeed16a0ef2746ff1f6f1a8dcce2702672eafd2d88737321"


def pv() -> Result[Any, Any]:
    return run("foundations.time_value", PV)


def rezip(members: dict[str, bytes], **infos: Any) -> bytes:  # noqa: ANN401
    """Zip members with zipfile's defaults, overriding ZipInfo fields by name."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in members.items():
            info = zipfile.ZipInfo(name, date_time=FIXED_TIMESTAMP)
            for field, value in infos.get(name, {}).items():
                setattr(info, field, value)
            archive.writestr(info, data)
    return buffer.getvalue()


def members_of(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


# --- writing ----------------------------------------------------------------------


def test_the_zip_layout_is_pinned_on_every_operating_system() -> None:
    data = bundle_bytes(FIXED)
    assert hashlib.sha256(data).hexdigest() == FIXED_SHA256


def test_every_member_is_stored_sorted_dated_1980_and_mode_0644() -> None:
    with zipfile.ZipFile(io.BytesIO(bundle_bytes(bundle_members(pv())))) as archive:
        infos = archive.infolist()
    assert [info.filename for info in infos] == sorted(BUNDLE_MEMBERS)
    for info in infos:
        assert info.compress_type == zipfile.ZIP_STORED
        assert info.date_time == FIXED_TIMESTAMP
        assert info.external_attr >> 16 == MEMBER_MODE
        assert info.create_system == 3


def test_equal_results_give_equal_bytes(tmp_path: Path) -> None:
    write_bundle(pv(), tmp_path / "a.zip")
    stream = io.BytesIO()
    write_bundle(pv(), stream)
    assert (tmp_path / "a.zip").read_bytes() == stream.getvalue()


def test_the_members_hold_the_result_and_how_to_rerun_it() -> None:
    result = pv()
    members = members_of(bundle_bytes(bundle_members(result)))
    assert members["result.json"] == result.to_json().encode()
    assert json.loads(members["inputs.json"]) == result.inputs.model_dump(mode="json")
    assert json.loads(members["manifest.json"]) == result.manifest.to_dict()
    assert members["request.json"] == b"null"
    assert members["reproduce.py"] == REPRODUCE_SCRIPT.encode()
    version = result.manifest.package_version
    assert members["requirements.txt"].decode().splitlines()[-1] == (
        f"pyeconomics=={version}"
    )
    readme = members["README.txt"].decode()
    assert result.manifest.result_sha256 in readme
    assert "pyeconomics bundle check" in readme
    assert "read it before you run" in readme
    assert "--refetch" not in readme
    assert members["ATTRIBUTION.txt"] == (
        b"This result read no data, so it carries no attribution.\n"
    )
    for name, data in members.items():
        assert b"\r\n" not in data, name


def test_requirements_name_the_extra_a_model_needs() -> None:
    result = run("econometrics.ols", _first_example("econometrics.ols"))
    lines = bundle_members(result)["requirements.txt"].decode().splitlines()
    version = result.manifest.package_version
    assert lines[-1] == f"pyeconomics[econometrics]=={version}"


def _first_example(model_id: str) -> dict[str, object]:
    from pyeconomics.core.registry import installed  # noqa: PLC0415

    return dict(installed().get(model_id).spec.examples[0].inputs)


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    install_world(monkeypatch)
    with cache.bypass():
        yield


@pytest.mark.usefixtures("world")
def test_a_bound_runs_bundle_records_its_request_and_attributions() -> None:
    request = BindRequest(as_of="2024-03-20", parameters={"meeting": "2024-09"})
    result = invoke("macro.toy_unemployment", {}, bind=request)
    members = members_of(bundle_bytes(bundle_members(result, request)))
    assert json.loads(members["request.json"]) == {
        "as_of": "2024-03-20",
        "vintage": None,
        "profile": "default",
        "concepts": {},
        "parameters": {"meeting": "2024-09"},
    }
    text = members["ATTRIBUTION.txt"].decode()
    for line in result.attributions():
        assert line in text.splitlines()
    record = result.manifest.data_sources[0]
    assert f"Terms: {record.terms_url}" in text
    assert "--refetch" in members["README.txt"].decode()
    assert check_bundle(bundle_bytes(members)).bound


# --- checking ---------------------------------------------------------------------


def test_a_valid_bundle_is_reported(tmp_path: Path) -> None:
    result = pv()
    path = tmp_path / "pv.zip"
    write_bundle(result, path)
    report = check_bundle(path)
    assert (report.model_id, report.model_version) == (result.model_id, 2)
    assert report.result_sha256 == result.manifest.result_sha256
    assert report.inputs_sha256 == result.manifest.inputs_sha256
    assert report.package_version == result.manifest.package_version
    assert (report.bound, report.sources) == (False, 0)
    assert [name for name, _ in report.members] == list(BUNDLE_MEMBERS)
    sizes = {name: len(data) for name, data in bundle_members(result).items()}
    assert report.members == tuple(sorted(sizes.items()))
    assert report.to_dict()["members"] == [
        {"name": name, "size": size} for name, size in report.members
    ]


def test_check_reads_only_the_json_members_and_runs_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "ran"
    members = bundle_members(pv())
    members["reproduce.py"] = f"open({str(marker)!r}, 'w').close()\n".encode()
    data = bundle_bytes(members)
    opened: list[str] = []
    original = zipfile.ZipFile.open

    def spy(self: zipfile.ZipFile, name: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        opened.append(name if isinstance(name, str) else name.filename)
        return original(self, name, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "open", spy)
    check_bundle(data)
    assert sorted(opened) == sorted(JSON_MEMBERS)
    assert not marker.exists()


@pytest.mark.parametrize(
    "name", ["../result.json", "dir/result.json", "dir\\result.json", "a..b"]
)
def test_a_member_name_with_a_separator_or_dots_is_refused(name: str) -> None:
    members = {**bundle_members(pv()), name: b"{}"}
    with pytest.raises(InputError, match=r"path separator or '\.\.'"):
        check_bundle(rezip(members))


def test_an_unexpected_a_missing_or_a_repeated_member_is_refused() -> None:
    members = bundle_members(pv())
    with pytest.raises(InputError, match=r"unexpected member 'extra\.txt'"):
        check_bundle(rezip({**members, "extra.txt": b""}))
    without = {name: data for name, data in members.items() if name != "README.txt"}
    with pytest.raises(InputError, match=r"lacks README\.txt"):
        check_bundle(rezip(without))
    doubled = io.BytesIO()
    with zipfile.ZipFile(doubled, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr("README.txt", b"again")
    with pytest.raises(InputError, match=r"holds 'README\.txt' twice"):
        check_bundle(doubled.getvalue())


def test_a_compressed_member_is_refused() -> None:
    members = bundle_members(pv())
    data = rezip(members, **{"result.json": {"compress_type": zipfile.ZIP_DEFLATED}})
    with pytest.raises(InputError, match=r"result\.json is compressed or encrypted"):
        check_bundle(data)


def test_too_many_members_are_refused_before_any_is_read() -> None:
    members = {
        f"m{index}": b"" for index in range(bundle_module.MAX_BUNDLE_MEMBERS + 1)
    }
    with pytest.raises(InputError, match="more than 64 members"):
        check_bundle(rezip(members))


@pytest.mark.parametrize("as_path", [True, False], ids=["path", "bytes"])
def test_an_oversized_archive_is_refused_before_it_is_opened(
    as_path: bool,  # noqa: FBT001 - a parameter
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = bundle_bytes(bundle_members(pv()))
    path = tmp_path / "big.zip"
    path.write_bytes(data)
    monkeypatch.setattr(bundle_module, "MAX_BUNDLE_BYTES", len(data) - 1)
    with pytest.raises(InputError, match="larger than"):
        check_bundle(path if as_path else data)


def test_a_member_total_above_the_limit_is_refused_before_reading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    members = bundle_members(pv())
    data = bundle_bytes(members)
    total = sum(len(v) for v in members.values())
    monkeypatch.setattr(bundle_module, "MAX_BUNDLE_BYTES", total - 1)
    # The archive is over the limit too; skip that check to reach this one.
    monkeypatch.setattr(
        bundle_module, "_open", lambda source: zipfile.ZipFile(io.BytesIO(source))
    )
    monkeypatch.setattr(zipfile.ZipFile, "open", _no_read)
    with pytest.raises(InputError, match="its members hold more than"):
        check_bundle(data)


def _no_read(*_: object, **__: object) -> None:
    msg = "a member was read"
    raise AssertionError(msg)


def _tampered(change: str) -> bytes:
    result = pv()
    members = bundle_members(result)
    document = json.loads(members["result.json"])
    if change == "outputs":
        document["outputs"]["present_value"] = 1.0
    elif change == "inputs":
        document["inputs"]["rate"] = 0.06
        document["manifest"]["result_sha256"] = result_sha256(
            {k: document[k] for k in bundle_module._BODY_KEYS}  # noqa: SLF001
        )
    members["result.json"] = canonical_json(document)
    return bundle_bytes(members)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("outputs", "result_sha256 is not the hash"),
        ("inputs", "inputs_sha256 is not the hash"),
    ],
)
def test_a_tampered_result_is_refused(change: str, message: str) -> None:
    with pytest.raises(InputError, match=message):
        check_bundle(_tampered(change))


@pytest.mark.parametrize(
    ("member", "content", "message"),
    [
        ("manifest.json", b'{"schema_version":2}', "manifest.json is not the result"),
        ("inputs.json", b'{"rate":1}', "inputs.json is not the result's inputs"),
        ("request.json", b'{"as_of":null}', "request.json is not a bind request"),
        ("request.json", b"[]", "request.json is not a JSON object"),
        ("inputs.json", b'{"a":1,"a":2}', "repeats the key 'a'"),
        ("inputs.json", b'{"a":NaN}', "holds NaN"),
        ("inputs.json", b'{ "a": 1 }', "inputs.json is not canonical JSON"),
        ("inputs.json", b"{", "inputs.json is not JSON"),
        ("inputs.json", b"[" * 100_000, "inputs.json is not JSON"),
        ("result.json", b'{"model_id":"x"}', "result.json lacks"),
        ("result.json", b"[]", "result.json is not a JSON object"),
    ],
    ids=[
        "manifest",
        "inputs",
        "request-keys",
        "request-type",
        "duplicate",
        "nan",
        "not-canonical",
        "truncated",
        "deep",
        "result-keys",
        "result-type",
    ],
)
def test_a_bad_json_member_is_refused(
    member: str, content: bytes, message: str
) -> None:
    members = {**bundle_members(pv()), member: content}
    with pytest.raises(InputError, match=message):
        check_bundle(bundle_bytes(members))


def test_a_result_with_a_mistyped_id_or_version_is_refused() -> None:
    members = bundle_members(pv())
    document = json.loads(members["result.json"])
    document["model_version"] = "2"
    members["result.json"] = canonical_json(document)
    with pytest.raises(InputError, match="model_version not an integer"):
        check_bundle(bundle_bytes(members))


def test_a_file_that_is_not_a_zip_or_cannot_be_read_is_refused(tmp_path: Path) -> None:
    with pytest.raises(InputError, match="not a zip archive"):
        check_bundle(b"not a zip")
    with pytest.raises(InputError, match=r"cannot be read \(FileNotFoundError\)"):
        check_bundle(tmp_path / "missing.zip")
    with pytest.raises(InputError) as caught:
        check_bundle(tmp_path / "missing.zip")
    assert str(tmp_path) not in str(caught.value)


def test_a_corrupt_member_is_refused() -> None:
    data = bytearray(bundle_bytes(bundle_members(pv())))
    marker = data.find(b'"present_value":61.')
    data[marker + 1] = ord("P")  # the CRC no longer matches
    with pytest.raises(InputError, match=r"result\.json cannot be read"):
        check_bundle(bytes(data))


def test_attribution_lists_each_source_once() -> None:
    from pyeconomics.core.provenance import (  # noqa: PLC0415
        DataSource,
        LicenceClass,
        LlmUse,
    )
    from pyeconomics.core.results import Result  # noqa: PLC0415

    result = pv()
    record = DataSource(
        provider="example",
        series_id="A",
        licence=LicenceClass.HOSTED_SAFE,
        attribution="Source: an example agency.",
        terms_url="https://www.example.org/terms",
        llm_use=LlmUse.ALLOWED,
    )
    records = (record, dataclasses.replace(record, series_id="B"))
    sourced = Result.build(result.model, result.inputs, result.outputs, (), records)
    text = bundle_members(sourced)["ATTRIBUTION.txt"].decode()
    assert text.count("Source: an example agency.") == 1
    assert "example: A" in text
    assert "example: B" not in text
