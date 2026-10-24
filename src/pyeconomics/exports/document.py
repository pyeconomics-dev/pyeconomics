# src/pyeconomics/exports/document.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""JSON exports: canonical JSON with the manifest embedded (ADR-0012 decision 6).

A result's JSON export is its canonical bytes, ``Result.to_json()`` in UTF-8:
the same bytes every surface returns, with no trailing newline, so its SHA-256
identifies it. A batch is ``{"attributions": [...], "model_id": ...,
"model_version": ..., "results": [...]}`` with each run's ``to_dict()``. Data is
the document ``pyeconomics data get --format json`` prints: the frame, the
concept it answers, the source records, the candidates passed over and the
attributions. Records are ``{"attributions": [...], "records": {...}}``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyeconomics.exports.layout import Subject

__all__ = ["to_json"]


def to_json(subject: Subject) -> bytes:
    """Return a subject's canonical JSON document."""
    return subject.document
