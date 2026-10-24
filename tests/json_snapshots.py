# tests/json_snapshots.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Syrupy JSON snapshots with LF line ends, for every snapshot test in the suite.

Syrupy's JSON extension writes text, which Windows writes with CRLF, while the
repository keeps LF everywhere (.gitattributes): a snapshot rewritten on Windows
would then differ from the one committed. This extension writes the same JSON as
UTF-8 bytes. Use it with ``snapshot.use_extension(LFJSONExtension)``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from syrupy.extensions.json import JSONSnapshotExtension
from syrupy.extensions.single_file import WriteMode

if TYPE_CHECKING:
    from syrupy.types import SerializableData, SerializedData

__all__ = ["LFJSONExtension"]


class LFJSONExtension(JSONSnapshotExtension):
    """Syrupy's JSON snapshots, written as UTF-8 bytes with LF line ends."""

    _write_mode = WriteMode.BINARY

    def serialize(self, data: SerializableData, **kwargs: Any) -> SerializedData:  # noqa: ANN401 - syrupy's filters
        """Serialize as the JSON extension does, then encode to UTF-8."""
        text = super().serialize(data, **kwargs)
        assert isinstance(text, str)
        return text.encode("utf-8")
