# tests/models/econometrics/test_ols.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``econometrics.ols``: invariants, NumPy oracles and the econometrics extra.

Every covariance estimator and diagnostic is recomputed here from its published
formula with NumPy (and SciPy's distributions for p-values), independently of
statsmodels: classical, HC0 to HC3 (MacKinnon and White, 1985), HAC with
Bartlett weights (Newey and West, 1987), the Wald F, Durbin-Watson, Koenker's
Breusch-Pagan, Jarque-Bera, D'Agostino and Pearson's omnibus K-squared, Ramsey's
RESET and the VIF.

statsmodels resets its own warning filters to "always" when imported, so
pytest's warnings-as-errors cannot see a statsmodels warning raised inside the
model; :func:`stray_warnings` records them instead.
"""

from __future__ import annotations

import contextlib
import math
import subprocess  # nosec B404: runs this interpreter with fixed arguments
import sys
import warnings
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
import pytest
import scipy.stats
import statsmodels.api  # noqa: F401 - paid here, not in a test's first example
import strategies
from hypothesis import given, reject, settings
from hypothesis import strategies as st

from pyeconomics import registry
from pyeconomics.core import (
    DomainError,
    InputError,
    MissingOptionalDependencyError,
    ModelWarning,
    run_model,
)
from pyeconomics.core import registry as core_registry
from pyeconomics.models.econometrics import ols

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

COVARIANCES = ["nonrobust", "hc0", "hc1", "hc2", "hc3", "hac"]


def result(**inputs: Any) -> Any:  # noqa: ANN401 - a Result
    return run_model(ols, inputs)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the outputs
    return result(**inputs).outputs


@st.composite
def regressions(draw: st.DrawFn, *, rows: int = 40) -> dict[str, Any]:
    """Draw a modest, well-conditioned regression."""
    width = draw(st.integers(1, 3))
    constant = draw(st.booleans())
    n = draw(st.integers(width + int(constant) + 4, rows))
    design = draw(
        st.lists(
            st.lists(st.floats(-10.0, 10.0), min_size=width, max_size=width),
            min_size=n,
            max_size=n,
        )
    )
    x = np.column_stack([np.ones(n), design]) if constant else np.asarray(design)
    scales = np.max(np.abs(x), axis=0)
    if np.any(scales < 1e-3) or np.linalg.cond(x / scales) > 1e4:
        reject()
    response = draw(st.lists(st.floats(-100.0, 100.0), min_size=n, max_size=n))
    y = np.asarray(response)
    b, *_ = np.linalg.lstsq(x, y, rcond=None)
    if np.max(np.abs(y - x @ b)) <= 1e-6 * max(1.0, float(np.max(np.abs(y)))):
        reject()  # a perfect fit has no t statistics: test_a_perfect_fit_has_no_tests
    return {"response": response, "design": design, "add_constant": constant}


def matrix(inputs: dict[str, Any]) -> NDArray[np.float64]:
    design = np.asarray(inputs["design"], dtype=np.float64)
    if inputs.get("add_constant", True):
        design = np.column_stack([np.ones(len(design)), design])
    return np.asarray(design, dtype=np.float64)


def fit(inputs: dict[str, Any]) -> tuple[Any, ...]:
    """Least squares with NumPy: X, y, b, e, (X'X)^-1, n, k."""
    x = matrix(inputs)
    y = np.asarray(inputs["response"], dtype=np.float64)
    b, *_ = np.linalg.lstsq(x, y, rcond=None)
    e = y - x @ b
    return x, y, b, e, np.linalg.inv(x.T @ x), len(y), x.shape[1]


def covariance(inputs: dict[str, Any], kind: str, lags: int = 0) -> NDArray[Any]:
    """The coefficient covariance by its formula."""
    x, _, _, e, bread, n, k = fit(inputs)
    if kind == "nonrobust":
        return np.asarray(float(e @ e) / (n - k) * bread, dtype=np.float64)
    leverage = np.einsum("ij,jk,ik->i", x, bread, x)
    if kind == "hac":
        u = x * e[:, None]
        meat = u.T @ u
        for lag in range(1, lags + 1):
            weight = 1 - lag / (lags + 1)
            cross = u[lag:].T @ u[:-lag]
            meat += weight * (cross + cross.T)
        return np.asarray(bread @ meat @ bread, dtype=np.float64)
    scale = {
        "hc0": e**2,
        "hc1": e**2 * n / (n - k),
        "hc2": e**2 / (1 - leverage),
        "hc3": e**2 / (1 - leverage) ** 2,
    }[kind]
    return np.asarray(bread @ (x.T * scale) @ x @ bread, dtype=np.float64)


def close(found: Any, expected: Any, rel: float = 1e-7, absolute: float = 1e-9) -> bool:  # noqa: ANN401
    return bool(np.allclose(found, expected, rtol=rel, atol=absolute))


def stray_warnings(inputs: dict[str, Any]) -> list[str]:
    """Run the model; return every warning that is not a model warning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with contextlib.suppress(DomainError):
            run(**inputs)
    return [
        f"{type(w.message).__name__}: {w.message}"
        for w in caught
        if not isinstance(w.message, ModelWarning)
    ]


# --- invariants -------------------------------------------------------------------


@pytest.mark.invariant("econometrics.ols", "residuals_orthogonal_to_regressors")
@given(inputs=regressions())
def test_residuals_are_orthogonal_to_every_regressor(inputs: dict[str, Any]) -> None:
    out = run(**inputs)
    x = matrix(inputs)
    scale = np.abs(x).T @ np.abs(np.asarray(inputs["response"])) + 1.0
    assert np.all(np.abs(x.T @ np.asarray(out.residuals)) <= 1e-10 * scale)


@pytest.mark.invariant("econometrics.ols", "r_squared_in_unit_interval")
@given(inputs=regressions())
def test_r_squared_lies_in_the_unit_interval(inputs: dict[str, Any]) -> None:
    out = run(**inputs)
    assert out.r_squared is not None
    assert 0.0 <= out.r_squared <= 1.0


@pytest.mark.invariant("econometrics.ols", "coefficients_invariant_to_row_order")
@given(inputs=regressions(), data=st.data())
def test_reordering_rows_keeps_the_coefficients(
    inputs: dict[str, Any], data: st.DataObject
) -> None:
    order = data.draw(st.permutations(range(len(inputs["response"]))))
    shuffled = {
        **inputs,
        "response": [inputs["response"][i] for i in order],
        "design": [inputs["design"][i] for i in order],
    }
    assert close(run(**shuffled).coefficients, run(**inputs).coefficients, 1e-9, 1e-9)


# --- oracles -----------------------------------------------------------------------


@pytest.mark.oracle("econometrics.ols")
@given(
    inputs=regressions(),
    kind=st.sampled_from(COVARIANCES),
    lags=st.integers(0, 4),
    alpha=st.floats(0.01, 0.2),
)
def test_coefficients_and_covariances_match_numpy(
    inputs: dict[str, Any], kind: str, lags: int, alpha: float
) -> None:
    out = run(**inputs, covariance=kind, hac_lags=lags, alpha=alpha)
    x, _, b, _, _, n, k = fit(inputs)
    if (
        kind in {"hc2", "hc3"}
        and np.max(np.einsum("ij,jk,ik->i", x, np.linalg.inv(x.T @ x), x)) > 1 - 1e-6
    ):
        reject()
    cov = covariance(inputs, kind, lags)
    errors = np.sqrt(np.diag(cov))
    assert close(out.coefficients, b, 1e-8, 1e-9)
    assert close(out.standard_errors, errors, 1e-6, 1e-9)
    margin = scipy.stats.t.ppf(1 - alpha / 2, n - k) * errors
    assert close(out.conf_lower, b - margin, 1e-6, 1e-8)
    assert close(out.t_statistics, b / errors, 1e-6, 1e-8)
    p = 2 * scipy.stats.t.sf(np.abs(b / errors), n - k)
    assert close(out.p_values, p, 1e-5, 1e-9)
    slopes = np.eye(k)[1:] if inputs["add_constant"] else np.eye(k)
    rb = slopes @ b
    wald = float(rb @ np.linalg.solve(slopes @ cov @ slopes.T, rb)) / len(slopes)
    assert math.isclose(out.f_statistic, wald, rel_tol=1e-6, abs_tol=1e-9)
    assert out.hac_lags == (lags if kind == "hac" else 0)


@pytest.mark.oracle("econometrics.ols")
@given(inputs=regressions())
def test_fit_statistics_match_numpy(inputs: dict[str, Any]) -> None:
    out = run(**inputs)
    _, y, _, e, _, n, k = fit(inputs)
    constant = inputs["add_constant"]
    total = float(np.sum((y - y.mean()) ** 2)) if constant else float(y @ y)
    r2 = 1 - float(e @ e) / total
    assert math.isclose(out.r_squared, r2, rel_tol=1e-8, abs_tol=1e-10)
    adjusted = 1 - (n - int(constant)) / (n - k) * (1 - r2)
    assert math.isclose(out.adjusted_r_squared, adjusted, rel_tol=1e-8, abs_tol=1e-9)
    assert math.isclose(
        out.residual_std_error, math.sqrt(float(e @ e) / (n - k)), rel_tol=1e-9
    )
    assert out.degrees_of_freedom == n - k


def omnibus(e: NDArray[np.float64]) -> float:
    """D'Agostino-Pearson K-squared from the skewness and kurtosis tests."""
    n = len(e)
    d = e - e.mean()
    m2, m3, m4 = (np.mean(d**p) for p in (2, 3, 4))
    skew, kurt = m3 / m2**1.5, m4 / m2**2
    y = skew * math.sqrt((n + 1) * (n + 3) / (6 * (n - 2)))
    beta2 = (
        3
        * (n**2 + 27 * n - 70)
        * (n + 1)
        * (n + 3)
        / ((n - 2) * (n + 5) * (n + 7) * (n + 9))
    )
    w2 = -1 + math.sqrt(2 * (beta2 - 1))
    delta, a = 1 / math.sqrt(0.5 * math.log(w2)), math.sqrt(2 / (w2 - 1))
    z_skew = delta * math.log(y / a + math.sqrt((y / a) ** 2 + 1))
    mean = 3 * (n - 1) / (n + 1)
    var = 24 * n * (n - 2) * (n - 3) / ((n + 1) ** 2 * (n + 3) * (n + 5))
    xk = (kurt - mean) / math.sqrt(var)
    beta1 = (
        6
        * (n * n - 5 * n + 2)
        / ((n + 7) * (n + 9))
        * math.sqrt(6 * (n + 3) * (n + 5) / (n * (n - 2) * (n - 3)))
    )
    big_a = 6 + 8 / beta1 * (2 / beta1 + math.sqrt(1 + 4 / beta1**2))
    denominator = 1 + xk * math.sqrt(2 / (big_a - 4))
    ratio = (1 - 2 / big_a) / abs(denominator)
    term = math.copysign(ratio ** (1 / 3), denominator)
    z_kurt = (1 - 2 / (9 * big_a) - term) / math.sqrt(2 / (9 * big_a))
    return z_skew**2 + z_kurt**2


@pytest.mark.oracle("econometrics.ols")
@given(inputs=regressions(rows=60), power=st.integers(2, 4))
def test_diagnostics_match_numpy(inputs: dict[str, Any], power: int) -> None:
    found = result(**inputs, reset_power=power)
    out = found.outputs
    x, y, _, e, _, n, k = fit(inputs)
    assert math.isclose(
        out.durbin_watson,
        float(np.sum(np.diff(e) ** 2) / (e @ e)),
        rel_tol=1e-8,
    )
    het = x if inputs["add_constant"] else np.column_stack([np.ones(n), x])
    squares = e**2
    g, *_ = np.linalg.lstsq(het, squares, rcond=None)
    fitted_squares = het @ g
    centered = np.sum((squares - squares.mean()) ** 2)
    lm = n * (1 - np.sum((squares - fitted_squares) ** 2) / centered)
    assert math.isclose(out.breusch_pagan, lm, rel_tol=1e-6, abs_tol=1e-8)
    assert math.isclose(
        out.breusch_pagan_p_value,
        scipy.stats.chi2.sf(lm, het.shape[1] - 1),
        rel_tol=1e-6,
        abs_tol=1e-10,
    )
    d = e - e.mean()
    m2 = np.mean(d**2)
    skew, kurt = np.mean(d**3) / m2**1.5, np.mean(d**4) / m2**2
    jb = n / 6 * (skew**2 + (kurt - 3) ** 2 / 4)
    assert math.isclose(out.jarque_bera, jb, rel_tol=1e-6, abs_tol=1e-9)
    if n >= 20:
        k2 = omnibus(e)
        assert math.isclose(out.omnibus, k2, rel_tol=1e-6, abs_tol=1e-9)
        assert math.isclose(
            out.omnibus_p_value, scipy.stats.chi2.sf(k2, 2), rel_tol=1e-6
        )
    else:
        assert out.omnibus is None
        assert "small_sample" in {w.code for w in found.warnings}
    if out.reset_f is None:
        assert "reset_undefined" in {w.code for w in found.warnings}
    else:
        fitted = y - e
        augmented = np.column_stack([x, *(fitted**p for p in range(2, power + 1))])
        c, *_ = np.linalg.lstsq(augmented, y, rcond=None)
        unrestricted = float(np.sum((y - augmented @ c) ** 2))
        q = power - 1
        f = (float(e @ e) - unrestricted) / q / (unrestricted / (n - k - q))
        assert math.isclose(out.reset_f, f, rel_tol=1e-5, abs_tol=1e-8)


@pytest.mark.oracle("econometrics.ols")
@given(inputs=regressions())
def test_vif_matches_numpy(inputs: dict[str, Any]) -> None:
    out = run(**inputs)
    x = matrix(inputs)
    constant = inputs["add_constant"]
    expected = []
    for j in range(int(constant), x.shape[1]):
        others = np.delete(x, j, axis=1)
        if others.shape[1] == 0:
            expected.append(1.0)
            continue
        c, *_ = np.linalg.lstsq(others, x[:, j], rcond=None)
        resid = x[:, j] - others @ c
        target = x[:, j] - x[:, j].mean() if constant else x[:, j]
        expected.append(float(target @ target / (resid @ resid)))
    assert close(out.vif, np.maximum(1.0, expected), 1e-7, 1e-9)


# --- no stray warnings ------------------------------------------------------------


@settings(max_examples=200)
@given(raw=strategies.inputs(ols))
def test_no_library_warning_escapes_the_model(raw: dict[str, Any]) -> None:
    assert stray_warnings(dict(raw)) == []


def test_nist_wampler_fits_without_library_warnings() -> None:
    x = np.arange(21.0)
    inputs = {
        "response": list(1 + x + x**2 + x**3 + x**4 + x**5),
        "design": np.column_stack([x**p for p in range(1, 6)]),
    }
    assert stray_warnings(inputs) == []


# --- inputs, edge cases and documented errors -------------------------------------


def test_a_table_names_the_regressors() -> None:
    frame = pd.DataFrame({"gdp": [1.0, 2.0, 3.0, 5.0], "rate": [0.5, 0.1, 0.4, 0.2]})
    out = run(response=[1.0, 2.5, 2.9, 5.2], design=frame)
    assert out.names == ("const", "gdp", "rate")
    single = run(response=[1.0, 2.5, 2.9, 5.2], design=np.array([1.0, 2.0, 3.0, 5.0]))
    assert single.names == ("const", "x1")
    listed = run(response=[1.0, 2.5, 2.9, 5.2], design=[1.0, 2.0, 3.0, 5.0])
    assert listed.coefficients == single.coefficients


def test_the_smallest_valid_sample() -> None:
    out = run(response=[1.0, 2.0, 4.0], design=[[0.0], [1.0], [2.0]])
    assert out.degrees_of_freedom == 1
    assert close(out.coefficients, [5 / 6, 3 / 2], 1e-12, 1e-12)


def test_a_perfectly_collinear_design_is_a_domain_error() -> None:
    with pytest.raises(DomainError, match="collinear"):
        run(response=[1.0, 2.0, 3.0, 5.0], design=[[1, 2], [2, 4], [3, 6], [4, 8]])
    with pytest.raises(DomainError, match="collinear"):
        run(response=[1.0, 2.0, 3.0, 5.0], design=[[3.0], [3.0], [3.0], [3.0]])
    with pytest.raises(DomainError, match="zero in every observation"):
        run(response=[1.0, 2.0, 3.0], design=[[0.0], [0.0], [0.0]], add_constant=False)


def test_hc3_with_leverage_one_is_a_domain_error() -> None:
    design = [[1.0, 0.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0]]
    with pytest.raises(DomainError, match="leverage one"):
        run(
            response=[1.0, 2.0, 3.0, 4.0],
            design=design,
            add_constant=False,
            covariance="hc3",
        )
    assert (
        run(
            response=[1.0, 2.0, 3.0, 4.0],
            design=design,
            add_constant=False,
            covariance="hc0",
        ).standard_errors[0]
        == 0.0
    )


def test_a_perfect_fit_has_no_tests() -> None:
    found = result(response=[1.0, 3.0, 5.0, 7.0], design=[[0.0], [1.0], [2.0], [3.0]])
    out = found.outputs
    assert out.t_statistics is out.p_values is out.f_statistic is None
    assert out.durbin_watson is out.reset_f is None
    assert out.r_squared == 1.0
    assert "perfect_fit" in {w.code for w in found.warnings}


def test_a_response_without_variation_has_no_r_squared() -> None:
    found = result(response=[0.0, 0.0, 0.0], design=[[1.0], [2.0], [4.0]])
    assert found.outputs.r_squared is None
    assert "no_variation" in {w.code for w in found.warnings}
    x = [[v] for v in (0.3, -1.2, 2.5, 0.7, 1.9, -0.4, 3.3, 1.1, -2.2, 0.5, 2.8, -0.9)]
    for level in (0.1, 5.0):
        flat = result(response=[level] * 12, design=x)
        assert flat.outputs.r_squared is None
        assert "no_variation" in {w.code for w in flat.warnings}


def test_perfect_fit_is_warned_once() -> None:
    found = result(response=[1.0, 3.0, 5.0, 7.0], design=[[0.0], [1.0], [2.0], [3.0]])
    assert [w.code for w in found.warnings].count("perfect_fit") == 1


def test_a_small_spread_on_a_large_level_is_not_a_perfect_fit() -> None:
    rng = np.random.default_rng(1)
    x = np.arange(200.0)
    y = 1.7e9 + x + rng.normal(0, 5e-4, 200)
    found = result(response=list(y), design=x)
    assert "perfect_fit" not in {w.code for w in found.warnings}
    assert found.outputs.t_statistics is not None
    assert found.outputs.durbin_watson is not None


@pytest.mark.parametrize("scale", [1e-160, 1e-200, 1e-300, 1e14])
def test_the_response_scale_changes_only_the_scaled_outputs(scale: float) -> None:
    rng = np.random.default_rng(2)
    y, x = rng.normal(size=20), rng.normal(size=20)
    base = run(response=list(y), design=x)
    scaled_inputs = {"response": list(y * scale), "design": x}
    assert stray_warnings(scaled_inputs) == []
    scaled = run(**scaled_inputs)
    assert close(np.asarray(scaled.coefficients) / scale, base.coefficients, 1e-9, 0)
    assert close(
        np.asarray(scaled.standard_errors) / scale, base.standard_errors, 1e-9, 0
    )
    assert math.isclose(scaled.residual_std_error / scale, base.residual_std_error)
    for name in ("t_statistics", "f_statistic", "r_squared", "durbin_watson"):
        assert close(getattr(scaled, name), getattr(base, name), 1e-9, 1e-12)


def test_newey_west_picks_the_lags_when_none_are_given() -> None:
    rng = np.random.default_rng(5)
    design = rng.normal(size=(250, 1))
    out = run(response=list(rng.normal(size=250)), design=design, covariance="hac")
    assert out.hac_lags == math.floor(4 * 2.5 ** (2 / 9))


def test_the_chart_plots_residuals_against_fitted_values() -> None:
    found = result(response=[1.0, 2.5, 2.9, 5.2], design=[1.0, 2.0, 3.0, 5.0])
    figure = found.plot()
    assert list(figure.data[0].y) == list(found.outputs.residuals)


@pytest.mark.parametrize(
    "inputs",
    [
        {"response": [1.0, 2.0, 3.0], "design": [[1.0], [2.0]]},
        {"response": [1.0, 2.0, 3.0], "design": [[1.0], [2.0, 3.0], [4.0]]},
        {"response": [1.0, 2.0], "design": [[1.0], [2.0]]},
        {"response": [1.0, 2.0, 3.0], "design": [[1.0], [2.0], [3.0]], "names": []},
        {
            "response": [1.0, 2.0, 3.0, 4.0],
            "design": [[1.0, 2.0], [2.0, 1.0], [3.0, 5.0], [4.0, 1.0]],
            "names": ["a", "a"],
        },
        {
            "response": [1.0, 2.0, 3.0],
            "design": [[1.0], [2.0], [4.0]],
            "names": ["const"],
        },
        {
            "response": [1.0, 2.0, 3.0],
            "design": [[1.0], [2.0], [4.0]],
            "covariance": "hac",
            "hac_lags": 3,
        },
    ],
)
def test_inconsistent_inputs_are_refused(inputs: dict[str, Any]) -> None:
    with pytest.raises(InputError):
        run(**inputs)


# --- the econometrics extra ---------------------------------------------------------


@pytest.fixture
def without_statsmodels(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make statsmodels unimportable and its distribution look uninstalled."""
    for name in [m for m in sys.modules if m.split(".")[0] == "statsmodels"]:
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.setitem(sys.modules, "statsmodels", None)
    installed = core_registry._is_installed  # noqa: SLF001

    def missing(distribution: str) -> bool:
        return distribution != "statsmodels" and installed(distribution)

    monkeypatch.setattr(core_registry, "_is_installed", missing)


@pytest.mark.usefixtures("without_statsmodels")
def test_without_statsmodels_the_model_names_the_extra() -> None:
    example = ols.spec.examples[0].inputs
    with pytest.raises(MissingOptionalDependencyError) as caught:
        run_model(ols, example)
    assert caught.value.extra == "econometrics"
    assert caught.value.package == "statsmodels"
    assert "pip install 'pyeconomics[econometrics]'" in str(caught.value)


@pytest.mark.usefixtures("without_statsmodels")
def test_without_statsmodels_the_registry_still_validates() -> None:
    registration = next(
        r for r in core_registry.installed().registrations if r.model.id == ols.id
    )
    assert not registration.provider.installed("econometrics")
    registry.validate()


def test_with_statsmodels_the_extra_is_installed() -> None:
    registration = next(
        r for r in core_registry.installed().registrations if r.model.id == ols.id
    )
    assert registration.provider.declares("econometrics")
    assert registration.provider.installed("econometrics")
    assert ols.spec.extra == "econometrics"


def test_importing_the_package_does_not_import_statsmodels(tmp_path: Path) -> None:
    code = (
        "import sys, pyeconomics.models.econometrics; "
        "print('statsmodels' in sys.modules)"
    )
    # From an empty directory: the checkout's root must not be on sys.path.
    found = subprocess.run(  # noqa: S603 # nosec B603: fixed arguments, no shell
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        cwd=tmp_path,
    )
    assert found.stdout.strip() == "False"
