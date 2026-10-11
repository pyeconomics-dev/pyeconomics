# src/pyeconomics/core/descriptive.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Descriptive statistics of a series: moments, semideviation and drawdown.

The estimators are named, because each has rivals:

- mean: :math:`\bar{x} = \frac{1}{n}\sum x_i`;
- sample variance: :math:`s^2 = \frac{1}{n - 1}\sum (x_i - \bar{x})^2`
  (``ddof=1``);
- semideviation below the mean:
  :math:`\sqrt{\frac{1}{n - 1}\sum \min(x_i - \bar{x}, 0)^2}`;
- semideviation below a target *T*: :math:`\sqrt{\frac{1}{n}\sum \min(x_i - T,
  0)^2}`;
- skewness, G1: :math:`\frac{\sqrt{n(n-1)}}{n-2}\,\frac{m_3}{m_2^{3/2}}`;
- excess kurtosis, G2:
  :math:`\frac{n-1}{(n-2)(n-3)}\left[(n+1)\frac{m_4}{m_2^2} - 3(n-1)\right]`;
- maximum drawdown: :math:`\max_{j}\left(1 - x_j / \max_{i \le j} x_i\right)`;
- compound return of a series: :math:`\prod (1 + r_t) - 1`;
- annualized return: :math:`(1 + R)^{m / k} - 1` for a return :math:`R` over
  :math:`k` periods and :math:`m` periods in a year;

with :math:`m_k = \frac{1}{n}\sum (x_i - \bar{x})^k`. G1 and G2 are the
adjusted estimators Joanes and Gill (1998) compare, the ones SAS, SPSS and
Excel report, and SciPy's ``skew`` and ``kurtosis`` with ``bias=False``.

Means and sums of squares use a corrected two-pass method (Chan, Golub and
LeVeque, 1983), so a series with a large offset and a small spread, such as
NIST's NumAcc1, keeps its digits.

Returns compound in log space. As in :mod:`pyeconomics.core.cashflows`, a
compound or annualized return too large for a float comes back as infinity, and
the model that asked decides what that means for its bounds.

Examples
--------
>>> from pyeconomics.core import sample_variance
>>> sample_variance([10000001.0, 10000003.0, 10000002.0])
1.0

"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np
from numpy.typing import NDArray

from pyeconomics.core.errors import DomainError, InputError

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "Drawdown",
    "Moments",
    "annualized_log_return",
    "annualized_return",
    "compound_return",
    "has_spread",
    "log_return",
    "max_drawdown",
    "sample_mean",
    "sample_moments",
    "sample_variance",
    "semideviation_below_mean",
    "semideviation_below_target",
]

#: A spread this many machine epsilons of the data's magnitude, or less, counts
#: as no spread at all: the deviations are rounding error.
_ZERO_SPREAD_ULPS: Final = 64

_KURTOSIS_MIN: Final = 4

#: The largest argument ``math.exp`` takes without overflowing.
_LOG_MAX: Final = math.log(np.finfo(np.float64).max)

type _Vector = NDArray[np.float64]


def _series(values: Sequence[float], minimum: int) -> _Vector:
    data = np.asarray(values, dtype=np.float64)
    if data.ndim != 1 or not np.all(np.isfinite(data)):
        msg = "a series must be a one-dimensional array of finite numbers"
        raise InputError(msg)
    if data.size < minimum:
        msg = f"the series needs at least {minimum} values, not {data.size}"
        raise InputError(msg)
    return data


def _centred(data: _Vector) -> tuple[float, _Vector]:
    """Return the mean and the deviations from it, after one correction pass."""
    mean = float(np.mean(data))
    deviations = data - mean
    correction = float(np.mean(deviations))
    return mean + correction, deviations - correction


def _no_spread(data: _Vector, deviations: _Vector) -> bool:
    scale = float(np.max(np.abs(data)))
    limit = _ZERO_SPREAD_ULPS * float(np.finfo(np.float64).eps) * scale
    return bool(np.max(np.abs(deviations)) <= limit)


def has_spread(values: Sequence[float]) -> bool:
    """Return whether the values differ by more than rounding error.

    A spread of 64 machine epsilons of the largest magnitude, or less, counts
    as none: a ratio divided by such a standard deviation is noise.

    Examples
    --------
    >>> has_spread([0.1, 0.1, 0.1]), has_spread([0.1, 0.2])
    (False, True)

    """
    data = _series(values, 1)
    _, deviations = _centred(data)
    return not _no_spread(data, deviations)


def compound_return(returns: Sequence[float]) -> float:
    """Return the compound return of a series, or infinity when it overflows.

    A return of -1 (a total loss) anywhere makes the result -1.

    Raises
    ------
    InputError
        If a return is below -1 or not finite, or there is none.

    Examples
    --------
    >>> round(compound_return([0.1, -0.05, 0.2]), 12)
    0.254

    """
    return _expm1(log_return(returns))


def log_return(returns: Sequence[float]) -> float:
    r"""Return the log of the compound gross return, :math:`\sum \ln(1 + r_t)`.

    A return of -1 (a total loss) anywhere makes it minus infinity. Unlike the
    compound return itself, the sum neither overflows nor rounds a long run of
    losses to exactly -1, so annualize from it
    (:func:`annualized_log_return`).

    Raises
    ------
    InputError
        If a return is below -1 or not finite, or there is none.

    Examples
    --------
    >>> round(log_return([0.1, -0.05, 0.2]), 12)
    0.226338442211

    """
    data = _series(returns, 1)
    if np.any(data < -1):
        msg = "a return below -1 (a loss of more than everything) does not compound"
        raise InputError(msg)
    if np.any(data == -1):
        return -math.inf
    return math.fsum(np.log1p(data).tolist())


def annualized_log_return(
    log_total: float, periods: float, periods_per_year: float
) -> float:
    r"""Return :math:`e^{\ell m / k} - 1` for a log return :math:`\ell` over k periods.

    Minus infinity (a total loss) gives -1, and an overflow infinity.

    Raises
    ------
    InputError
        If the log return is NaN or plus infinity, or a count of periods is
        not positive.

    Examples
    --------
    >>> round(annualized_log_return(log_return([-0.5] * 100), 100, 1), 12)
    -0.5

    """
    if math.isnan(log_total) or log_total == math.inf:
        msg = f"a log return must be finite or minus infinity, not {log_total!r}"
        raise InputError(msg)
    for name, value in (("periods", periods), ("periods_per_year", periods_per_year)):
        if not (math.isfinite(value) and value > 0):
            msg = f"{name} must be finite and above zero, not {value!r}"
            raise InputError(msg)
    if log_total in {0.0, -math.inf}:
        # Fixed points of compounding; an exponent that overflows to inf
        # would otherwise turn 0 into NaN.
        return _expm1(log_total)
    return _expm1(periods_per_year / periods * log_total)


def annualized_return(
    total_return: float, periods: float, periods_per_year: float
) -> float:
    """Return a return over ``periods`` compounded to a year of ``periods_per_year``.

    The result is :math:`(1 + R)^{m / k} - 1`, or infinity when it overflows.
    Zero and -1 are fixed points. A return compounded over many periods may
    already have rounded to -1 or overflowed: annualize those from their
    :func:`log_return` instead.

    Raises
    ------
    InputError
        If the return is below -1 or not finite, or a count of periods is not
        positive.

    Examples
    --------
    >>> round(annualized_return(0.01, 1, 12), 12)
    0.126825030132
    >>> annualized_return(-1.0, 3, 12)
    -1.0

    """
    if not (math.isfinite(total_return) and total_return >= -1):
        msg = f"the return must be finite and at least -1, not {total_return!r}"
        raise InputError(msg)
    log_total = -math.inf if total_return == -1 else math.log1p(total_return)
    return annualized_log_return(log_total, periods, periods_per_year)


def _expm1(log_total: float) -> float:
    """Return ``e**x - 1`` at least -1, or infinity where it overflows."""
    if log_total > _LOG_MAX:
        return math.inf
    if log_total == -math.inf:
        return -1.0
    return max(math.expm1(log_total), -1.0)


def sample_mean(values: Sequence[float]) -> float:
    """Return the arithmetic mean, with one correction pass.

    Examples
    --------
    >>> sample_mean([10000001.0, 10000003.0, 10000002.0])
    10000002.0

    """
    return _centred(_series(values, 1))[0]


def sample_variance(values: Sequence[float], *, ddof: int = 1) -> float:
    """Return the variance with ``n - ddof`` in the denominator.

    The default ``ddof=1`` is the unbiased sample variance.

    Raises
    ------
    InputError
        If the series has no more than ``ddof`` values.

    """
    data = _series(values, ddof + 1)
    _, deviations = _centred(data)
    return float(np.sum(deviations * deviations)) / (data.size - ddof)


def semideviation_below_mean(values: Sequence[float]) -> float:
    """Return the semideviation below the sample mean, with ``n - 1``.

    Every observation counts in the denominator; only those below the mean
    contribute to the sum.

    Examples
    --------
    >>> semideviation_below_mean([1.0, 2.0, 3.0])
    0.7071067811865476

    """
    data = _series(values, 2)
    _, deviations = _centred(data)
    below = np.minimum(deviations, 0.0)
    return math.sqrt(float(np.sum(below * below)) / (data.size - 1))


def semideviation_below_target(values: Sequence[float], target: float) -> float:
    """Return the downside deviation below ``target``, with ``n``.

    The target is given, not estimated, so the denominator is ``n``.

    Examples
    --------
    >>> semideviation_below_target([-0.02, 0.01, 0.03, -0.04], 0.0)
    0.022360679774997897

    """
    data = _series(values, 1)
    if not math.isfinite(target):
        msg = f"the target must be finite, not {target!r}"
        raise InputError(msg)
    below = np.minimum(data - target, 0.0)
    return math.sqrt(float(np.sum(below * below)) / data.size)


@dataclass(frozen=True, slots=True)
class Moments:
    """The shape of a sample: adjusted skewness (G1) and excess kurtosis (G2)."""

    skewness: float
    excess_kurtosis: float


def sample_moments(values: Sequence[float]) -> Moments:
    """Return the G1 skewness and G2 excess kurtosis of at least four values.

    Raises
    ------
    InputError
        If there are fewer than four values.
    DomainError
        If the values have no spread: both statistics divide by the variance.

    Examples
    --------
    >>> shape = sample_moments([1.0, 2.0, 3.0, 4.0])
    >>> shape.skewness, round(shape.excess_kurtosis, 12)
    (0.0, -1.2)

    """
    data = _series(values, _KURTOSIS_MIN)
    _, deviations = _centred(data)
    if _no_spread(data, deviations):
        msg = "the values have no spread, so skewness and kurtosis are undefined"
        raise DomainError(msg)
    n = data.size
    # G1 and G2 do not change with scale: dividing by the largest deviation
    # keeps m2 away from underflow for data with a tiny absolute spread.
    deviations = deviations / float(np.max(np.abs(deviations)))
    squares = deviations * deviations
    m2 = float(np.mean(squares))
    m3 = float(np.mean(squares * deviations))
    m4 = float(np.mean(squares * squares))
    g1 = m3 / m2**1.5
    skewness = g1 * math.sqrt(n * (n - 1)) / (n - 2)
    kurtosis = (n - 1) / ((n - 2) * (n - 3)) * ((n + 1) * m4 / (m2 * m2) - 3 * (n - 1))
    return Moments(skewness=skewness, excess_kurtosis=kurtosis)


@dataclass(frozen=True, slots=True)
class Drawdown:
    """The largest peak-to-trough decline of a value series."""

    depth: float
    """The decline as a fraction of the peak, from 0 to 1."""
    peak: int
    """The position of the peak, counting from 0."""
    trough: int
    """The position of the trough, counting from 0."""


def max_drawdown(values: Sequence[float]) -> Drawdown:
    """Return the maximum drawdown of positive values, with its positions.

    The peak is the running maximum before the trough (the first, if the
    maximum repeats). With no decline the depth is 0 and both positions are 0.

    Raises
    ------
    InputError
        If a value is not positive and finite, or there is none.

    Examples
    --------
    >>> max_drawdown([100.0, 120.0, 90.0, 130.0, 117.0])
    Drawdown(depth=0.25, peak=1, trough=2)

    """
    data = _series(values, 1)
    if not np.all(data > 0):
        msg = "a drawdown needs positive values"
        raise InputError(msg)
    peaks = np.maximum.accumulate(data)
    depths = 1.0 - data / peaks
    trough = int(np.argmax(depths))
    depth = float(depths[trough])
    if depth <= 0:
        return Drawdown(depth=0.0, peak=0, trough=0)
    peak = int(np.argmax(data[: trough + 1] == peaks[trough]))
    return Drawdown(depth=depth, peak=peak, trough=trough)
