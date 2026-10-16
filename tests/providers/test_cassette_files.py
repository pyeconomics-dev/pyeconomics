# tests/providers/test_cassette_files.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Every committed cassette passes the scan (the Recording rule).

For each file under ``tests/providers/cassettes``: it parses strictly and is stored
as canonical JSON and one line feed; its directory is a registered provider's id;
it is at most 32 KiB; no response holds more than 24 observations of a series; it
passes the secret scan (gitleaks-style patterns, the project's key patterns and any
credential parameter); and a source that is not hosted-safe, or that forbids
storage, is marked synthetic. ``problems`` returns what is wrong, so a test can
prove each check fails on a bad file. The toys' files are also checked to be exactly
what ``build_toy_cassettes.build`` produces.
"""

from __future__ import annotations

import json
import secrets
from typing import TYPE_CHECKING, Final

import pytest
from build_toy_cassettes import build, needs_synthetic
from provider_contract import CASSETTES
from toys import ToyJson, ToyVintage

from pyeconomics.core.errors import InputError
from pyeconomics.data import DataProvider, registry
from pyeconomics.data.transport.cassette import (
    MAX_CASSETTE_BYTES,
    MAX_OBSERVATIONS,
    Cassette,
    scan_text,
)

if TYPE_CHECKING:
    from pathlib import Path

PROVIDERS: Final[dict[str, type[DataProvider]]] = {
    **{p.info.id: p for p in (ToyJson, ToyVintage)},
    **{i: type(registry.get(i)) for i in registry.ids()},
}
FILES: Final = sorted(CASSETTES.rglob("*"))


def _longest_dated_list(value: object) -> int:
    """Return the length of the longest JSON array of dated rows, anywhere inside."""
    longest = 0
    if isinstance(value, list):
        dated = [
            item
            for item in value
            if (
                isinstance(item, dict)
                and any("date" in k or "period" in k for k in item)
            )
            or (
                isinstance(item, list)
                and item
                and isinstance(item[0], str)
                and item[0][:2] == "20"
            )
        ]
        longest = len(dated)
        for item in value:
            longest = max(longest, _longest_dated_list(item))
    elif isinstance(value, dict):
        for item in value.values():
            longest = max(longest, _longest_dated_list(item))
    return longest


def _body_problems(path: Path, cassette: Cassette) -> list[str]:
    """Scan every response body, and count its dated rows."""
    found: list[str] = []
    for record in cassette.requests:
        body = record.response.body
        found.extend(
            f"{path.name}: a response body matches the {name} pattern"
            for name in scan_text(body.decode("utf-8", "replace"))
        )
        try:
            rows = _longest_dated_list(json.loads(body))
        except ValueError:
            rows = 0
        if rows > MAX_OBSERVATIONS:
            found.append(f"{path.name}: {rows} dated rows exceeds {MAX_OBSERVATIONS}")
    return found


def _provider_problems(
    path: Path, cassette: Cassette, providers: dict[str, type[DataProvider]]
) -> list[str]:
    """Check the cassette against the provider whose directory it sits in."""
    provider = providers.get(path.parent.name)
    if provider is None:
        return [f"{path.name}: {path.parent.name} is not a registered provider"]
    if needs_synthetic(provider) and not cassette.synthetic:
        return [f"{path.name}: this source's cassettes must be marked synthetic"]
    return []


def problems(path: Path, providers: dict[str, type[DataProvider]]) -> list[str]:
    """Return what is wrong with one cassette file; secrets are named, never shown."""
    if path.suffix != ".json":
        return [f"{path.name}: only .json cassettes belong here"]
    raw = path.read_bytes()
    found: list[str] = []
    if len(raw) > MAX_CASSETTE_BYTES:
        found.append(f"{path.name}: {len(raw)} bytes exceeds {MAX_CASSETTE_BYTES}")
    try:
        cassette = Cassette.from_json(raw)
    except InputError as error:
        return [*found, f"{path.name}: not a valid cassette ({error})"]
    if raw != cassette.document():
        found.append(f"{path.name}: not canonical JSON with one line feed")
    if cassette.provider != path.parent.name:
        found.append(
            f"{path.name}: records {cassette.provider}, not {path.parent.name}"
        )
    found.extend(
        f"{path.name}: matches the {name} pattern"
        for name in scan_text(raw.decode("utf-8", "replace"))
    )
    found.extend(_body_problems(path, cassette))
    found.extend(_provider_problems(path, cassette, providers))
    return found


def test_there_are_cassettes_to_check() -> None:
    assert [p for p in FILES if p.is_file()], "the toy cassettes are missing"


@pytest.mark.parametrize(
    "path", [p for p in FILES if p.is_file()], ids=lambda p: f"{p.parent.name}/{p.name}"
)
def test_a_committed_cassette_passes_the_scan(path: Path) -> None:
    assert problems(path, PROVIDERS) == []


def test_the_toy_cassettes_are_exactly_what_the_builder_makes() -> None:
    built = build()
    toys = {"toy_json", "toy_vintage"}
    on_disk = {p for p in FILES if p.is_file() and p.parent.name in toys}
    assert set(built) == on_disk, "run tests/providers/build_toy_cassettes.py"
    stale = sorted(
        p.name for p, document in built.items() if p.read_bytes() != document
    )
    assert stale == [], "run tests/providers/build_toy_cassettes.py"


def test_every_case_has_exactly_one_cassette_and_no_cassette_is_orphaned() -> None:
    expected = {
        CASSETTES / provider.info.id / f"{case.name}.json"
        for provider in PROVIDERS.values()
        for case in provider.cases
    }
    assert {p for p in FILES if p.is_file()} == expected


def test_a_vintage_source_that_forbids_storage_has_only_synthetic_cassettes() -> None:
    for path in (CASSETTES / "toy_vintage").glob("*.json"):
        assert Cassette.from_json(path.read_bytes()).synthetic is True
    assert needs_synthetic(ToyVintage)
    assert not needs_synthetic(ToyJson)


# --- the scan fails on a bad file ---------------------------------------------


def good(tmp_path: Path) -> Path:
    source = CASSETTES / "toy_json" / "fetch_ok.json"
    target = tmp_path / "toy_json" / "fetch_ok.json"
    target.parent.mkdir()
    target.write_bytes(source.read_bytes())
    return target


def test_a_good_file_copied_elsewhere_passes(tmp_path: Path) -> None:
    assert problems(good(tmp_path), PROVIDERS) == []


def rewrite(path: Path, edit: object) -> Path:
    document = json.loads(path.read_bytes())
    edit(document)  # type: ignore[operator]
    path.write_bytes(Cassette.from_json(json.dumps(document)).document())
    return path


def test_a_planted_key_in_a_response_body_is_found_by_name(tmp_path: Path) -> None:
    import secrets  # noqa: PLC0415

    planted = "gh" + "p_" + secrets.token_hex(18)
    path = good(tmp_path)
    rewrite(
        path,
        lambda d: d["requests"][0]["response"].update(body=f'{{"token":"{planted}"}}'),
    )
    found = problems(path, PROVIDERS)
    assert any("github-token" in line for line in found)
    assert planted not in "".join(found)


def test_an_unscrubbed_credential_parameter_in_a_body_is_found(tmp_path: Path) -> None:
    path = good(tmp_path)
    link = "https://api.toyjson.example.org/v1/x?api_key=" + secrets.token_hex(8)
    rewrite(
        path,
        lambda d: d["requests"][0]["response"].update(body=json.dumps({"next": link})),
    )
    assert any("credential-parameter" in line for line in problems(path, PROVIDERS))


def test_an_oversize_file_is_found(tmp_path: Path) -> None:
    path = good(tmp_path)
    rewrite(path, lambda d: d["requests"][0]["response"].update(body="x" * 40_000))
    assert any("exceeds 32768" in line for line in problems(path, PROVIDERS))


def test_too_many_observations_are_found(tmp_path: Path) -> None:
    path = good(tmp_path)
    rows = [{"date": f"2020-{m:02d}-01", "value": "1"} for m in range(1, 13)] * 3
    rewrite(
        path,
        lambda d: d["requests"][0]["response"].update(
            body=json.dumps({"observations": rows})
        ),
    )
    assert any("dated rows exceeds 24" in line for line in problems(path, PROVIDERS))


def test_a_non_synthetic_cassette_of_a_library_only_source_is_found(
    tmp_path: Path,
) -> None:
    source = CASSETTES / "toy_vintage" / "fetch_all.json"
    path = tmp_path / "toy_vintage" / "fetch_all.json"
    path.parent.mkdir()
    path.write_bytes(source.read_bytes())
    assert problems(path, PROVIDERS) == []
    rewrite(path, lambda d: d.update(synthetic=False))
    assert any("must be marked synthetic" in line for line in problems(path, PROVIDERS))


def test_a_cassette_in_the_wrong_directory_or_for_an_unknown_provider_is_found(
    tmp_path: Path,
) -> None:
    path = good(tmp_path)
    moved = tmp_path / "other_provider" / "fetch_ok.json"
    moved.parent.mkdir()
    moved.write_bytes(path.read_bytes())
    found = problems(moved, PROVIDERS)
    assert any("records toy_json, not other_provider" in line for line in found)
    assert any("not a registered provider" in line for line in found)


def test_a_file_that_is_not_canonical_or_not_a_cassette_is_found(
    tmp_path: Path,
) -> None:
    path = good(tmp_path)
    path.write_bytes(path.read_bytes().rstrip(b"\n"))
    assert any("one line feed" in line for line in problems(path, PROVIDERS))
    path.write_bytes(b"{}\n")
    assert any("not a valid cassette" in line for line in problems(path, PROVIDERS))
    other = tmp_path / "toy_json" / "notes.txt"
    other.write_text("hello")
    assert any("only .json" in line for line in problems(other, PROVIDERS))
