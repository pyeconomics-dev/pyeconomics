# src/pyeconomics/data/records.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Bounded identifier and filing records, separate from numeric frames.

Records are never binding inputs and are not put in the frame cache. All text
uses the same no-URL rule as frames; upstream URLs and document paths are omitted.
"""

from __future__ import annotations

import datetime as dt  # noqa: TC003 - pydantic resolves date annotations
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pyeconomics.core import _fields as f
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.provenance import DATA_DATE_BOUNDS
from pyeconomics.data.terms import Terms  # noqa: TC001 - pydantic resolves fields


class Record(BaseModel):
    """An immutable record with bounded text and no request information."""

    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)

    @field_validator("*", mode="after")
    @classmethod
    def _text(cls, value: object) -> object:
        if isinstance(value, str):
            return f.text(value, "record text", max_length=512)
        return value


class FigiMapping(Record):
    """One instrument returned for an identifier mapping job."""

    kind: Literal["figi"] = "figi"
    identifier_type: str
    identifier: str
    figi: str
    ticker: str | None = None
    name: str | None = None
    exchange: str | None = None
    market_sector: str | None = None
    security_type: str | None = None
    composite_figi: str | None = None
    share_class_figi: str | None = None


class Filing(Record):
    """One EDGAR submission's identifiers and dates; no document name or path."""

    kind: Literal["filing"] = "filing"
    cik: str = Field(pattern=r"^\d{10}$")
    accession: str = Field(pattern=r"^\d{10}-\d{2}-\d{6}$")
    form: str
    filed: dt.date
    report_date: dt.date | None = None

    @field_validator("filed", "report_date")
    @classmethod
    def _date(cls, value: dt.date | None) -> dt.date | None:
        return None if value is None else f.day(value, "filing date", DATA_DATE_BOUNDS)


class Records(Record):
    """Typed records with source terms and retrieval time, bounded to 100,000.

    ``canonical_json`` and ``from_json`` provide the sole serialized form. A
    discriminator prevents one record kind being silently read as another.
    """

    provider: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    terms: Terms
    retrieved_at: dt.datetime
    rows: tuple[Annotated[FigiMapping | Filing, Field(discriminator="kind")], ...] = (
        Field(max_length=100_000)
    )

    @field_validator("retrieved_at")
    @classmethod
    def _instant(cls, value: dt.datetime) -> dt.datetime:
        return f.instant(value, "retrieved_at")

    def canonical_json(self) -> bytes:
        """Return RFC 8785 JSON without arbitrary upstream fields."""
        return canonical_json(self.model_dump(mode="json"))

    @classmethod
    def from_json(cls, document: str | bytes) -> Self:
        """Read strict JSON, refusing unknown and duplicate keys."""
        return cls.model_validate(f.load_json(document))
