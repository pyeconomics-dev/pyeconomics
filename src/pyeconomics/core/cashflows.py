# src/pyeconomics/core/cashflows.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Discounting cash flows: growth and annuity factors, present values and IRR.

Every function takes a rate per period as a decimal (ADR-0008 decision 1),
greater than -1, and a number of periods or a time in periods. Nothing here
raises on overflow: a factor or value too large for a float comes back as
infinity, and the model that called it decides what that means for its bounds
(ADR-0008 decision 10). That keeps NumPy's and ``math``'s overflow errors out of
models, whose tests turn warnings into errors.

- growth factor: :math:`(1 + r)^n`;
- annuity factor, in arrears: :math:`a = (1 - (1 + r)^{-n}) / r`, and :math:`n`
  at :math:`r = 0`;
- accumulated annuity factor: :math:`s = ((1 + r)^n - 1) / r`, and :math:`n` at
  :math:`r = 0`;
- growing annuity factor: :math:`(1 - q^n) / (r - g)` with
  :math:`q = (1 + g) / (1 + r)`, and :math:`n / (1 + r)` at :math:`r = g`;
- growing perpetuity factor: :math:`1 / (r - g)`, for :math:`r > g`;
- present value of cash flows: :math:`\sum_i C_i (1 + r)^{-t_i}`.

An annuity due (payments at the start of each period) is the arrears factor
times :math:`1 + r`.

Present values are summed in log space: each term is
:math:`\operatorname{sign}(C_i) e^{\ln|C_i| - t_i \ln(1+r) - m}` for the largest
log magnitude :math:`m`, so no term overflows. :func:`internal_rate_of_return`
finds a root of that scaled sum, which has the same sign and roots as the
present value itself, with :func:`~pyeconomics.core.numerics.find_root` (ADR-0008
decision 11): the smallest root in the bracket, with a ``several_roots`` warning
when the scan finds more than one.

Examples
--------
>>> from pyeconomics.core import annuity_factor, internal_rate_of_return
>>> round(annuity_factor(0.05, 10), 10)
7.7217349292
>>> round(internal_rate_of_return([-100.0, 60.0, 60.0]), 10)
0.1306623863

"""

from __future__ import annotations

import math
import sys
from typing import TYPE_CHECKING, Final

import numpy as np

from pyeconomics.core.context import warn
from pyeconomics.core.errors import ConvergenceError, DomainError, InputError
from pyeconomics.core.numerics import RootPolicy, find_root

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

__all__ = [
    "IRR_LOWER",
    "IRR_POLICY",
    "IRR_UPPER",
    "accumulated_annuity_factor",
    "accumulated_growing_annuity_factor",
    "annuity_factor",
    "growing_annuity_factor",
    "growing_perpetuity_factor",
    "growth_factor",
    "internal_rate_of_return",
    "present_value",
    "present_value_factor",
    "sign_changes",
]

#: The largest argument ``math.exp`` takes without overflowing.
_LOG_MAX: Final = math.log(sys.float_info.max)

#: The bracket :func:`internal_rate_of_return` searches by default: the
#: default bounds of a rate (ADR-0008 decision 3).
IRR_LOWER: Final = -0.99
IRR_UPPER: Final = 10.0

#: The root policy for an IRR: ADR-0008 decision 11's tolerances, with a scan
#: grid fine enough (a step of 0.01 over the default bracket) that two roots a
#: percentage point apart are both seen. The bracket never expands.
IRR_POLICY: Final = RootPolicy(scan_points=1100)


def _exp(x: float) -> float:
    """Return ``e**x``, or infinity where ``math.exp`` would raise."""
    return math.inf if x > _LOG_MAX else math.exp(x)


def _check(rate: float, periods: float) -> float:
    """Check a rate and a number of periods; return ``ln(1 + rate)``."""
    if not (math.isfinite(rate) and rate > -1):
        msg = f"the rate must be a finite decimal above -1, not {rate!r}"
        raise InputError(msg)
    if not (math.isfinite(periods) and periods >= 0):
        msg = f"the number of periods must be finite and not negative, not {periods!r}"
        raise InputError(msg)
    return math.log1p(rate)


def growth_factor(rate: float, periods: float) -> float:
    """Return :math:`(1 + r)^n`, or infinity when it overflows.

    Examples
    --------
    >>> growth_factor(0.1, 2)
    1.21
    >>> growth_factor(1.0, 2000)
    inf

    """
    return _exp(periods * _check(rate, periods))


def annuity_factor(rate: float, periods: float, *, due: bool = False) -> float:
    """Return the present value of one unit paid each period for ``periods``.

    Parameters
    ----------
    rate
        The rate per period, above -1.
    periods
        The number of payments, zero or more; it may be fractional.
    due
        Payments at the start of each period (an annuity due) rather than at
        the end (in arrears).

    Examples
    --------
    >>> annuity_factor(0.0, 12)
    12.0
    >>> round(annuity_factor(0.05, 10, due=True) / annuity_factor(0.05, 10), 12)
    1.05

    """
    log_growth = _check(rate, periods)
    if rate == 0:
        factor = float(periods)
    else:
        exponent = -periods * log_growth
        factor = math.inf if exponent > _LOG_MAX else -math.expm1(exponent) / rate
    return factor * (1 + rate) if due else factor


def accumulated_annuity_factor(
    rate: float, periods: float, *, due: bool = False
) -> float:
    """Return the value after ``periods`` of one unit paid each period.

    The arguments are those of :func:`annuity_factor`.

    Examples
    --------
    >>> round(accumulated_annuity_factor(0.05, 10), 10)
    12.5778925355

    """
    log_growth = _check(rate, periods)
    if rate == 0:
        factor = float(periods)
    else:
        exponent = periods * log_growth
        factor = math.inf if exponent > _LOG_MAX else math.expm1(exponent) / rate
    return factor * (1 + rate) if due else factor


def growing_annuity_factor(
    rate: float, growth: float, periods: float, *, due: bool = False
) -> float:
    r"""Return the present value of payments of 1, 1 + g, (1 + g)², ...

    The first payment is one unit, at the end of the first period (or at its
    start for an annuity due), and each later one grows by ``growth``.

    The ratio :math:`(1+g)/(1+r)` is formed as :math:`1 + d` with
    :math:`d = (g - r)/(1 + r)`, so a growth rate close to the rate loses no
    precision.

    Examples
    --------
    >>> round(growing_annuity_factor(0.05, 0.0, 10), 10) == round(
    ...     annuity_factor(0.05, 10), 10)
    True
    >>> growing_annuity_factor(0.05, 0.05, 10) == 10 / 1.05
    True

    """
    _check(growth, periods)
    _check(rate, periods)
    step = (growth - rate) / (1 + rate)
    if step == 0:
        factor = periods / (1 + rate)
    else:
        exponent = periods * math.log1p(step)
        factor = (
            math.inf
            if exponent > _LOG_MAX
            else math.expm1(exponent) / (step * (1 + rate))
        )
    return factor * (1 + rate) if due else factor


def growing_perpetuity_factor(
    rate: float, growth: float = 0.0, *, due: bool = False
) -> float:
    """Return the present value of a perpetuity of 1, 1 + g, (1 + g)², ...

    Raises
    ------
    DomainError
        If the rate is not above the growth rate: the sum diverges.

    Examples
    --------
    >>> round(growing_perpetuity_factor(0.05), 12)
    20.0
    >>> round(growing_perpetuity_factor(0.08, 0.03), 12)
    20.0

    """
    _check(rate, 0.0)
    _check(growth, 0.0)
    if rate <= growth:
        msg = (
            f"a perpetuity needs a rate above its growth rate; {rate!r} is not "
            f"above {growth!r}, so its value is infinite"
        )
        raise DomainError(msg)
    factor = 1 / (rate - growth)
    return factor * (1 + rate) if due else factor


def _arrays(
    cash_flows: Sequence[float], times: Sequence[float] | None
) -> tuple[NDArray[np.float64], ...]:
    flows = np.asarray(cash_flows, dtype=np.float64)
    if flows.ndim != 1 or not np.all(np.isfinite(flows)):
        msg = "the cash flows must be a one-dimensional array of finite numbers"
        raise InputError(msg)
    if times is None:
        when = np.arange(flows.size, dtype=np.float64)
    else:
        when = np.asarray(times, dtype=np.float64)
        if when.shape != flows.shape or not np.all(np.isfinite(when)):
            msg = "the times must be finite and as many as the cash flows"
            raise InputError(msg)
    return flows, when


def _scaled(
    log_growth: float,
    flows: NDArray[np.float64],
    times: NDArray[np.float64],
) -> tuple[float, float]:
    """Return the present value as ``(s, m)`` with value ``s * e**m``.

    ``s`` is at most the number of flows in magnitude, so it never overflows.
    """
    nonzero = flows != 0
    if not nonzero.any():
        return 0.0, 0.0
    logs = np.log(np.abs(flows[nonzero])) - times[nonzero] * log_growth
    peak = float(logs.max())
    scaled = float(np.sum(np.sign(flows[nonzero]) * np.exp(logs - peak)))
    return scaled, peak


def present_value(
    rate: float, cash_flows: Sequence[float], times: Sequence[float] | None = None
) -> float:
    r"""Return :math:`\sum_i C_i (1 + r)^{-t_i}`, or ±infinity on overflow.

    Parameters
    ----------
    rate
        The rate per period, above -1.
    cash_flows
        The cash flows, positive for money received.
    times
        When each flow occurs, in periods from now; by default 0, 1, 2, ...,
        so the first flow is not discounted. Times may be fractional or
        negative.

    Examples
    --------
    >>> abs(present_value(0.1, [-100.0, 110.0])) < 1e-12
    True
    >>> present_value(0.0, [1.0, 2.0, 3.0])
    6.0

    """
    _check(rate, 0.0)
    flows, when = _arrays(cash_flows, times)
    log_growth = math.log1p(rate)
    exponents = -when * log_growth
    largest = float(np.max(np.abs(flows))) if flows.size else 0.0
    if largest == 0:
        return 0.0
    steepest = float(np.max(exponents))
    if (
        steepest < _LOG_MAX - 1
        and steepest + math.log(largest * flows.size) < _LOG_MAX - 1
    ):
        # No factor, term or partial sum overflows: sum the terms directly.
        return math.fsum((flows * np.power(1 + rate, -when)).tolist())
    scaled, peak = _scaled(log_growth, flows, when)
    if scaled == 0:
        return 0.0
    magnitude = peak + math.log(abs(scaled))
    return math.copysign(_exp(magnitude), scaled)


def sign_changes(cash_flows: Sequence[float]) -> int:
    """Return how many times the cash flows change sign, ignoring zeros.

    By Descartes' rule of signs, it bounds the number of IRRs.

    Examples
    --------
    >>> sign_changes([-100.0, 0.0, 50.0, -10.0, 70.0])
    3

    """
    flows, _ = _arrays(cash_flows, None)
    signs = np.sign(flows[flows != 0])
    return int(np.count_nonzero(signs[1:] != signs[:-1]))


def internal_rate_of_return(
    cash_flows: Sequence[float],
    times: Sequence[float] | None = None,
    *,
    lower: float = IRR_LOWER,
    upper: float = IRR_UPPER,
) -> float | None:
    """Return the rate at which the cash flows' present value is zero.

    The root is found in ``[lower, upper]`` under :data:`IRR_POLICY`. With
    several, the smallest is returned and ``several_roots`` is warned
    (ADR-0008 decision 11).

    Parameters
    ----------
    cash_flows, times
        As for :func:`present_value`; times may be year fractions, for an
        annual IRR of dated flows (XIRR).
    lower, upper
        The bracket to search, above -1.

    Returns
    -------
    float or None
        The IRR, or ``None`` when it is undefined: with a ``no_sign_change``
        warning when the flows never change sign (no rate can make their sum
        zero), and with ``no_root_in_range`` when no root lies in the bracket.

    Examples
    --------
    >>> import warnings
    >>> with warnings.catch_warnings(record=True) as caught:
    ...     warnings.simplefilter("always")
    ...     internal_rate_of_return([100.0, 50.0])
    >>> caught[0].message.code
    'no_sign_change'

    """
    flows, when = _arrays(cash_flows, times)
    _check(lower, 0.0)
    if sign_changes(flows.tolist()) == 0:
        warn(
            "no_sign_change",
            "the cash flows never change sign, so no rate makes their present "
            "value zero",
            stacklevel=2,
        )
        return None

    def scaled_value(rate: float) -> float:
        value, peak = _scaled(math.log1p(rate), flows, when)
        if rate in (lower, upper) and value != 0:
            # Log scaling can round a mathematical endpoint root away from
            # zero. Accept only a residual whose Newton displacement fits
            # the existing tolerance in RATE units, never an arbitrary NPV
            # epsilon (which could invent roots for tiny cash flows).
            nonzero = flows != 0
            logs = np.log(np.abs(flows[nonzero])) - when[nonzero] * math.log1p(rate)
            terms = np.sign(flows[nonzero]) * np.exp(logs - peak)
            slope = math.fsum((-when[nonzero] * terms / (1 + rate)).tolist())
            tolerance = IRR_POLICY.xtol + IRR_POLICY.rtol * abs(rate)
            if slope != 0 and abs(value / slope) <= tolerance:
                return 0.0
        return value

    try:
        found = find_root(scaled_value, lower, upper, policy=IRR_POLICY)
    except ConvergenceError:
        warn(
            "no_root_in_range",
            f"the present value does not cross zero for rates in [{lower}, {upper}]",
            stacklevel=2,
        )
        return None
    return found.root


def accumulated_growing_annuity_factor(
    rate: float, growth: float, periods: float, *, due: bool = False
) -> float:
    r"""Return the value after ``periods`` of payments 1, 1 + g, (1 + g)², ...

    The sum :math:`\sum_{t=1}^{n} (1+g)^{t-1} (1+r)^{n-t}` is symmetric in the
    two rates, so it is formed from whichever is larger, as that one's growth
    factor times a bounded :func:`growing_annuity_factor`; no product of an
    infinity and a zero can arise.

    Examples
    --------
    >>> round(accumulated_growing_annuity_factor(0.05, 0.0, 10), 10)
    12.5778925355

    """
    _check(rate, periods)
    _check(growth, periods)
    high, low = (rate, growth) if rate >= growth else (growth, rate)
    factor = growth_factor(high, periods) * growing_annuity_factor(high, low, periods)
    return factor * (1 + rate) if due else factor


def present_value_factor(rate: float, periods: float) -> float:
    """Return :math:`(1 + r)^{-n}`, or infinity when it overflows.

    Examples
    --------
    >>> round(present_value_factor(0.1, 2), 12)
    0.826446280992

    """
    return _exp(-periods * _check(rate, periods))
