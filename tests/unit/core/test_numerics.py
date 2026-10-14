# tests/unit/core/test_numerics.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The bracketed root finder: a known root, no root, several roots."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pytest

from pyeconomics.core import (
    DEFAULT_ROOT_POLICY,
    ConvergenceError,
    InputError,
    ModelWarning,
    RootPolicy,
    bracket_roots,
    find_root,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def test_a_known_root() -> None:
    result = find_root(lambda x: x * x - 2.0, 0.0, 2.0)
    assert math.isclose(result.root, math.sqrt(2.0), rel_tol=1e-12)
    assert result.candidates == 1
    assert result.bracket == (0.0, 2.0)
    assert 0 < result.iterations <= DEFAULT_ROOT_POLICY.maxiter
    assert result.function_calls >= DEFAULT_ROOT_POLICY.scan_points


def test_the_root_meets_the_policy_tolerance() -> None:
    # Dottie's number: the fixed point of cos, 0.7390851332151606416553...
    result = find_root(lambda x: math.cos(x) - x, 0.0, 1.0)
    policy = DEFAULT_ROOT_POLICY
    assert math.isclose(
        result.root,
        0.7390851332151606416553,
        abs_tol=policy.xtol,
        rel_tol=policy.rtol,
    )


def test_no_root_raises_convergence_error() -> None:
    with pytest.raises(ConvergenceError, match="no sign change"):
        find_root(lambda x: x * x + 1.0, -1.0, 1.0)


def test_no_root_within_the_limits_raises_after_expanding() -> None:
    with pytest.raises(ConvergenceError, match=r"no sign change in \[-10.0, 10.0\]"):
        find_root(lambda x: x * x + 1.0, -1.0, 1.0, limits=(-10.0, 10.0))


def test_several_roots_yield_the_smallest_and_a_warning() -> None:
    with pytest.warns(ModelWarning, match="several_roots") as caught:
        result = find_root(lambda x: (x - 1.0) * (x - 2.0) * (x - 3.0), 0.5, 3.6)
    assert math.isclose(result.root, 1.0, abs_tol=1e-11)
    assert result.candidates == 3
    assert isinstance(caught[0].message, ModelWarning)
    assert caught[0].message.code == "several_roots"


def test_the_bracket_expands_within_the_limits() -> None:
    result = find_root(lambda x: x - 5.0, 0.0, 1.0, limits=(-100.0, 100.0))
    assert math.isclose(result.root, 5.0, rel_tol=1e-12)
    low, high = result.bracket
    assert -100.0 <= low <= 0.0
    assert 5.0 < high <= 100.0


def test_expansion_moves_the_end_whose_value_is_nearer_zero() -> None:
    # |f(0)| = 5 < |f(1)| = 6, so only the lower end moves: 0 - 1.6 * 1 = -1.6
    # (f = 3.4), then -1.6 - 1.6 * 2.6 = -5.76 (f = -0.76), a sign change.
    result = find_root(lambda x: x + 5.0, 0.0, 1.0, limits=(-100.0, 100.0))
    assert result.bracket[0] == pytest.approx(-5.76, rel=1e-12)
    assert result.bracket[1] == 1.0
    assert math.isclose(result.root, -5.0, rel_tol=1e-12)


def test_expansion_stops_at_the_limits() -> None:
    result = find_root(lambda x: x + 3.0, 0.0, 1.0, limits=(-3.0, 1.0))
    assert result.root == -3.0
    assert result.bracket[0] == -3.0


def test_expansion_gives_up_after_its_budget() -> None:
    policy = RootPolicy(max_expansions=1)
    with pytest.raises(ConvergenceError, match="no sign change"):
        find_root(lambda x: x - 50.0, 0.0, 1.0, limits=(-1e3, 1e3), policy=policy)


def test_limits_equal_to_the_bracket_leave_nothing_to_expand() -> None:
    with pytest.raises(ConvergenceError, match=r"no sign change in \[0.0, 1.0\]"):
        find_root(lambda x: x - 5.0, 0.0, 1.0, limits=(0.0, 1.0))


def test_without_limits_the_bracket_never_expands() -> None:
    with pytest.raises(ConvergenceError, match=r"no sign change in \[0.0, 1.0\]"):
        find_root(lambda x: x - 5.0, 0.0, 1.0)


def test_an_exact_zero_on_the_scan_grid_is_returned_as_is() -> None:
    result = find_root(lambda x: x - 1.0, 0.0, 2.0, policy=RootPolicy(scan_points=3))
    assert result.root == 1.0
    assert result.iterations == 0


def test_a_function_that_is_not_finite_raises() -> None:
    with pytest.raises(ConvergenceError, match="not finite"):
        find_root(lambda x: math.nan if x > 0.5 else x, -1.0, 1.0)


def test_brent_failing_to_converge_raises() -> None:
    policy = RootPolicy(maxiter=1)
    with pytest.raises(ConvergenceError, match="did not converge"):
        find_root(lambda x: math.exp(x) - 1.5, -10.0, 10.0, policy=policy)


@pytest.mark.parametrize(
    ("lower", "upper", "limits", "message"),
    [
        (1.0, 0.0, None, "not below"),
        (math.nan, 1.0, None, "finite"),
        (0.0, 1.0, (math.inf, 2.0), "finite"),
        (0.0, 1.0, (0.5, 2.0), "do not contain"),
    ],
)
def test_bad_brackets_and_limits_are_refused(
    lower: float, upper: float, limits: tuple[float, float] | None, message: str
) -> None:
    with pytest.raises(InputError, match=message):
        find_root(lambda x: x + 10.0, lower, upper, limits=limits)


@pytest.mark.parametrize(
    ("make", "message"),
    [
        (lambda: RootPolicy(xtol=0.0), "xtol"),
        (lambda: RootPolicy(rtol=1e-17), "rtol"),
        (lambda: RootPolicy(maxiter=0), "maxiter"),
        (lambda: RootPolicy(expansion_factor=1.0), "expansion_factor"),
        (lambda: RootPolicy(max_expansions=-1), "max_expansions"),
        (lambda: RootPolicy(scan_points=1), "scan_points"),
    ],
)
def test_policy_limits_are_checked(
    make: Callable[[], RootPolicy], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        make()


def test_the_default_policy_is_scipys() -> None:
    assert DEFAULT_ROOT_POLICY.xtol == 2e-12
    assert DEFAULT_ROOT_POLICY.rtol == 4 * 2.220446049250313e-16
    assert DEFAULT_ROOT_POLICY.maxiter == 100
    assert DEFAULT_ROOT_POLICY.expansion_factor == 1.6
    assert DEFAULT_ROOT_POLICY.max_expansions == 50


def test_bracket_roots_lists_every_sign_change() -> None:
    found = bracket_roots(math.sin, 0.5, 10.0, points=100)
    assert len(found) == 3  # pi, 2 pi, 3 pi
    for (low, high), k in zip(found, (1, 2, 3), strict=True):
        assert low < k * math.pi < high


def test_bracket_roots_needs_two_points() -> None:
    with pytest.raises(InputError, match="at least 2 points"):
        bracket_roots(lambda x: x, -1.0, 1.0, points=1)


@pytest.mark.parametrize("root", [-1.0, 0.0, 1.0])
def test_exact_zeros_at_both_ends_and_inside_are_roots(root: float) -> None:
    # A touching root proves exact-zero detection independently of sign changes.
    function = lambda x: (x - root) ** 2  # noqa: E731
    assert bracket_roots(function, -1.0, 1.0, points=3) == [(root, root)]
    found = find_root(function, -1.0, 1.0, policy=RootPolicy(scan_points=3))
    assert found.root == root
    assert found.iterations == 0


def test_endpoint_and_interior_roots_keep_smallest_root_policy() -> None:
    function = lambda x: (x + 1) * x * (x - 1)  # noqa: E731
    assert bracket_roots(function, -1.0, 1.0, points=3) == [
        (-1.0, -1.0),
        (0.0, 0.0),
        (1.0, 1.0),
    ]
    with pytest.warns(ModelWarning, match="several_roots"):
        result = find_root(function, -1.0, 1.0, policy=RootPolicy(scan_points=3))
    assert result.root == -1.0
    assert result.candidates == 3
