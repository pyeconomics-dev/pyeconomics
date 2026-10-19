# src/pyeconomics/data/providers/fed_board.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Board release files: H.15, GSW and meeting-specific SEP projections.

Ids are ``h15:RIFSPFF_N.B`` (or another series name in the release), ``gsw``
(all published columns), and ``sep:YYYY-MM-DD`` (one published SEP meeting).
The release files are used directly; no Data Download Program package builder.
"""

from __future__ import annotations

import csv
import datetime as dt
import re
from dataclasses import replace
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Final

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import LicenceClass, LlmUse, RealtimePeriod
from pyeconomics.data.errors import DataError, RateLimitError, SeriesNotFoundError
from pyeconomics.data.providers import _shared as s
from pyeconomics.data.providers.base import (
    Capability,
    Case,
    DataProvider,
    ProviderInfo,
    Query,
    RateLimit,
)
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.transport.base import Request, Response
from pyeconomics.data.transport.files import archive
from pyeconomics.data.types import (
    ColumnMeta,
    DateConvention,
    ObservationFrequency,
    SeasonalAdjustment,
    Table,
    TableMeta,
    UnitRecord,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["FedBoard"]

_ID: Final = "fed_board"

_RATE: Final = UnitRecord(text="Percent", kind=UnitKind.RATE)
_YEAR: Final = UnitRecord(text="Years", kind=UnitKind.YEARS)


class ProjectionTable(HTMLParser):
    """Read only Table 1 of the accessible SEP release, without executing HTML."""

    def __init__(self, *, all_tables: bool = False) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.all_tables = all_tables
        self.inside = False
        self.cell: list[str] | None = None
        self.row: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect table cells, retaining their published ordering."""
        if tag == "table" and (
            self.all_tables
            or dict(attrs).get("id") == "table1"
            or "xt1" in (dict(attrs).get("aria-labelledby") or "").split()
        ):
            self.inside = True
        if self.inside and tag == "tr":
            self.row = []
        if self.inside and tag in {"td", "th"}:
            self.cell = []

    def handle_data(self, data: str) -> None:
        """Collect text inside a table cell."""
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        """Finish cells and rows; ignore the following projection tables."""
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(" ".join(" ".join(self.cell).split()))
            self.cell = None
        if tag == "tr" and self.inside and self.row:
            self.rows.append(self.row)
        if tag == "table":
            self.inside = False


def _table(  # noqa: PLR0913 - data, metadata and vintage inputs
    query: Query,
    info: ProviderInfo,
    responses: Sequence[Response],
    rows: dict[dt.date, dict[str, float | None]],
    units: dict[str, UnitRecord],
    *,
    notes: tuple[str, ...] = (),
    realtime: tuple[RealtimePeriod, ...] | None = None,
) -> Table:
    if not rows:
        raise SeriesNotFoundError(_ID, query.series[0])
    index = tuple(sorted(rows))[-query.max_observations :]
    names = tuple(units)
    return Table(
        index,
        tuple(
            ColumnMeta(
                name=n,
                unit=units[n],
                seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            )
            for n in names
        ),
        tuple(tuple(rows[d].get(n) for d in index) for n in names),
        TableMeta(
            provider=info.id,
            table_id=query.series[0],
            title=query.series[0],
            frequency=ObservationFrequency.IRREGULAR,
            source_dating=DateConvention.PERIOD_END,
            terms=info.terms,
            retrieved_at=responses[-1].retrieved_at,
            notes=notes,
        ),
        realtime=realtime,
    )


class FedBoard(DataProvider):
    """Federal Reserve Board published release files and staff curve estimates."""

    info = ProviderInfo(
        id="fed_board",
        name="Federal Reserve Board",
        homepage="https://www.federalreserve.gov",
        terms=Terms(
            licence=LicenceClass.HOSTED_SAFE,
            terms_url="https://www.federalreserve.gov/disclaimer.htm",
            checked=dt.date(2026, 10, 16),
            attribution="Source: Board of Governors of the Federal Reserve System.",
            llm_use=LlmUse.ALLOWED,
            cache=CachePolicy.ALLOWED,
        ),
        hosts=("www.federalreserve.gov",),
        capabilities=(Capability.FETCH, Capability.BULK),
        rate_limits=(RateLimit(requests=2, per="second"),),
        ttl_seconds=86400,
        max_response_bytes=32 * 1024 * 1024,
    )
    cases = (
        *(
            Case(
                name=name,
                operation=Capability.FETCH,
                argument=Query(
                    series=(series,),
                    start=dt.date(2025, 1, 1),
                    end=dt.date(2025, 1, 6),
                    max_observations=3,
                ),
            )
            for name, series in (("h15", "h15:RIFSPFF_N.B"), ("gsw", "gsw"))
        ),
        Case(
            name="target_range",
            operation=Capability.FETCH,
            argument=Query(
                series=("target_range",),
                start=dt.date(2025, 1, 1),
                end=dt.date(2025, 12, 31),
                max_observations=3,
            ),
        ),
        Case(
            name="sep",
            operation=Capability.FETCH,
            argument=Query(series=("sep:2026-09-16",), max_observations=3),
        ),
        Case(
            name="error_not_found",
            operation=Capability.FETCH,
            argument=Query(series=("sep:1900-01-01",), max_observations=3),
            expect=SeriesNotFoundError,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.FETCH,
            argument=Query(series=("gsw",), max_observations=3),
            expect=RateLimitError,
            simulate=429,
        ),
    )

    def trim_recording(
        self, request: Request, response: Response, query: Query
    ) -> Response:
        """Keep a handful of genuine observations in the source's format."""
        from pyeconomics.data.transport.recording import trim_response  # noqa: PLC0415

        return trim_response(self.info.id, request, response, query)

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Choose one stable release file, never a caller's URL."""
        series = query.series[0]
        if series == "target_range":
            path = "/monetarypolicy/openmarket.htm"
        elif series == "gsw":
            path = "/data/yield-curve-tables/feds200628.csv"
        elif all(i.startswith("h15:") for i in query.series):
            path = "/releases/h15/data/FRB_h15_xml.zip"
        elif series.startswith("sep:") and len(query.series) == 1:
            day = dt.date.fromisoformat(series[4:])
            path = f"/monetarypolicy/fomcprojtabl{day:%Y%m%d}.htm"
        else:
            msg = "fed_board query requires gsw, h15:series or sep:YYYY-MM-DD"
            raise DataError(msg, provider="fed_board")
        return (Request(host="www.federalreserve.gov", path=path, series=series),)

    def parse(self, responses: Sequence[Response], query: Query) -> Table:
        """Parse the selected file, converting published percent to decimal."""
        if query.series[0] == "target_range":
            return self._target(responses, query)
        if query.series[0] == "gsw":
            return self._gsw(responses, query)
        if query.series[0].startswith("sep:"):
            return self._sep(responses, query)
        return self._h15(responses, query)

    def _target(self, responses: Sequence[Response], query: Query) -> Table:
        rows = {}
        text = responses[0].body.decode("utf-8")
        for year, html in re.findall(r"<h4>([0-9]{4})</h4>([\s\S]*?</table>)", text):
            parser = ProjectionTable(all_tables=True)
            parser.feed(html)
            for row in parser.rows:
                if (
                    len(row) != len(("Date", "Increase", "Decrease", "Level"))
                    or row[0] == "Date"
                ):
                    continue
                label = re.match(r"([A-Za-z]+)\s+([0-9]{1,2})", row[0])
                if label is None:
                    continue
                day = (
                    dt.datetime.strptime(label.group(0) + " " + year, "%B %d %Y")
                    .replace(tzinfo=dt.UTC)
                    .date()
                )
                if (query.start and day < query.start) or (
                    query.end and day > query.end
                ):
                    continue
                values = re.findall(r"[0-9]+(?:\.[0-9]+)?", row[3])
                if not values:
                    continue
                rows[day] = {
                    "lower": s.rate_or_value(float(values[0]), percent=True),
                    "upper": s.rate_or_value(float(values[-1]), percent=True),
                }
        return _table(
            query,
            self.info,
            responses,
            rows,
            {"lower": _RATE, "upper": _RATE},
            notes=(
                (
                    "target_changes: effective dates of published target changes; "
                    "no daily forward fill"
                ),
            ),
        )

    def _gsw(self, responses: Sequence[Response], query: Query) -> Table:
        lines = responses[0].body.decode("utf-8-sig").splitlines()
        first = next(
            i for i, line in enumerate(lines) if line.startswith("Date,BETA0,")
        )
        reader = csv.DictReader(lines[first:])
        units = {
            n: _YEAR
            if n.startswith("TAU")
            else UnitRecord(text="Svensson coefficient in decimal rate units")
            if n.startswith("BETA")
            else _RATE
            for n in reader.fieldnames or ()
            if n != "Date"
        }
        rows = {}
        for raw in reader:
            day = dt.date.fromisoformat(raw["Date"])
            if (query.start and day < query.start) or (query.end and day > query.end):
                continue
            rows[day] = {
                n: s.rate_or_value(
                    s.number(raw[n], "fed_board", missing=("NA", "-999.99")),
                    percent=not n.startswith("TAU"),
                )
                for n in units
            }
        return _table(
            query,
            self.info,
            responses,
            rows,
            units,
            notes=(
                (
                    "staff_research: GSW estimates are subject to revision; "
                    "Svensson beta parameters use decimal units "
                    "and tau parameters use years"
                ),
            ),
        )

    def _h15(self, responses: Sequence[Response], query: Query) -> Table:
        from defusedxml.ElementTree import fromstring  # noqa: PLC0415

        root = fromstring(
            archive(responses[0].body, "fed_board")["H15_data.xml"], forbid_dtd=True
        )
        third_party = any(i[4:].startswith(("RIMLP", "RIFLDI")) for i in query.series)
        wanted = {i[4:] for i in query.series}
        rows: dict[dt.date, dict[str, float | None]] = {}
        units = {}
        for series in root.iter():
            name = series.attrib.get("SERIES_NAME")
            if name not in wanted:
                continue
            units[name] = _RATE
            for obs in series:
                if "TIME_PERIOD" not in obs.attrib:
                    continue
                raw_day = obs.attrib["TIME_PERIOD"]
                if len(raw_day) != len("YYYY-MM-DD"):
                    msg = "request a daily H.15 series"
                    raise DataError(msg, provider="fed_board")
                day = dt.date.fromisoformat(raw_day)
                if (query.start and day < query.start) or (
                    query.end and day > query.end
                ):
                    continue
                rows.setdefault(day, {})[name] = s.rate_or_value(
                    s.number(
                        obs.attrib.get("OBS_VALUE", ""),
                        "fed_board",
                        missing=("ND", "NA"),
                    ),
                    percent=True,
                )
        if set(units) != wanted:
            msg = "fed_board H.15 series not found"
            raise SeriesNotFoundError(_ID, query.series[0])
        info = self.info
        if third_party:
            info = replace(
                info,
                terms=replace(
                    info.terms,
                    licence=LicenceClass.LIBRARY_ONLY,
                    notice=(
                        "H.15 identifies this corporate or municipal index as "
                        "third-party content; redistribution requires its "
                        "originator's permission."
                    ),
                ),
            )
        return _table(query, info, responses, rows, units)

    def _sep(self, responses: Sequence[Response], query: Query) -> Table:
        parser = ProjectionTable()
        parser.feed(responses[0].body.decode("utf-8"))
        horizons: list[str] = []
        data: dict[str, float | None] = {}
        for row in parser.rows:
            if row and all(re.fullmatch(r"20\d{2}|Longer run", cell) for cell in row):
                horizons = row[: len(row) // 3]
                continue
            if not horizons or len(row) < 1 + 3 * len(horizons):
                continue
            # A label may end in a footnote number ("Core PCE inflation 4"); it
            # is not part of the variable's name.
            label = re.sub(r"\d+$", "", row[0].strip())
            variable = re.sub(r"[^a-z0-9]+", "_", label.casefold()).strip("_")
            if "projection" in variable or "june" in variable:
                continue
            for group, statistic in enumerate(("median", "central_tendency", "range")):
                for j, horizon in enumerate(horizons):
                    cell = row[1 + group * len(horizons) + j]
                    values = re.findall(r"-?\d+(?:\.\d+)?", cell.replace("\u2212", "-"))
                    key = f"{variable}_{statistic}_{horizon.replace(' ', '_')}"
                    if statistic == "median":
                        data[key] = s.rate_or_value(
                            s.number(values[0] if values else "", "fed_board"),
                            percent=True,
                        )
                    else:
                        for k, suffix in enumerate(("low", "high")):
                            data[key + "_" + suffix] = s.rate_or_value(
                                s.number(
                                    values[k] if len(values) > k else "", "fed_board"
                                ),
                                percent=True,
                            )
        meeting = dt.date.fromisoformat(query.series[0][4:])
        return _table(
            query,
            self.info,
            responses,
            {meeting: data} if data else {},
            dict.fromkeys(data, _RATE),
            notes=(
                (
                    "meeting_vintage: SEP horizons, including longer run, are columns; "
                    "the index is the meeting date"
                ),
            ),
            realtime=(RealtimePeriod(meeting, None),),
        )
