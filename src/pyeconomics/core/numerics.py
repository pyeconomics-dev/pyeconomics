# src/pyeconomics/core/numerics.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Root finding under one convergence policy (ADR-0008 decision 11).

:func:`find_root` finds a root of a scalar function with Brent's method
(:func:`scipy.optimize.brentq`) inside a bracket, in four steps:

1. **Scan.** Evaluate the function on ``policy.scan_points`` evenly spaced
   points of the bracket and collect every sub-interval whose ends differ in
   sign, and every point where it is exactly zero.
2. **Expand.** If the scan finds none and ``limits`` are given, widen the
   bracket geometrically: move the end whose value is smaller in magnitude
   outwards by ``policy.expansion_factor`` times the bracket's width, never
   past ``limits``, at most ``policy.max_expansions`` times, until the ends
   differ in sign. Then scan the widened bracket.
3. **Choose.** With no sign change, raise :class:`ConvergenceError`. With
   several, take the smallest root and issue a ``several_roots``
   :class:`ModelWarning`; a model whose convention differs (an IRR nearest
   a guess, say) chooses for itself from :func:`bracket_roots`.
4. **Refine.** Run Brent's method on the chosen sub-interval with the
   policy's ``xtol``, ``rtol`` and ``maxiter``; failure to converge raises
   :class:`ConvergenceError`.

The scan records exact zeros, including either inclusive bracket endpoint,
as well as sign changes (a clarification of ADR-0008 decision 11). A root
that touches zero between grid points, or two roots closer together than the
grid spacing, can go unseen. A model that must not miss such roots chooses
its own grid.

Examples
--------
>>> from pyeconomics.core import find_root
>>> round(find_root(lambda x: x * x - 2.0, 0.0, 2.0).root, 12)
1.414213562373

"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

import numpy as np

from pyeconomics.core.context import warn
from pyeconomics.core.errors import ConvergenceError, InputError

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "DEFAULT_ROOT_POLICY",
    "RootPolicy",
    "RootResult",
    "bracket_roots",
    "find_root",
]

# scipy.optimize.brentq refuses an rtol below four machine epsilons.
_MIN_RTOL: Final = 4 * float(np.finfo(float).eps)
_MIN_SCAN_POINTS: Final = 2


@dataclass(frozen=True, slots=True)
class RootPolicy:
    """Tolerances and limits for :func:`find_root`.

    The defaults are SciPy's own for :func:`scipy.optimize.brentq`
    (``xtol=2e-12``, ``rtol=4*eps``, ``maxiter=100``) and Numerical Recipes'
    bracket expansion factor of 1.6.

    Raises
    ------
    ValueError
        If a tolerance or limit is out of range.

    """

    xtol: float = 2e-12
    rtol: float = _MIN_RTOL
    maxiter: int = 100
    expansion_factor: float = 1.6
    max_expansions: int = 50
    scan_points: int = 64

    def __post_init__(self) -> None:
        """Reject tolerances and limits the method cannot honour."""
        problems = [
            f"xtol must be positive, not {self.xtol!r}"
            if not (math.isfinite(self.xtol) and self.xtol > 0)
            else "",
            f"rtol must be at least {_MIN_RTOL!r}, not {self.rtol!r}"
            if not (math.isfinite(self.rtol) and self.rtol >= _MIN_RTOL)
            else "",
            f"maxiter must be at least 1, not {self.maxiter!r}"
            if self.maxiter < 1
            else "",
            f"expansion_factor must exceed 1, not {self.expansion_factor!r}"
            if not (math.isfinite(self.expansion_factor) and self.expansion_factor > 1)
            else "",
            f"max_expansions must not be negative, not {self.max_expansions!r}"
            if self.max_expansions < 0
            else "",
            f"scan_points must be at least 2, not {self.scan_points!r}"
            if self.scan_points < _MIN_SCAN_POINTS
            else "",
        ]
        message = "; ".join(p for p in problems if p)
        if message:
            raise ValueError(message)


#: The policy :func:`find_root` uses unless given another.
DEFAULT_ROOT_POLICY: Final = RootPolicy()


@dataclass(frozen=True, slots=True)
class RootResult:
    """A root and how it was found."""

    root: float
    """The root."""
    bracket: tuple[float, float]
    """The bracket that was scanned, after any expansion."""
    candidates: int
    """How many roots the scan found; more than one issued a warning."""
    iterations: int
    """Brent's method's iterations (0 when the scan hit the root exactly)."""
    function_calls: int = field(default=0)
    """Evaluations of the function, across the scan, expansion and refinement."""


class _Counted:
    """Wrap a function, count its calls and check it returns finite values."""

    def __init__(self, function: Callable[[float], float]) -> None:
        self.function = function
        self.calls = 0

    def __call__(self, x: float) -> float:
        self.calls += 1
        value = float(self.function(float(x)))
        if not math.isfinite(value):
            msg = f"the function is not finite at {x!r} (it returned {value!r})"
            raise ConvergenceError(msg)
        return value


def _check_bracket(lower: float, upper: float, what: str) -> None:
    if not (math.isfinite(lower) and math.isfinite(upper)):
        msg = f"the {what} must be finite, not [{lower!r}, {upper!r}]"
        raise InputError(msg)
    if lower >= upper:
        msg = f"the {what}'s lower end {lower!r} is not below {upper!r}"
        raise InputError(msg)


def bracket_roots(
    function: Callable[[float], float],
    lower: float,
    upper: float,
    *,
    points: int = DEFAULT_ROOT_POLICY.scan_points,
) -> list[tuple[float, float]]:
    """Scan ``[lower, upper]`` and return the sub-intervals that hold a root.

    A sub-interval ``(a, b)`` with ``a < b`` has ends of opposite sign; one
    with ``a == b`` is a point where the function is exactly zero. They are
    in increasing order.

    Raises
    ------
    InputError
        If the bracket is not finite and increasing, or ``points < 2``.
    ConvergenceError
        If the function is not finite at a grid point.

    Examples
    --------
    >>> bracket_roots(lambda x: (x - 1) * (x - 3), 0.0, 4.0, points=5)
    [(1.0, 1.0), (3.0, 3.0)]

    """
    _check_bracket(lower, upper, "bracket")
    if points < _MIN_SCAN_POINTS:
        msg = f"the scan needs at least 2 points, not {points}"
        raise InputError(msg)
    counted = function if isinstance(function, _Counted) else _Counted(function)
    grid = [float(x) for x in np.linspace(lower, upper, points)]
    values = [counted(x) for x in grid]
    found: list[tuple[float, float]] = []
    for i, (x, value) in enumerate(zip(grid, values, strict=True)):
        if value == 0:
            found.append((x, x))
        elif (
            i + 1 < points and values[i + 1] != 0 and (value > 0) != (values[i + 1] > 0)
        ):
            found.append((x, grid[i + 1]))
    return found


def _expand(
    counted: _Counted,
    lower: float,
    upper: float,
    limits: tuple[float, float],
    policy: RootPolicy,
) -> tuple[float, float]:
    """Widen the bracket until its ends differ in sign, within ``limits``."""
    low_limit, high_limit = limits
    a, b = lower, upper
    fa, fb = counted(a), counted(b)
    for _ in range(policy.max_expansions):
        if (fa > 0) != (fb > 0) or fa == 0 or fb == 0:
            break
        can_lower, can_raise = a > low_limit, b < high_limit
        if not (can_lower or can_raise):
            break
        width = b - a
        if can_lower and (abs(fa) < abs(fb) or not can_raise):
            a = max(a - policy.expansion_factor * width, low_limit)
            fa = counted(a)
        else:
            b = min(b + policy.expansion_factor * width, high_limit)
            fb = counted(b)
    return a, b


def find_root(
    function: Callable[[float], float],
    lower: float,
    upper: float,
    *,
    limits: tuple[float, float] | None = None,
    policy: RootPolicy = DEFAULT_ROOT_POLICY,
) -> RootResult:
    """Find a root of ``function`` in ``[lower, upper]``.

    Parameters
    ----------
    function
        A scalar function of one float.
    lower, upper
        The initial bracket.
    limits
        How far the bracket may expand, usually the bounds of the input
        being solved for. Without limits, the bracket never expands.
    policy
        Tolerances and limits; :data:`DEFAULT_ROOT_POLICY` by default.

    Returns
    -------
    RootResult
        The smallest root found, with the bracket and counts.

    Raises
    ------
    InputError
        If the bracket or limits are not finite and increasing, or the
        limits do not contain the bracket.
    ConvergenceError
        If no sign change is found, Brent's method does not converge, or the
        function is not finite at a point it is evaluated at.

    Warns
    -----
    ModelWarning
        ``several_roots``, when the scan finds more than one root.

    Examples
    --------
    >>> import warnings
    >>> with warnings.catch_warnings(record=True) as caught:
    ...     warnings.simplefilter("always")
    ...     result = find_root(lambda x: (x - 1) * (x - 2) * (x - 3), 0.5, 3.6)
    >>> round(result.root, 12), result.candidates, caught[0].message.code
    (1.0, 3, 'several_roots')

    """
    _check_bracket(lower, upper, "bracket")
    counted = _Counted(function)
    a, b = lower, upper
    found = bracket_roots(counted, a, b, points=policy.scan_points)
    if not found and limits is not None:
        _check_bracket(limits[0], limits[1], "limits")
        if not limits[0] <= lower < upper <= limits[1]:
            msg = f"the limits {limits!r} do not contain [{lower!r}, {upper!r}]"
            raise InputError(msg)
        a, b = _expand(counted, lower, upper, limits, policy)
        if (a, b) != (lower, upper):
            found = bracket_roots(counted, a, b, points=policy.scan_points)
    if not found:
        msg = f"no sign change in [{a!r}, {b!r}]: the function may have no root"
        raise ConvergenceError(msg)
    if len(found) > 1:
        warn(
            "several_roots",
            f"found {len(found)} roots in [{a!r}, {b!r}]; using the smallest",
            stacklevel=2,
        )
    left, right = found[0]
    if left == right:
        return RootResult(left, (a, b), len(found), 0, counted.calls)
    from scipy.optimize import brentq  # noqa: PLC0415 - SciPy loads on first use

    root, report = brentq(
        counted,
        left,
        right,
        xtol=policy.xtol,
        rtol=policy.rtol,
        maxiter=policy.maxiter,
        full_output=True,
        disp=False,
    )
    if not report.converged:
        msg = f"Brent's method did not converge in [{left!r}, {right!r}]: {report.flag}"
        raise ConvergenceError(msg)
    return RootResult(float(root), (a, b), len(found), report.iterations, counted.calls)
