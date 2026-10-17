# tests/providers/build_toy_cassettes.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Build the toy providers' cassettes.

Run ``uv run python tests/providers/build_toy_cassettes.py``.

The toys have no real API to record, so their cassettes are built from the canned
responses below, through the same ``Cassette.from_exchanges`` the recorder uses
(scrubbing and all). ``toy_vintage`` is library-only and forbids storage, so its
responses go through its ``synthesize`` hook and its cassettes are marked
synthetic, as the Recording rule requires of such a source.

``tests/providers/test_toy_cassettes.py`` fails when the files on disk differ from
what this module builds, so a change to a toy or to the format is a reviewed diff.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import TYPE_CHECKING, Final

from toys import ToyJson, ToyVintage

from pyeconomics.data import LicenceClass, Query
from pyeconomics.data.providers.base import Capability, Case, DataProvider
from pyeconomics.data.transport.base import Request, Response
from pyeconomics.data.transport.cassette import Cassette

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ["CASSETTES", "RECORDED_ON", "build", "needs_synthetic"]

CASSETTES: Final = Path(__file__).resolve().parent / "cassettes"
RECORDED_ON: Final = dt.datetime(2026, 10, 15, 14, 0, tzinfo=dt.UTC)
_JSON: Final = {"content-type": "application/json"}

_Canned = tuple[int, dict[str, str], bytes]


def _body(document: object) -> bytes:
    return json.dumps(document, separators=(",", ":")).encode("utf-8")


def _ok(document: object) -> _Canned:
    return 200, _JSON, _body(document)


def _error(status: int, message: str, **headers: str) -> _Canned:
    document = {"error_code": status, "error_message": message}
    return status, {**_JSON, **headers}, _body(document)


def _rows(dates: Iterable[str], values: Iterable[str]) -> list[dict[str, str]]:
    return [{"date": d, "value": v} for d, v in zip(dates, values, strict=True)]


_MONTHS = [f"2025-0{m}-01" for m in range(1, 7)]

_TOY_JSON: Final[dict[str, list[_Canned]]] = {
    "fetch_ok": [
        _ok(
            {
                "series_id": "TOYRATE",
                "title": "Toy policy rate",
                "units": "Percent",
                "frequency": "monthly",
                "seasonal_adjustment": "NSA",
                "license": "public",
                "observations": _rows(
                    _MONTHS, ["4.50", "4.50", ".", "4.25", "4.25", "4.00"]
                ),
            }
        )
    ],
    "fetch_table": [
        _ok(
            {
                "series_id": "TOYRATE",
                "title": "Toy policy rate",
                "units": "Percent",
                "frequency": "monthly",
                "seasonal_adjustment": "NSA",
                "license": "public",
                "observations": _rows(
                    _MONTHS, ["4.50", "4.50", ".", "4.25", "4.25", "4.00"]
                ),
            }
        ),
        _ok(
            {
                "series_id": "TOYGROWTH",
                "title": "Toy output growth",
                "units": "Percent",
                "frequency": "monthly",
                "seasonal_adjustment": "SA",
                "license": "public",
                "observations": _rows(
                    _MONTHS, ["0.30", "0.25", "0.40", "0.10", ".", "0.20"]
                ),
            }
        ),
    ],
    "fetch_restricted": [
        _ok(
            {
                "series_id": "TOYRESTRICTED",
                "title": "Toy restricted index",
                "units": "Percent",
                "frequency": "monthly",
                "seasonal_adjustment": "NSA",
                "license": "restricted",
                "observations": _rows(_MONTHS[:3], ["1.00", "1.10", "1.20"]),
            }
        )
    ],
    "search_ok": [
        _ok(
            {
                "results": [
                    {
                        "series_id": "TOYRATE",
                        "title": "Toy policy rate",
                        "frequency": "monthly",
                        "units": "Percent",
                    },
                    {
                        "series_id": "TOYGROWTH",
                        "title": "Toy output growth",
                        "frequency": "monthly",
                        "units": "Percent",
                    },
                ]
            }
        )
    ],
    "describe_ok": [
        _ok(
            {
                "series_id": "TOYRATE",
                "title": "Toy policy rate",
                "units": "Percent",
                "frequency": "monthly",
                "seasonal_adjustment": "NSA",
                "license": "public",
            }
        )
    ],
    "error_unauthorized": [_error(401, "Bad Request. The API key is not valid.")],
    "error_unknown_series": [_error(400, "Bad Request. The series does not exist.")],
    "error_not_found": [_error(404, "Not found.")],
    "error_rate_limited": [_error(429, "Too many requests.", **{"retry-after": "30"})],
    "error_unavailable": [
        (503, {"content-type": "text/plain"}, b"Service Unavailable")
    ],
    "error_malformed": [
        (
            200,
            {"content-type": "text/html"},
            b"<html><body>down for maintenance</body></html>",
        )
    ],
}

#: GDP-growth-like rows with ALFRED's layout: a first release, then revisions,
#: each period ending the day before the next begins. The numbers are invented
#: (and the synthesize hook replaces them anyway).
_VINTAGE_ROWS: Final = [
    ("2008-06-30", "1.0", "2008-07-30", "2008-08-27"),
    ("2008-06-30", "1.2", "2008-08-28", "2008-09-25"),
    ("2008-06-30", "1.5", "2008-09-26", "9999-12-31"),
    ("2008-09-30", "-0.5", "2008-10-30", "2008-11-26"),
    ("2008-09-30", "-0.4", "2008-11-27", "2008-12-22"),
    ("2008-09-30", "-0.3", "2008-12-23", "9999-12-31"),
]
_TOY_VINTAGE: Final[dict[str, list[_Canned]]] = {
    "fetch_all": [
        _ok(
            {
                "series": "TOYGDP",
                "title": "Toy real GDP growth",
                "observations": [
                    {
                        "date": date,
                        "value": value,
                        "realtime_start": start,
                        "realtime_end": end,
                    }
                    for date, value, start, end in _VINTAGE_ROWS
                ],
            }
        )
    ],
    "vintages_ok": [
        _ok({"vintage_dates": sorted({start for _, _, start, _ in _VINTAGE_ROWS})})
    ],
    "error_not_found": [_error(404, "Not found.")],
    "error_rate_limited": [_error(429, "Too many requests.", **{"retry-after": "30"})],
}


def needs_synthetic(provider: type[DataProvider]) -> bool:
    """Whether the Recording rule requires synthetic values for a provider.

    That is a source not classed hosted-safe, or one whose terms forbid storage.
    """
    terms = provider.info.terms
    return (
        terms.licence is not LicenceClass.HOSTED_SAFE
        or terms.cache.value == "forbidden"
    )


def _requests(provider: DataProvider, case: Case) -> tuple[Request, ...]:
    """The requests a case sends, built the way the provider builds them."""
    argument = case.argument
    if case.operation is Capability.FETCH:
        assert isinstance(argument, Query)
        return tuple(provider.build_requests(argument))
    text = str(argument)
    builders = {
        Capability.SEARCH: lambda: provider.build_search(text, 25),
        Capability.DESCRIBE: lambda: provider.build_describe(text),
        Capability.VINTAGES: lambda: provider.build_vintages(text),
    }
    return tuple(builders[case.operation]())


def _cassette(
    provider_class: type[DataProvider], canned: dict[str, list[_Canned]], case: Case
) -> Cassette:
    provider = provider_class()
    requests = _requests(provider, case)
    answers = canned[case.name]
    assert len(requests) == len(answers), case.name
    synthetic = needs_synthetic(provider_class) or case.name == "fetch_restricted"
    exchanges: list[tuple[Request, Response]] = []
    for position, (request, (status, headers, body)) in enumerate(
        zip(requests, answers, strict=True)
    ):
        response = Response(status, body, RECORDED_ON, tuple(headers.items()))
        if (
            synthetic
            and response.ok
            and response.header("content-type") == "application/json"
        ):
            seed = request.series or f"{case.name}-{position}"
            response = provider.synthesize(request, response, seed=seed)
        exchanges.append((request, response))
    return Cassette.from_exchanges(
        provider.info.id, RECORDED_ON, exchanges, synthetic=synthetic
    )


def build() -> dict[Path, bytes]:
    """Return every toy cassette's path and its canonical JSON bytes."""
    built: dict[Path, bytes] = {}
    for provider_class, canned in ((ToyJson, _TOY_JSON), (ToyVintage, _TOY_VINTAGE)):
        assert {case.name for case in provider_class.cases} == set(canned)
        for case in provider_class.cases:
            path = CASSETTES / provider_class.info.id / f"{case.name}.json"
            built[path] = _cassette(provider_class, canned, case).document()
    return built


def main() -> None:  # pragma: no cover - a manual tool
    """Write the cassettes, with LF endings."""
    for path, document in build().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(document)
        print(f"wrote {path.relative_to(CASSETTES.parent.parent.parent)}")  # noqa: T201


if __name__ == "__main__":  # pragma: no cover
    main()
