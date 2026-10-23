# src/pyeconomics/core/context.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The run context: where a model's warnings go (ADR-0008 decision 13).

A model reports a non-fatal condition through :func:`warn`. What happens next
depends on where the model runs:

- Inside a run, :func:`collect_warnings` has installed a collector. :func:`warn`
  records the :class:`~pyeconomics.core.warnings.ModelWarning` in it and issues
  nothing, so the runner can carry the warnings in the result.
- Outside a run (a model called directly, a doctest, a notebook cell),
  :func:`warn` issues the warning through the :mod:`warnings` module, with the
  stack level pointing at the caller.

The collector lives in a :mod:`contextvars` variable, so concurrent threads and
``asyncio`` tasks each see their own. :func:`library_warnings` changes the
:mod:`warnings` module's process-wide state, so its blocks take turns under one
lock (issue #157).

Examples
--------
>>> from pyeconomics.core import collect_warnings, warn
>>> with collect_warnings() as recorded:
...     warn("zero_volatility", "the Sharpe ratio is undefined at zero volatility")
>>> [(w.code, w.text) for w in recorded]
[('zero_volatility', 'the Sharpe ratio is undefined at zero volatility')]

"""

from __future__ import annotations

import threading
import warnings
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Final

from pyeconomics.core.warnings import ModelWarning

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping
    from typing import TextIO

__all__ = ["collect_warnings", "library_warnings", "warn"]

_COLLECTOR: Final[ContextVar[list[ModelWarning] | None]] = ContextVar(
    "pyeconomics_warning_collector", default=None
)
# Held by each library_warnings block: the warning filters and showwarning are
# process-wide, so two blocks must not change them at once (issue #157).
# Re-entrant, so a block nested in another on the same thread cannot deadlock.
_LIBRARY_LOCK: Final = threading.RLock()


@contextmanager
def collect_warnings() -> Generator[list[ModelWarning], None, None]:
    """Record the warnings :func:`warn` issues inside the ``with`` block.

    The runner installs one around each model call. Collectors nest: the
    innermost one receives the warnings, and the outer one is restored on exit.

    Yields
    ------
    list of ModelWarning
        The warnings recorded so far, in the order they were issued.
    """
    recorded: list[ModelWarning] = []
    token = _COLLECTOR.set(recorded)
    try:
        yield recorded
    finally:
        _COLLECTOR.reset(token)


def warn(code: str, message: str, *, stacklevel: int = 1) -> None:
    """Report a non-fatal condition from inside a computation.

    Parameters
    ----------
    code
        The warning's snake_case code. Codes are stable, and each model's card
        documents its own.
    message
        What happened, for people.
    stacklevel
        Which frame the warning points at when it is issued through the
        :mod:`warnings` module, counted from the code that calls :func:`warn`:
        1, the default, is that line; 2 is its caller. A collector ignores it.

    Raises
    ------
    ValueError
        If ``code`` is not snake_case.

    Examples
    --------
    >>> import warnings
    >>> with warnings.catch_warnings(record=True) as caught:
    ...     warnings.simplefilter("always")
    ...     warn("several_roots", "the equation has two roots")
    >>> caught[0].category.__name__, caught[0].message.code
    ('ModelWarning', 'several_roots')

    """
    warning = ModelWarning(code, message)
    collector = _COLLECTOR.get()
    if collector is not None:
        collector.append(warning)
        return
    warnings.warn(warning, stacklevel=stacklevel + 1)


@contextmanager
def library_warnings(
    library: str, *, codes: Mapping[str, str] | None = None
) -> Generator[list[warnings.WarningMessage], None, None]:
    """Report a library's warnings inside the ``with`` block as the model's own.

    statsmodels and arch reset their own warning filters, so a caller's filters
    (pytest's warnings-as-errors among them) may never see what they warn.
    Inside the block every warning is caught. On a normal exit each one is
    reported with :func:`warn`, once per distinct message: a
    :class:`~pyeconomics.core.warnings.ModelWarning` as it was, any other under
    the code ``codes`` gives its category's name, or ``<library>_warning``. The
    caller may first remove an entry it has shown to be harmless; when the
    block raises, nothing is reported.

    The warning filters and :func:`warnings.showwarning` belong to the whole
    process, so the blocks of concurrent threads take turns under one
    re-entrant lock: a wrapped fit waits for another wrapped fit, never for an
    unwrapped model, and a block nested in another on the same thread runs at
    once. The block records only its own thread's warnings; a warning another
    thread issues meanwhile goes to whatever would have shown it before the
    block, so it is neither attributed to this result nor lost. While a block
    runs, another thread's warnings pass the ``"always"`` filter, so an
    ``"error"`` filter that thread relies on does not raise them (issue #174).
    Keep the block to the library's computation: no I/O, and no waiting on
    another thread.

    Parameters
    ----------
    library
        The library's import name, which prefixes each message.
    codes
        Warning codes by category name, such as
        ``{"ConvergenceWarning": "optimizer_not_converged"}``.

    Yields
    ------
    list of warnings.WarningMessage
        The warnings caught so far.

    Examples
    --------
    >>> import warnings
    >>> with collect_warnings() as recorded:
    ...     with library_warnings("toylib"):
    ...         warnings.warn("rank deficient", RuntimeWarning, stacklevel=1)
    >>> [(w.code, w.text) for w in recorded]
    [('toylib_warning', 'toylib: RuntimeWarning: rank deficient')]

    """
    caught: list[warnings.WarningMessage] = []
    owner = threading.get_ident()
    with _LIBRARY_LOCK, warnings.catch_warnings():
        warnings.simplefilter("always")
        shown = warnings.showwarning

        def record(  # noqa: PLR0913, PLR0917 - warnings.showwarning's signature
            message: Warning | str,
            category: type[Warning],
            filename: str,
            lineno: int,
            file: TextIO | None = None,
            line: str | None = None,
        ) -> None:
            if threading.get_ident() != owner:
                shown(message, category, filename, lineno, file, line)
                return
            caught.append(
                warnings.WarningMessage(message, category, filename, lineno, file, line)
            )

        warnings.showwarning = record
        yield caught
    seen: set[str] = set()
    for item in caught:
        found = item.message
        if isinstance(found, ModelWarning):
            warn(found.code, found.text)
            continue
        kind = type(found).__name__
        text = " ".join(str(found).split())
        if text in seen:
            continue
        seen.add(text)
        code = (codes or {}).get(kind, f"{library}_warning")
        warn(code, f"{library}: {kind}: {text}")
