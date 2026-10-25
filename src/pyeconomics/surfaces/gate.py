# src/pyeconomics/surfaces/gate.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The ``llm_use`` gate's final check (ADR-0012 decision 14).

A surface that feeds a language model (the MCP server, the AI narrative) asks
for data under an :class:`~pyeconomics.core.provenance.LlmUsePolicy`, and the
resolver passes over every source the policy does not permit. This module is
the defence in depth behind that: before a result or a series reaches the
model, every source record it carries is checked again, and the whole answer
is withheld with :class:`~pyeconomics.data.errors.LlmUseError` (the
``llm-use-forbidden`` problem) if one is still ``forbidden``, or ``unclear``
without the user's opt-in. Nothing is trimmed or redacted: an answer passes
whole or not at all.

- :func:`check_records` checks :class:`~pyeconomics.core.provenance.DataSource`
  records, such as a result's manifest's;
- :func:`check_document` checks a canonical JSON document a surface is about to
  return (a run's result, or a series' document), reading every record it holds,
  so a surface checks the very bytes it sends, wherever they were made.

Nothing here imports the data layer until it has something to refuse, so
``import pyeconomics.surfaces`` still loads no data module.

Examples
--------
>>> from pyeconomics.core import LlmUsePolicy
>>> check_document({"manifest": {"data_sources": []}}, LlmUsePolicy.ALLOWED_ONLY)
>>> check_document(
...     {"sources": [{"provider": "fred", "series_id": "UNRATE", "llm_use": "forbidden",
...       "licence": "library-only", "terms_url": None}]},
...     LlmUsePolicy.ALLOW_UNCLEAR,
... )
Traceback (most recent call last):
...
pyeconomics.data.errors.LlmUseError: the answer carries data from fred (UNRATE), whose terms make it forbidden for language models, which the allow-unclear policy does not permit; it is withheld
"""  # noqa: E501 - doctest lines cannot wrap

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, NoReturn

from pyeconomics.core.provenance import LicenceClass, LlmUse, LlmUsePolicy

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pyeconomics.core.provenance import DataSource

__all__ = ["check_document", "check_records"]


def _refuse(  # noqa: PLR0913 - the record's facts, one by one
    subject: str,
    *,
    provider: str,
    series: str,
    licence: LicenceClass,
    llm_use: LlmUse,
    terms_url: str | None,
    policy: LlmUsePolicy,
) -> NoReturn:
    from pyeconomics.data.errors import LlmUseError  # noqa: PLC0415 - when refusing

    msg = (
        f"{subject} carries data from {provider} ({series}), whose terms make it "
        f"{llm_use.value} for language models, which the {policy.value} policy "
        "does not permit; it is withheld"
    )
    raise LlmUseError(
        msg,
        provider=provider,
        licence=licence,
        llm_use=llm_use,
        terms_url=terms_url,
    )


def check_records(
    records: Iterable[DataSource],
    policy: LlmUsePolicy,
    *,
    subject: str = "the answer",
) -> None:
    """Refuse records of which one is not permitted by the policy.

    Raises
    ------
    LlmUseError
        Naming the first such record's provider, series and ``llm_use`` class.
    """
    for record in records:
        if not policy.permits(record.llm_use):
            _refuse(
                subject,
                provider=record.provider,
                series=record.series_id,
                licence=record.licence,
                llm_use=record.llm_use,
                terms_url=record.terms_url,
                policy=policy,
            )


def _records(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return every source record a result's or a series' document holds."""
    manifest = document.get("manifest")
    bound = manifest.get("data_sources") if isinstance(manifest, Mapping) else None
    held = [*(bound or ()), *(document.get("sources") or ())]
    return [record for record in held if isinstance(record, Mapping)]


def check_document(
    document: Mapping[str, Any],
    policy: LlmUsePolicy,
    *,
    subject: str = "the answer",
) -> None:
    """Refuse a canonical document holding a record the policy does not permit.

    The document is a run's result (``manifest.data_sources``) or a series'
    document (``sources``). A record whose ``llm_use`` is missing or not one of
    the classes is refused as ``forbidden``: what cannot be read is not
    permitted.

    Raises
    ------
    LlmUseError
        Naming the first such record's provider, series and ``llm_use`` class.
    """
    for record in _records(document):
        try:
            use = LlmUse(str(record.get("llm_use")))
        except ValueError:
            use = LlmUse.FORBIDDEN
        if policy.permits(use):
            continue
        try:
            licence = LicenceClass(str(record.get("licence")))
        except ValueError:
            licence = LicenceClass.LIBRARY_ONLY
        terms = record.get("terms_url")
        _refuse(
            subject,
            provider=str(record.get("provider") or "an unnamed provider"),
            series=str(record.get("series_id") or "an unnamed series"),
            licence=licence,
            llm_use=use,
            terms_url=terms if isinstance(terms, str) else None,
            policy=policy,
        )
