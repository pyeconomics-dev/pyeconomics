# src/pyeconomics/data/terms.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A source's terms of use, as code (ADR-0011 decisions 7 and 8).

Every provider declares :class:`Terms`: its licence class (ADR-0005), the
public page its terms were read from, the date they were last read, the
attribution and any required notice, whether its data may reach a language
model, and whether its data may be stored (:class:`CachePolicy`). A series may
override the class, ``llm_use``, the cache policy and the notice from the
source's own markers: FRED's copyright tags, the World Bank's
``License_Type``, Eurostat's listed exceptions.

Terms are read again within 13 months (:data:`TERMS_MAX_AGE_MONTHS`), which
turns ROADMAP §5's yearly review into a check: :meth:`Terms.is_stale` takes
the date to judge against, because nothing here reads the clock.

Examples
--------
>>> import datetime as dt
>>> from pyeconomics.data import CachePolicy, LicenceClass, LlmUse, Terms
>>> terms = Terms(
...     licence=LicenceClass.LIBRARY_ONLY,
...     terms_url="https://fred.stlouisfed.org/docs/api/terms_of_use.html",
...     checked=dt.date(2026, 10, 14),
...     attribution="Source: Federal Reserve Bank of St. Louis, FRED.",
...     llm_use=LlmUse.FORBIDDEN,
...     cache=CachePolicy.FORBIDDEN,
... )
>>> terms.stale_after, terms.is_stale(dt.date(2027, 11, 15))
(datetime.date(2027, 11, 14), True)

"""

from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any, Final

from pyeconomics.core import _fields as f
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.core.units import DEFAULT_DATE_BOUNDS

__all__ = ["TERMS_MAX_AGE_MONTHS", "CachePolicy", "Terms"]

#: Terms read longer ago than this are stale: a provider test fails on them.
TERMS_MAX_AGE_MONTHS: Final = 13


class CachePolicy(StrEnum):
    """Whether a source's terms let its data be stored (ADR-0011 decision 14).

    ``FORBIDDEN`` means no cache path at all: the data is fetched live and
    never written to disk, with no opt-in (ADR-0005 rule 4). FRED and ALFRED
    are forbidden. An in-process memo that never outlives the process is not
    storage.
    """

    ALLOWED = "allowed"
    """The data may be cached on the user's machine, under its time-to-live."""
    FORBIDDEN = "forbidden"
    """The terms forbid storage: the data is never written to disk."""


@dataclass(frozen=True, slots=True, kw_only=True)
class Terms:
    """A source's terms of use, as its provider (or a series) declares them."""

    licence: LicenceClass
    """The licence class (ADR-0005)."""
    terms_url: str
    """The public ``https`` page the terms were read from."""
    checked: dt.date
    """The date the terms page was last read."""
    attribution: str
    """The attribution that travels with the data."""
    notice: str | None = None
    """The notice the source requires wherever its data appears, if any."""
    llm_use: LlmUse
    """Whether the data may reach a language model."""
    cache: CachePolicy
    """Whether the data may be stored."""

    def __post_init__(self) -> None:
        """Check every field; accept the enums' values as well as members."""
        f.terms_url(self.terms_url)
        f.day(self.checked, "checked", DEFAULT_DATE_BOUNDS)
        f.text(self.attribution, "attribution", max_length=f.MAX_TEXT_LENGTH)
        f.optional_text(self.notice, "notice", max_length=f.MAX_TEXT_LENGTH)
        object.__setattr__(
            self, "licence", f.choice(LicenceClass, self.licence, "licence")
        )
        object.__setattr__(self, "llm_use", f.choice(LlmUse, self.llm_use, "llm_use"))
        object.__setattr__(self, "cache", f.choice(CachePolicy, self.cache, "cache"))

    @property
    def stale_after(self) -> dt.date:
        """The last day on which the terms count as current.

        It is :data:`TERMS_MAX_AGE_MONTHS` months after :attr:`checked`, on the
        same day of the month or the month's last day when that is shorter.
        """
        index = self.checked.year * 12 + self.checked.month - 1 + TERMS_MAX_AGE_MONTHS
        year, month = divmod(index, 12)
        last = calendar.monthrange(year, month + 1)[1]
        return dt.date(year, month + 1, min(self.checked.day, last))

    def is_stale(self, on: dt.date) -> bool:
        """Return whether the terms are older than 13 months on the date ``on``.

        Examples
        --------
        >>> import datetime as dt
        >>> from pyeconomics.data import CachePolicy, LicenceClass, LlmUse, Terms
        >>> terms = Terms(
        ...     licence=LicenceClass.HOSTED_SAFE,
        ...     terms_url="https://www.bls.gov/developers/termsOfService.htm",
        ...     checked=dt.date(2026, 1, 31),
        ...     attribution="Source: US Bureau of Labor Statistics.",
        ...     llm_use=LlmUse.ALLOWED,
        ...     cache=CachePolicy.ALLOWED,
        ... )
        >>> terms.is_stale(dt.date(2027, 2, 28)), terms.is_stale(dt.date(2027, 3, 1))
        (False, True)

        """
        return on > self.stale_after

    def with_overrides(
        self,
        *,
        licence: LicenceClass | None = None,
        llm_use: LlmUse | None = None,
        cache: CachePolicy | None = None,
        notice: str | None = None,
    ) -> Terms:
        """Return the terms a series carries when its source's markers differ.

        Only the class, ``llm_use``, the cache policy and the notice may differ
        per series; the page, date and attribution are the provider's.
        """
        changes: dict[str, Any] = {
            name: value
            for name, value in (
                ("licence", licence),
                ("llm_use", llm_use),
                ("cache", cache),
                ("notice", notice),
            )
            if value is not None
        }
        return replace(self, **changes)

    def to_dict(self) -> dict[str, object]:
        """Return the terms as JSON-ready values."""
        return {
            "licence": self.licence.value,
            "terms_url": self.terms_url,
            "checked": self.checked.isoformat(),
            "attribution": self.attribution,
            "notice": self.notice,
            "llm_use": self.llm_use.value,
            "cache": self.cache.value,
        }

    def canonical_json(self) -> bytes:
        """Return the terms as canonical JSON (RFC 8785)."""
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, data: object) -> Terms:
        """Read terms back from :meth:`to_dict`'s form, refusing any other."""
        values: dict[str, Any] = dict(f.mapping(data, "terms", _TERMS_KEYS))
        values["checked"] = f.parse_day(values["checked"], "checked")
        return cls(**values)

    @classmethod
    def from_json(cls, document: str | bytes) -> Terms:
        """Read terms back from their canonical JSON."""
        return cls.from_dict(f.load_json(document))


_TERMS_KEYS: Final = (
    "licence",
    "terms_url",
    "checked",
    "attribution",
    "notice",
    "llm_use",
    "cache",
)
