# src/pyeconomics/core/_fields.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Field checks shared by the provenance record and the data value types.

Each check returns the value it accepted, normalized, or raises
:class:`~pyeconomics.core.errors.InputError` naming the field. Text never holds
``://``, so no field but a source's terms page can carry a URL (ADR-0011
decisions 2 and 16), and the one URL check, :func:`terms_url`, accepts only a
public ``https`` page with no user information, port, query or fragment.

The JSON helpers read canonical JSON back strictly: no NaN or infinity, no
duplicate keys, no deeper nesting than the canonical writer allows, and
exactly the keys a type writes.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import TYPE_CHECKING, Final
from urllib.parse import urlsplit

from pyeconomics.core.canonical import MAX_DEPTH
from pyeconomics.core.errors import InputError

if TYPE_CHECKING:
    from pyeconomics.core.units import DateBounds

#: The longest identifier: a provider id, a field name or a warning code.
MAX_IDENTIFIER_LENGTH: Final = 64
#: The longest title, dataset name or series id.
MAX_NAME_LENGTH: Final = 256
#: The longest attribution or notice.
MAX_TEXT_LENGTH: Final = 1_000
#: The longest terms URL.
MAX_URL_LENGTH: Final = 512

_IDENTIFIER: Final = re.compile(r"[a-z][a-z0-9_]*")
_CONTROL: Final = re.compile(r"[\x00-\x1f\x7f]")
_ISO_DATE: Final = re.compile(r"\d{4}-\d{2}-\d{2}")
# A DNS name of two or more labels whose last label starts with a letter, so
# neither an IP address nor a bare host name passes.
_HOST: Final = re.compile(
    r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z](?:[a-z0-9-]*[a-z0-9])?"
)


def fail(message: str) -> InputError:
    """Return the error a failed check raises."""
    return InputError(message)


def text(value: object, what: str, *, max_length: int = MAX_NAME_LENGTH) -> str:
    """Accept non-empty, single-line text that holds no URL."""
    if not isinstance(value, str):
        msg = f"{what} must be a string, not {type(value).__name__}"
        raise fail(msg)
    if not value.strip():
        msg = f"{what} must not be empty"
        raise fail(msg)
    if len(value) > max_length:
        msg = f"{what} must be at most {max_length} characters, not {len(value)}"
        raise fail(msg)
    if _CONTROL.search(value):
        msg = f"{what} must not contain control characters or line breaks"
        raise fail(msg)
    if "://" in value:
        msg = f"{what} must not contain a URL"
        raise fail(msg)
    return value


def optional_text(
    value: object, what: str, *, max_length: int = MAX_NAME_LENGTH
) -> str | None:
    """Accept ``None`` or what :func:`text` accepts."""
    return None if value is None else text(value, what, max_length=max_length)


def identifier(value: object, what: str) -> str:
    """Accept a snake_case identifier such as a provider id or a warning code."""
    checked = text(value, what, max_length=MAX_IDENTIFIER_LENGTH)
    if not _IDENTIFIER.fullmatch(checked):
        msg = f"{what} must be snake_case (a-z, 0-9 and _, starting with a letter)"
        raise fail(msg)
    return checked


def identifiers(
    values: object, what: str, *, max_items: int, unique: bool = True
) -> tuple[str, ...]:
    """Accept a sequence of identifiers, at most ``max_items`` long."""
    items = sequence(values, what, max_items=max_items)
    checked = tuple(identifier(item, f"each of {what}") for item in items)
    if unique and len(set(checked)) != len(checked):
        msg = f"{what} must not repeat an entry"
        raise fail(msg)
    return checked


def sequence(values: object, what: str, *, max_items: int) -> tuple[object, ...]:
    """Accept a list or tuple of at most ``max_items`` items."""
    if not isinstance(values, Sequence) or isinstance(values, str | bytes):
        msg = f"{what} must be a list or tuple, not {type(values).__name__}"
        raise fail(msg)
    if len(values) > max_items:
        msg = f"{what} holds at most {max_items} items, not {len(values)}"
        raise fail(msg)
    return tuple(values)


def instance[T](value: object, cls: type[T], what: str) -> T:
    """Accept an instance of ``cls``."""
    if not isinstance(value, cls):
        msg = f"{what} must be a {cls.__name__}, not {type(value).__name__}"
        raise fail(msg)
    return value


def choice[E: StrEnum](cls: type[E], value: object, what: str) -> E:
    """Accept a member of the enum ``cls``, or its value."""
    if isinstance(value, cls):
        return value
    if isinstance(value, str):
        try:
            return cls(value)
        except ValueError:
            pass
    allowed = ", ".join(member.value for member in cls)
    msg = f"{what} must be one of {allowed}, not {value!r}"
    raise fail(msg)


def flag(value: object, what: str) -> bool:
    """Accept a ``bool``, never a number standing in for one."""
    if not isinstance(value, bool):
        msg = f"{what} must be true or false, not {type(value).__name__}"
        raise fail(msg)
    return value


def day(value: object, what: str, bounds: DateBounds) -> dt.date:
    """Accept a calendar date (not a ``datetime``) within ``bounds``."""
    if not isinstance(value, dt.date) or isinstance(value, dt.datetime):
        msg = f"{what} must be a date, not {type(value).__name__}"
        raise fail(msg)
    if not bounds.contains(value):
        msg = f"{what} must lie between {bounds.lower} and {bounds.upper}, not {value}"
        raise fail(msg)
    return value


def optional_day(value: object, what: str, bounds: DateBounds) -> dt.date | None:
    """Accept ``None`` or what :func:`day` accepts."""
    return None if value is None else day(value, what, bounds)


def instant(value: object, what: str) -> dt.datetime:
    """Accept a timezone-aware ``datetime``, normalized to UTC."""
    if not isinstance(value, dt.datetime):
        msg = f"{what} must be a datetime, not {type(value).__name__}"
        raise fail(msg)
    if value.utcoffset() is None:
        msg = f"{what} must carry a time zone"
        raise fail(msg)
    return value.astimezone(dt.UTC)


def optional_instant(value: object, what: str) -> dt.datetime | None:
    """Accept ``None`` or what :func:`instant` accepts."""
    return None if value is None else instant(value, what)


def terms_url(value: object, what: str = "terms_url") -> str:
    """Accept the public ``https`` address of a source's terms page.

    It must name a host and may have a path, but no user information, port,
    query or fragment, so it can carry neither a credential nor a request.
    """
    if not isinstance(value, str):
        msg = f"{what} must be a string, not {type(value).__name__}"
        raise fail(msg)
    if len(value) > MAX_URL_LENGTH or _CONTROL.search(value) or " " in value:
        msg = f"{what} must be a single URL of at most {MAX_URL_LENGTH} characters"
        raise fail(msg)
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as error:
        msg = f"{what} is not a valid URL"
        raise fail(msg) from error
    if parts.scheme != "https":
        msg = f"{what} must use https"
        raise fail(msg)
    if parts.username is not None or parts.password is not None or port is not None:
        msg = f"{what} must not carry user information or a port"
        raise fail(msg)
    if parts.query or parts.fragment or "?" in value or "#" in value:
        msg = f"{what} must not carry a query or a fragment"
        raise fail(msg)
    if not _HOST.fullmatch(parts.netloc):
        msg = f"{what} must name a lowercase host such as www.example.org"
        raise fail(msg)
    return value


# --- reading canonical JSON back ------------------------------------------------


def _no_constant(name: str) -> object:
    msg = f"canonical JSON has no {name}"
    raise fail(msg)


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = f"the JSON object repeats the key {key!r}"
            raise fail(msg)
        result[key] = value
    return result


def _check_depth(value: object) -> None:
    """Refuse a value nested deeper than canonical JSON's writer allows."""
    pending: list[tuple[object, int]] = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > MAX_DEPTH:
            msg = f"the JSON document nests deeper than {MAX_DEPTH} levels"
            raise fail(msg)
        if isinstance(item, dict):
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)


def load_json(document: object) -> object:
    """Parse JSON strictly: no NaN or infinity, no repeated keys, bounded depth.

    The depth bound is the canonical writer's (:data:`MAX_DEPTH`), checked after
    parsing, so it holds whatever recursion limit the interpreter's parser has.
    """
    if not isinstance(document, str | bytes):
        msg = f"a JSON document is a str or bytes, not {type(document).__name__}"
        raise fail(msg)
    try:
        value = json.loads(
            document, parse_constant=_no_constant, object_pairs_hook=_unique_keys
        )
    except (ValueError, RecursionError) as error:
        if isinstance(error, InputError):
            raise
        msg = f"not a JSON document: {error}"
        raise fail(msg) from error
    _check_depth(value)
    return value


def mapping(value: object, what: str, keys: Sequence[str]) -> Mapping[str, object]:
    """Accept a JSON object holding exactly ``keys``."""
    if not isinstance(value, Mapping):
        msg = f"{what} must be a JSON object, not {type(value).__name__}"
        raise fail(msg)
    missing = sorted(set(keys) - set(value))
    extra = sorted(set(value) - set(keys))
    if missing or extra:
        msg = f"{what} has missing keys {missing} or unknown keys {extra}"
        raise fail(msg)
    return value


def parse_day(value: object, what: str) -> dt.date:
    """Read an ISO 8601 calendar date written as ``YYYY-MM-DD``."""
    if not isinstance(value, str) or not _ISO_DATE.fullmatch(value):
        msg = f"{what} must be a YYYY-MM-DD date, not {value!r}"
        raise fail(msg)
    try:
        return dt.date.fromisoformat(value)
    except ValueError as error:
        msg = f"{what} is not a calendar date: {value!r}"
        raise fail(msg) from error


def parse_optional_day(value: object, what: str) -> dt.date | None:
    """Read ``null`` or what :func:`parse_day` reads."""
    return None if value is None else parse_day(value, what)


def parse_instant(value: object, what: str) -> dt.datetime | None:
    """Read ``null`` or an ISO 8601 datetime with its UTC offset."""
    if value is None:
        return None
    if not isinstance(value, str) or "T" not in value:
        msg = f"{what} must be an ISO 8601 datetime, not {value!r}"
        raise fail(msg)
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError as error:
        msg = f"{what} is not an ISO 8601 datetime: {value!r}"
        raise fail(msg) from error
