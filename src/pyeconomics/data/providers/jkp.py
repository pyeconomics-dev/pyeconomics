# src/pyeconomics/data/providers/jkp.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""JKP's public factor returns: ``usa:be_me:monthly:vw``.

The public dataset is CC BY-NC 4.0; the separate code licence grants no
commercial rights to these data. Each request selects one small country/factor
archive rather than downloading the global stock-level dataset.
"""

# ruff: noqa: PLR2004 - fixed source layouts, HTTP status and calendar bounds

from __future__ import annotations

import re
from dataclasses import replace
from typing import TYPE_CHECKING

from pyeconomics.data.errors import DataError, ResponseError
from pyeconomics.data.providers import _finance as f
from pyeconomics.data.providers.base import DataProvider
from pyeconomics.data.transport.base import Request, request_path
from pyeconomics.data.transport.cassette import synthetic_value
from pyeconomics.data.transport.files import archive, csv_document, zip_document
from pyeconomics.data.types import ObservationFrequency as F

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data.providers.base import Query
    from pyeconomics.data.transport.base import Response
    from pyeconomics.data.types import Table

__all__ = ["Jkp"]


class Jkp(DataProvider):
    """Jensen, Kelly and Pedersen factor files, as decimal excess returns."""

    info = f.info(
        "jkp",
        "JKP Global Factor Data",
        "https://jkpfactors.com",
        "https://jkpfactors.com/",
        "Source: Jensen, Kelly and Pedersen (2023), Global Factor Data.",
        "Creative Commons Attribution-NonCommercial 4.0 International",
        ("jkpfactors-data.s3.amazonaws.com",),
    )
    cases = f.cases("usa:be_me:monthly:vw", "usa:ret_12_1:daily:vw_cap")

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Encode identifiers as one filename segment on the fixed public host."""
        parts = f.single(query, self.info.id).split(":")
        if (
            len(parts) != 4
            or not re.fullmatch(
                r"[a-z]{3}|world|world_ex_us|developed|emerging|frontier", parts[0]
            )
            or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", parts[1])
            or parts[2] not in {"monthly", "daily"}
            or parts[3] not in {"vw", "vw_cap", "ew"}
        ):
            msg = "JKP id is country:factor:frequency:weight"
            raise DataError(msg, provider=self.info.id)
        filename = "_".join("[" + part + "]" for part in parts) + ".zip"
        return (
            Request(
                host=self.info.hosts[0],
                path=request_path("public", filename),
                series=query.series[0],
            ),
        )

    def _source(self, body: bytes) -> tuple[str, list[list[str]]]:
        members = archive(body, self.info.id)
        files = [(n, b) for n, b in members.items() if n.endswith(".csv")]
        if len(files) != 1:
            msg = "JKP archive must contain one CSV"
            raise ResponseError(msg, provider=self.info.id)
        name, content = files[0]
        return name, f.csv_rows(content)

    def parse(self, responses: Sequence[Response], query: Query) -> Table:
        """Keep the published return's sign, weighting, universe and native units."""
        _, source = self._source(responses[0].body)
        header = source[0]
        frequency = (
            F.MONTHLY
            if query.series[0].split(":")[2] == "monthly"
            else F.BUSINESS_DAILY
        )
        rows = {}
        for fields in source[1:]:
            row = dict(zip(header, fields, strict=True))
            observed = f.day(row["date"], frequency)
            if observed in rows:
                msg = "JKP selection repeats a date"
                raise ResponseError(msg, provider=self.info.id)
            rows[observed] = {"ret": f.value(row["ret"], self.info.id)}
        return f.table(
            rows,
            {"ret": f.RATE},
            query,
            self.info,
            responses[0],
            frequency,
            notes=(
                "source_units: decimal excess returns in USD",
                "selection: " + query.series[0],
            ),
        )

    def synthesize(
        self, request: Request, response: Response, *, seed: str
    ) -> Response:
        """Retain categorical identifiers and dates; replace all numerical measures."""
        del request
        name, source = self._source(response.body)
        metadata = {"location", "name", "freq", "weighting", "date"}
        rows = [
            [
                value
                if source[0][j] in metadata
                else synthetic_value(seed, i * len(row) + j)
                for j, value in enumerate(row)
            ]
            for i, row in enumerate(source[-3:])
        ]
        return replace(
            response, body=zip_document({name: csv_document([source[0], *rows])})
        )
