# src/pyeconomics/data/transport/recording.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Trim genuine provider responses for the deliberate local cassette recorder.

No fetch calls this module. Spreadsheet writers are imported only here; xlwt
is a development dependency used solely to preserve the upstream XLS format.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import replace
from io import BytesIO
from typing import TYPE_CHECKING, Any
from zipfile import ZIP_DEFLATED, ZipFile

from pyeconomics.data.transport.files import archive

if TYPE_CHECKING:
    from pyeconomics.data.providers.base import Query
    from pyeconomics.data.transport.base import Request, Response


def _keep(day: str, query: Query) -> bool:
    return (query.start is None or day >= query.start.isoformat()) and (
        query.end is None or day <= query.end.isoformat()
    )


def _json(provider: str, body: bytes, query: Query) -> bytes:
    from pyeconomics.core import _fields  # noqa: PLC0415

    data: Any = _fields.load_json(body)
    limit = min(query.max_observations, 24)
    if provider == "nyfed":
        if "refRates" in data:
            data["refRates"] = data["refRates"][:limit]
        elif "soma" in data:
            data["soma"]["summary"] = data["soma"]["summary"][-limit:]
        else:
            for root in ("repo", "reverseRepo"):
                if root in data:
                    data[root]["operations"] = data[root]["operations"][:limit]
    return json.dumps(data, separators=(",", ":")).encode("utf-8")


def _h15(body: bytes, query: Query) -> bytes:
    from defusedxml.ElementTree import fromstring, tostring  # noqa: PLC0415

    files = archive(body, "fed_board")
    root = fromstring(files["H15_data.xml"], forbid_dtd=True)
    wanted = {n[4:] for n in query.series}
    for parent in root.iter():
        for child in list(parent):
            if "SERIES_NAME" not in child.attrib:
                continue
            if child.attrib["SERIES_NAME"] not in wanted:
                parent.remove(child)
                continue
            observations = [o for o in child if "TIME_PERIOD" in o.attrib]
            kept = [o for o in observations if _keep(o.attrib["TIME_PERIOD"], query)][
                -min(24, query.max_observations) :
            ]
            for obs in observations:
                if obs not in kept:
                    child.remove(obs)
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as zipped:
        zipped.writestr("H15_data.xml", tostring(root))
    return output.getvalue()


def _xlsx(body: bytes, query: Query) -> bytes:
    from pyeconomics.data.transport.files import spreadsheet, workbook  # noqa: PLC0415

    name, _, vintage = query.series[0].partition(":")
    sheet = vintage or (
        "Forecasts By Quarter"
        if name == "nowcast"
        else "data"
        if name == "lw"
        else "HLW Estimates"
    )
    rows = spreadsheet(body, sheet, "nyfed")
    prefix = [row for row in rows if row and not isinstance(row[0], dt.datetime)]
    dated = [
        row
        for row in rows
        if row
        and isinstance(row[0], dt.datetime)
        and _keep(row[0].date().isoformat(), query)
    ]
    return workbook(
        {sheet: tuple(prefix[:6] + dated[-min(24, query.max_observations) :])}
    )


def _xls(body: bytes, query: Query) -> bytes:
    import xlrd  # noqa: PLC0415
    import xlwt  # noqa: PLC0415 - recorder-only development dependency

    source = xlrd.open_workbook(file_contents=body, on_demand=True)
    output = xlwt.Workbook()
    try:
        sheet = source.sheet_by_name("ACM Daily")
        target = output.add_sheet(sheet.name)
        rows = [sheet.row_values(0)] + [
            sheet.row_values(i)
            for i in range(
                max(1, sheet.nrows - min(24, query.max_observations)), sheet.nrows
            )
        ]
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                target.write(i, j, value)
        stream = BytesIO()
        output.save(stream)
        return stream.getvalue()
    finally:
        source.release_resources()


def trim_response(
    provider: str, request: Request, response: Response, query: Query
) -> Response:
    """Keep the real format and observations, bounded by the recording query."""
    del request  # the query selects the trimmed dataset, not the request path
    if not response.ok:
        return replace(response, body=response.body[:1024])
    body = response.body
    if provider == "fed_board" and query.series[0].startswith("h15:"):
        body = _h15(body, query)
    elif provider == "fed_board" and query.series[0] == "gsw":
        lines = body.decode("utf-8-sig").splitlines()
        start = next(
            i for i, line in enumerate(lines) if line.startswith("Date,BETA0,")
        )
        rows = [
            line
            for line in lines[start + 1 :]
            if line and _keep(line.split(",", 1)[0], query)
        ]
        body = (
            "\n".join(lines[: start + 1] + rows[-min(24, query.max_observations) :])
            + "\n"
        ).encode()
    elif provider == "fed_board" and query.series[0] == "target_range":
        text = body.decode("utf-8")
        chunks = re.findall(r"(<h4>([0-9]{4})</h4>[\s\S]*?</table>)", text)
        body = "".join(
            chunk
            for chunk, year in chunks
            if (query.start is None or int(year) >= query.start.year)
            and (query.end is None or int(year) <= query.end.year)
        ).encode()
    elif provider == "fed_board" and query.series[0].startswith("sep:"):
        text = body.decode("utf-8")
        match = re.search(
            r'<table\b[^>]*(?:aria-labelledby="xt1\s|id="table1")[\s\S]+?</table>', text
        )
        if match:
            body = match.group(0).encode()
    elif provider == "nyfed" and body.startswith(b"PK"):
        body = _xlsx(body, query)
    elif provider == "nyfed" and query.series[0] == "acm":
        body = _xls(body, query)
    elif body.lstrip().startswith((b"{", b"[")):
        body = _json(provider, body, query)
    return replace(response, body=body)
