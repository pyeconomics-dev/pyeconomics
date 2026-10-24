# src/pyeconomics/surfaces/invoke.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The one invocation path every surface runs a model through (ADR-0012 decision 2).

:func:`invoke` resolves a model id (an alias warns and resolves, ADR-0003), decodes
the inputs through :mod:`~pyeconomics.surfaces.codec` and runs the model through
:mod:`pyeconomics.core.runner`. Given a :class:`BindRequest`, it first binds the
model's data through the data layer, with the decoded inputs as overrides, so the
result's manifest records every series, vintage and retrieval time exactly as
``pyeconomics.run(model_id, pyeconomics.bind(...))`` would. The data layer is
imported only then: a run that reads no data loads no data module.

The command line, the REST API, the MCP server and the exports call this and
nothing else; none of them calls the runner, ``pyeconomics.run`` or
``pyeconomics.bind`` itself.

``pyeconomics.surfaces`` exports the function :func:`invoke`, which hides this
module there, as ``pyeconomics.core``'s ``model`` decorator hides its module:
import from this module by its path (``from pyeconomics.surfaces.invoke import
BindRequest``).

Examples
--------
>>> from pyeconomics.surfaces.invoke import BindRequest
>>> BindRequest(as_of="2019-06-28").to_dict()["as_of"]
'2019-06-28'
"""

from __future__ import annotations

import datetime as dt
import itertools
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from pyeconomics.core import _fields as f
from pyeconomics.core.binding import DEFAULT_PROFILE, VintagePolicy
from pyeconomics.core.errors import InputError
from pyeconomics.core.runner import MAX_BATCH_ROWS, run_model, run_model_batch
from pyeconomics.surfaces import codec

if TYPE_CHECKING:
    from pyeconomics.core.results import BatchResult, Result

__all__ = ["BindRequest", "invoke", "invoke_batch"]


def _strings(value: object, what: str) -> Mapping[str, str]:
    if not isinstance(value, Mapping) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    ):
        msg = f"{what} maps field names to concept ids, both text"
        raise f.fail(msg)
    return MappingProxyType(dict(value))


def _named(value: object, what: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(k, str) for k in value):
        msg = f"{what} maps parameter names to values"
        raise f.fail(msg)
    return MappingProxyType(dict(value))


def _day(value: object) -> dt.date | None:
    if isinstance(value, str):
        return f.parse_day(value, "as_of")
    if value is not None and (
        not isinstance(value, dt.date) or isinstance(value, dt.datetime)
    ):
        msg = f"as_of is a date, not {type(value).__name__}"
        raise f.fail(msg)
    return value


@dataclass(frozen=True, slots=True, init=False)
class BindRequest:
    """A request to bind a model's data before it runs, as ``pyeconomics.bind`` does.

    Parameters
    ----------
    as_of
        The evaluation date, a ``date`` or an ISO ``YYYY-MM-DD`` text: each binding
        reads what was published by then. ``None`` reads the latest data.
    vintage
        A :class:`~pyeconomics.core.binding.VintagePolicy`, or its value, for every
        binding in place of their own.
    profile
        The named set of bindings to resolve.
    concepts
        ``{field: concept}``: rebinds a field to another concept of the same unit
        kind and frequency.
    parameters
        Values of concept parameters, such as an SEP ``meeting``.

    Raises
    ------
    InputError
        For a date that is not a calendar date, an unknown vintage policy, or
        concepts or parameters that are not mappings named by text.
    """

    as_of: dt.date | None
    vintage: VintagePolicy | None
    profile: str
    concepts: Mapping[str, str]
    parameters: Mapping[str, object]

    def __init__(
        self,
        *,
        as_of: dt.date | str | None = None,
        vintage: VintagePolicy | str | None = None,
        profile: str = DEFAULT_PROFILE,
        concepts: Mapping[str, str] | None = None,
        parameters: Mapping[str, object] | None = None,
    ) -> None:
        """Normalize the date and the policy, and hold read-only mappings."""
        policy = (
            None if vintage is None else f.choice(VintagePolicy, vintage, "vintage")
        )
        object.__setattr__(self, "as_of", _day(as_of))
        object.__setattr__(self, "vintage", policy)
        object.__setattr__(self, "profile", f.text(profile, "profile"))
        object.__setattr__(self, "concepts", _strings(concepts or {}, "concepts"))
        object.__setattr__(self, "parameters", _named(parameters or {}, "parameters"))

    def to_dict(self) -> dict[str, object]:
        """Return the request as JSON-ready values, the shape a bundle records."""
        return {
            "as_of": None if self.as_of is None else self.as_of.isoformat(),
            "vintage": None if self.vintage is None else self.vintage.value,
            "profile": self.profile,
            "concepts": dict(self.concepts),
            "parameters": dict(self.parameters),
        }


def invoke(
    model_id: str,
    inputs: object = None,
    /,
    *,
    bind: BindRequest | None = None,
    mode: str | None = None,
) -> Result[Any, Any]:
    """Run a registered model for a surface and return its result.

    Parameters
    ----------
    model_id
        A model id or alias; an alias warns with ``PyeconomicsDeprecationWarning``
        and the result carries the canonical id.
    inputs
        ``None``, a mapping, JSON text or bytes, or ``field=value`` strings, as
        :func:`~pyeconomics.surfaces.codec.decode` takes them.
    bind
        Bind the model's data first, with ``inputs`` as overrides; ``None`` runs
        on ``inputs`` alone.
    mode
        ``library`` or ``hosted`` for the bind; the configured mode by default. A
        run that reads no data reads no source, so without ``bind`` it is unused.

    Returns
    -------
    Result
        The result, whose ``to_json()`` is the same text ``pyeconomics.run``
        returns for the same inputs and data.

    Raises
    ------
    ModelNotFoundError
        If no model or alias has the id.
    InputError
        If the inputs cannot be decoded or fail validation, or ``mode`` is not a
        mode.
    InputTooLargeError
        If JSON inputs are larger than the codec's limit.
    DataError, LicenceError, CredentialError, OfflineError
        As the bind raises them.
    DomainError, ConvergenceError
        As the model raises them.
    """
    from pyeconomics.core.registry import installed  # noqa: PLC0415 - as run() does

    model = installed().resolve(model_id, stacklevel=3)
    decoded = codec.decode(inputs, model)
    if bind is None:
        return run_model(model, decoded)
    # The data layer arrives with the first bind (ADR-0012 decision 1).
    from pyeconomics.data.bindings import bind_model  # noqa: PLC0415
    from pyeconomics.data.modes import Mode  # noqa: PLC0415

    bound = bind_model(
        model,
        as_of=bind.as_of,
        vintage=bind.vintage,
        mode=None if mode is None else f.choice(Mode, mode, "mode"),
        profile=bind.profile,
        concepts=bind.concepts,
        parameters=bind.parameters,
        overrides=decoded,
    )
    return run_model(model, bound)


def invoke_batch(
    model_id: str, rows: Iterable[object], /, *, limit: int = codec.MAX_INPUT_BYTES
) -> BatchResult:
    """Run a registered model once per row of inputs, for a surface.

    Each row is decoded as :func:`invoke` decodes its inputs, then the rows run
    through :func:`~pyeconomics.core.runner.run_model_batch`, so the batch's
    results are ``pyeconomics.run_batch``'s. A batch reads no data.

    Parameters
    ----------
    model_id
        A model id or alias; an alias warns and the results carry the canonical
        id.
    rows
        Each row's inputs: a mapping, JSON text or bytes, or ``field=value``
        strings. At most :data:`~pyeconomics.core.runner.MAX_BATCH_ROWS` rows.
    limit
        The largest JSON row decoded, in bytes.

    Raises
    ------
    ModelNotFoundError
        If no model or alias has the id.
    InputError
        For more than ``MAX_BATCH_ROWS`` rows, or a row that cannot be decoded
        (its message names the row, counted from 0) or fails validation.
    DomainError, ConvergenceError
        As the model raises them, with a note naming the row.
    """
    from pyeconomics.core.registry import installed  # noqa: PLC0415 - as run() does

    model = installed().resolve(model_id, stacklevel=3)
    taken = list(itertools.islice(rows, MAX_BATCH_ROWS + 1))
    if len(taken) > MAX_BATCH_ROWS:
        msg = f"a batch holds at most {MAX_BATCH_ROWS} rows"
        raise InputError(msg)
    decoded: list[dict[str, object]] = []
    for index, row in enumerate(taken):
        try:
            decoded.append(codec.decode(row, model, limit=limit))
        except codec.InputTooLargeError:
            raise
        except InputError as error:
            msg = f"row {index} of the batch: {error}"
            raise InputError(msg) from None
    return run_model_batch(model, decoded)
