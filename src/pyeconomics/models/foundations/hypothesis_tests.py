# src/pyeconomics/models/foundations/hypothesis_tests.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Classical tests from summary statistics: ``foundations.hypothesis_tests``.

Six calculations, discriminated on ``calculation``, each from sizes, means and
standard deviations rather than data:

- ``one_sample_t``: a mean against a hypothesized value;
- ``two_sample_t``: two means, with pooled variance or Welch's unequal variances;
- ``paired_t``: the mean of paired differences;
- ``z_mean``: a mean with a known population standard deviation;
- ``chi_square_variance``: a variance against a hypothesized one;
- ``f_variances``: the ratio of two variances.

Each returns its statistic, the p-value for the chosen alternative, the
critical values and the decision at ``alpha``, and the two-sided confidence
interval at ``1 - alpha`` for the quantity tested. A two-sided p-value is twice
the smaller one-sided p-value, capped at 1, for the asymmetric chi-square and F
distributions too.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Protocol

from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Count,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Probability,
    Ratio,
    Reference,
    Symbol,
    model,
)
from pyeconomics.core.model import ARRAY_INPUT

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["hypothesis_tests"]

type Alternative = Literal["two_sided", "less", "greater"]


class _Distribution(Protocol):
    """What the tests use of a frozen SciPy distribution."""

    def cdf(self, x: float, /) -> Any: ...  # noqa: ANN401 - SciPy returns arrays
    def sf(self, x: float, /) -> Any: ...  # noqa: ANN401
    def ppf(self, q: float, /) -> Any: ...  # noqa: ANN401
    def isf(self, q: float, /) -> Any: ...  # noqa: ANN401


#: Bounds on the summary statistics. A test statistic from inputs at these
#: bounds reaches about 1e16 and a variance-ratio interval about 1e24, so the
#: outputs widen the ratio's default bounds to 1e30.
_MEAN_MAX: Final = 1e9
_SD_MIN: Final = 1e-4
_SD_MAX: Final = 1e4
_N_MAX: Final = 1_000_000
_OUT_MAX: Final = 1e30
#: Two samples of a million give up to two million degrees of freedom.
_DF_MAX: Final = 2.0 * _N_MAX

_Criticals = Annotated[
    tuple[Annotated[Ratio, Field(ge=-_OUT_MAX, le=_OUT_MAX)], ...], ARRAY_INPUT
]


def _size(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=2, le=_N_MAX, description=description)


def _mean(description: str, default: float | None = None) -> Any:  # noqa: ANN401
    if default is None:
        return Field(ge=-_MEAN_MAX, le=_MEAN_MAX, description=description)
    return Field(default, ge=-_MEAN_MAX, le=_MEAN_MAX, description=description)


def _sd(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=_SD_MIN, le=_SD_MAX, description=description)


def _out(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-_OUT_MAX, le=_OUT_MAX, description=description)


def _df(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=0, le=_DF_MAX, description=description)


# --- inputs ------------------------------------------------------------------


class _Test(ModelInputs):
    alternative: Alternative = Field(
        "two_sided", description="The alternative hypothesis"
    )
    alpha: Probability = Field(0.05, ge=1e-4, le=0.5, description="Significance level")


class OneSampleTInputs(_Test):
    """One sample's size, mean and standard deviation."""

    calculation: Literal["one_sample_t"] = Field(
        "one_sample_t", description="One-sample t test of a mean"
    )
    n: Count = _size("Sample size")
    mean: Ratio = _mean("Sample mean")
    sd: Ratio = _sd("Sample standard deviation (n - 1)")
    hypothesized_mean: Ratio = _mean("Mean under the null hypothesis", 0.0)


class TwoSampleTInputs(_Test):
    """Two independent samples' sizes, means and standard deviations."""

    calculation: Literal["two_sample_t"] = Field(
        "two_sample_t", description="Two-sample t test of a difference in means"
    )
    n1: Count = _size("First sample size")
    mean1: Ratio = _mean("First sample mean")
    sd1: Ratio = _sd("First sample standard deviation (n - 1)")
    n2: Count = _size("Second sample size")
    mean2: Ratio = _mean("Second sample mean")
    sd2: Ratio = _sd("Second sample standard deviation (n - 1)")
    equal_variances: bool = Field(
        default=True,
        description="Pool the variances (Student); false for Welch's test",
    )
    hypothesized_difference: Ratio = _mean(
        "mean1 - mean2 under the null hypothesis", 0.0
    )


class PairedTInputs(_Test):
    """The size, mean and standard deviation of paired differences."""

    calculation: Literal["paired_t"] = Field(
        "paired_t", description="Paired t test of a mean difference"
    )
    n: Count = _size("Number of pairs")
    mean_difference: Ratio = _mean("Mean of the differences")
    sd_difference: Ratio = _sd("Standard deviation of the differences (n - 1)")
    hypothesized_difference: Ratio = _mean(
        "Mean difference under the null hypothesis", 0.0
    )


class ZMeanInputs(_Test):
    """A sample mean, its size, and the known population standard deviation."""

    calculation: Literal["z_mean"] = Field(
        "z_mean", description="z test of a mean with known sigma"
    )
    n: Count = Field(ge=1, le=_N_MAX, description="Sample size")
    mean: Ratio = _mean("Sample mean")
    sigma: Ratio = _sd("Known population standard deviation")
    hypothesized_mean: Ratio = _mean("Mean under the null hypothesis", 0.0)


class ChiSquareVarianceInputs(_Test):
    """A sample's size and standard deviation, and the hypothesized one."""

    calculation: Literal["chi_square_variance"] = Field(
        "chi_square_variance", description="Chi-square test of a variance"
    )
    n: Count = _size("Sample size")
    sd: Ratio = _sd("Sample standard deviation (n - 1)")
    hypothesized_sd: Ratio = _sd("Standard deviation under the null hypothesis")


class FVariancesInputs(_Test):
    """Two independent samples' sizes and standard deviations."""

    calculation: Literal["f_variances"] = Field(
        "f_variances", description="F test of the ratio of two variances"
    )
    n1: Count = _size("First sample size")
    sd1: Ratio = _sd("First sample standard deviation (n - 1)")
    n2: Count = _size("Second sample size")
    sd2: Ratio = _sd("Second sample standard deviation (n - 1)")


HypothesisTestsInputs = Annotated[
    OneSampleTInputs
    | TwoSampleTInputs
    | PairedTInputs
    | ZMeanInputs
    | ChiSquareVarianceInputs
    | FVariancesInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


class _Result(ModelOutputs):
    statistic: Ratio = _out("The test statistic")
    p_value: Probability = Field(
        ge=0, le=1, description="p-value for the chosen alternative"
    )
    critical_values: _Criticals = Field(
        min_length=1,
        max_length=2,
        description=(
            "Bounds of the rejection region: lower and upper for a two-sided "
            "test, the one bound for a one-sided test"
        ),
    )
    reject: bool = Field(description="Whether the null hypothesis is rejected at alpha")
    estimate: Ratio = _out("Point estimate of the quantity tested")
    ci_lower: Ratio = _out("Lower end of the two-sided 1 - alpha confidence interval")
    ci_upper: Ratio = _out("Upper end of the two-sided 1 - alpha confidence interval")


class _MeanResult(_Result):
    standard_error: Ratio = Field(
        ge=0, le=1e5, description="Standard error of the estimate"
    )


class OneSampleTOutputs(_MeanResult):
    calculation: Literal["one_sample_t"] = Field(
        "one_sample_t", description="One-sample t test of a mean"
    )
    degrees_of_freedom: Ratio = _df("n - 1")


class TwoSampleTOutputs(_MeanResult):
    calculation: Literal["two_sample_t"] = Field(
        "two_sample_t", description="Two-sample t test of a difference in means"
    )
    degrees_of_freedom: Ratio = _df(
        "n1 + n2 - 2 when pooled; Welch-Satterthwaite otherwise"
    )


class PairedTOutputs(_MeanResult):
    calculation: Literal["paired_t"] = Field(
        "paired_t", description="Paired t test of a mean difference"
    )
    degrees_of_freedom: Ratio = _df("n - 1")


class ZMeanOutputs(_MeanResult):
    calculation: Literal["z_mean"] = Field(
        "z_mean", description="z test of a mean with known sigma"
    )


class ChiSquareVarianceOutputs(_Result):
    calculation: Literal["chi_square_variance"] = Field(
        "chi_square_variance", description="Chi-square test of a variance"
    )
    degrees_of_freedom: Ratio = _df("n - 1")


class FVariancesOutputs(_Result):
    calculation: Literal["f_variances"] = Field(
        "f_variances", description="F test of the ratio of two variances"
    )
    df_numerator: Ratio = _df("n1 - 1")
    df_denominator: Ratio = _df("n2 - 1")


HypothesisTestsOutputs = Annotated[
    OneSampleTOutputs
    | TwoSampleTOutputs
    | PairedTOutputs
    | ZMeanOutputs
    | ChiSquareVarianceOutputs
    | FVariancesOutputs,
    Field(discriminator="calculation"),
]


# --- the tests ---------------------------------------------------------------


def _decide(
    distribution: _Distribution,
    statistic: float,
    alternative: Alternative,
    alpha: float,
) -> dict[str, Any]:
    """Return the p-value, critical values and decision for one statistic."""
    lower_p = float(distribution.cdf(statistic))
    upper_p = float(distribution.sf(statistic))
    if alternative == "less":
        critical: tuple[float, ...] = (float(distribution.ppf(alpha)),)
        p_value, reject = lower_p, statistic < critical[0]
    elif alternative == "greater":
        critical = (float(distribution.isf(alpha)),)
        p_value, reject = upper_p, statistic > critical[0]
    else:
        critical = (
            float(distribution.ppf(alpha / 2)),
            float(distribution.isf(alpha / 2)),
        )
        p_value = min(1.0, 2.0 * min(lower_p, upper_p))
        reject = statistic < critical[0] or statistic > critical[1]
    return {
        "statistic": statistic,
        "p_value": p_value,
        "critical_values": critical,
        "reject": reject,
    }


def _location(
    distribution: _Distribution,
    estimate: float,
    hypothesized: float,
    standard_error: float,
    inputs: _Test,
) -> dict[str, Any]:
    """Decide a test of a mean or a difference of means, with its interval."""
    statistic = (estimate - hypothesized) / standard_error
    half_width = float(distribution.isf(inputs.alpha / 2)) * standard_error
    return {
        **_decide(distribution, statistic, inputs.alternative, inputs.alpha),
        "estimate": estimate,
        "standard_error": standard_error,
        "ci_lower": estimate - half_width,
        "ci_upper": estimate + half_width,
    }


def _one_sample_t(inputs: OneSampleTInputs) -> OneSampleTOutputs:
    from scipy import stats  # noqa: PLC0415 - SciPy loads on first use

    df = inputs.n - 1
    se = inputs.sd / math.sqrt(inputs.n)
    found = _location(stats.t(df), inputs.mean, inputs.hypothesized_mean, se, inputs)
    return OneSampleTOutputs(degrees_of_freedom=df, **found)


def _two_sample_t(inputs: TwoSampleTInputs) -> TwoSampleTOutputs:
    from scipy import stats  # noqa: PLC0415 - SciPy loads on first use

    n1, n2 = inputs.n1, inputs.n2
    v1, v2 = inputs.sd1**2, inputs.sd2**2
    if inputs.equal_variances:
        df = float(n1 + n2 - 2)
        pooled = ((n1 - 1) * v1 + (n2 - 1) * v2) / df
        se = math.sqrt(pooled * (1 / n1 + 1 / n2))
    else:
        a, b = v1 / n1, v2 / n2
        se = math.sqrt(a + b)
        df = (a + b) ** 2 / (a * a / (n1 - 1) + b * b / (n2 - 1))
    found = _location(
        stats.t(df),
        inputs.mean1 - inputs.mean2,
        inputs.hypothesized_difference,
        se,
        inputs,
    )
    return TwoSampleTOutputs(degrees_of_freedom=df, **found)


def _paired_t(inputs: PairedTInputs) -> PairedTOutputs:
    from scipy import stats  # noqa: PLC0415 - SciPy loads on first use

    df = inputs.n - 1
    se = inputs.sd_difference / math.sqrt(inputs.n)
    found = _location(
        stats.t(df),
        inputs.mean_difference,
        inputs.hypothesized_difference,
        se,
        inputs,
    )
    return PairedTOutputs(degrees_of_freedom=df, **found)


def _z_mean(inputs: ZMeanInputs) -> ZMeanOutputs:
    from scipy import stats  # noqa: PLC0415 - SciPy loads on first use

    se = inputs.sigma / math.sqrt(inputs.n)
    found = _location(stats.norm(), inputs.mean, inputs.hypothesized_mean, se, inputs)
    return ZMeanOutputs(**found)


def _chi_square_variance(inputs: ChiSquareVarianceInputs) -> ChiSquareVarianceOutputs:
    from scipy import stats  # noqa: PLC0415 - SciPy loads on first use

    df = inputs.n - 1
    variance = inputs.sd**2
    statistic = df * variance / inputs.hypothesized_sd**2
    distribution = stats.chi2(df)
    tail = inputs.alpha / 2
    return ChiSquareVarianceOutputs(
        degrees_of_freedom=df,
        estimate=variance,
        ci_lower=df * variance / float(distribution.isf(tail)),
        ci_upper=df * variance / float(distribution.ppf(tail)),
        **_decide(distribution, statistic, inputs.alternative, inputs.alpha),
    )


def _f_variances(inputs: FVariancesInputs) -> FVariancesOutputs:
    from scipy import stats  # noqa: PLC0415 - SciPy loads on first use

    d1, d2 = inputs.n1 - 1, inputs.n2 - 1
    ratio = inputs.sd1**2 / inputs.sd2**2
    distribution = stats.f(d1, d2)
    tail = inputs.alpha / 2
    return FVariancesOutputs(
        df_numerator=d1,
        df_denominator=d2,
        estimate=ratio,
        ci_lower=ratio / float(distribution.isf(tail)),
        ci_upper=ratio / float(distribution.ppf(tail)),
        **_decide(distribution, ratio, inputs.alternative, inputs.alpha),
    )


# --- the model ---------------------------------------------------------------


def _nist(key: str, section: str, title: str, page: str) -> Reference:
    return Reference(
        key=key,
        citation=(
            f"NIST/SEMATECH (2012). e-Handbook of Statistical Methods, section "
            f"{section}, {title}."
        ),
        url=f"https://www.itl.nist.gov/div898/handbook/eda/section3/{page}.htm",
        locator=f"Section {section}",
    )


_STUDENT = Reference(
    key="student1908",
    citation="Student (1908). The probable error of a mean. Biometrika, 6(1), 1-25.",
    doi="10.1093/biomet/6.1.1",
    locator="The distribution of the mean over its estimated standard deviation",
)
_WELCH = Reference(
    key="welch1947",
    citation=(
        "Welch, B. L. (1947). The generalization of 'Student's' problem when "
        "several different population variances are involved. Biometrika, "
        "34(1-2), 28-35."
    ),
    doi="10.1093/biomet/34.1-2.28",
    locator="The approximate degrees of freedom of the difference of two means",
)


@model(
    id="foundations.hypothesis_tests",
    version=1,
    title="Hypothesis tests from summary statistics",
    summary=(
        "One-sample, two-sample (pooled and Welch) and paired t tests, the z "
        "test, and chi-square and F tests of variances, with p-values, critical "
        "values and confidence intervals."
    ),
    formula=(
        r"t = \frac{\bar{x} - \mu_0}{s / \sqrt{n}}, \quad \nu = n - 1",
        (
            r"t = \frac{\bar{x}_1 - \bar{x}_2 - \delta_0}"
            r"{s_p \sqrt{1/n_1 + 1/n_2}}, \quad \nu = n_1 + n_2 - 2"
        ),
        (
            r"t = \frac{\bar{x}_1 - \bar{x}_2 - \delta_0}"
            r"{\sqrt{s_1^2/n_1 + s_2^2/n_2}}, \quad \nu = \frac{(s_1^2/n_1 + "
            r"s_2^2/n_2)^2}{\frac{(s_1^2/n_1)^2}{n_1 - 1} + \frac{(s_2^2/n_2)^2}"
            r"{n_2 - 1}}"
        ),
        r"z = \frac{\bar{x} - \mu_0}{\sigma / \sqrt{n}}",
        r"\chi^2 = \frac{(n - 1) s^2}{\sigma_0^2}, \quad F = \frac{s_1^2}{s_2^2}",
    ),
    symbols=(
        Symbol("t", "The t statistic", "statistic"),
        Symbol(r"\bar{x}", "Sample mean", "mean"),
        Symbol(r"\mu_0", "The mean under the null hypothesis", "hypothesized_mean"),
        Symbol("s", "Sample standard deviation", "sd"),
        Symbol("n", "Sample size", "n"),
        Symbol(r"\nu", "Degrees of freedom", "degrees_of_freedom"),
        Symbol(r"\bar{x}_1", "Mean of the first sample", "mean1"),
        Symbol(r"\bar{x}_2", "Mean of the second sample", "mean2"),
        Symbol(
            r"\delta_0",
            "The difference in means under the null hypothesis",
            "hypothesized_difference",
        ),
        Symbol("s_p", "Pooled standard deviation of the two samples"),
        Symbol("n_1", "Size of the first sample", "n1"),
        Symbol("n_2", "Size of the second sample", "n2"),
        Symbol("s_1", "Standard deviation of the first sample", "sd1"),
        Symbol("s_2", "Standard deviation of the second sample", "sd2"),
        Symbol("z", "The z statistic", "statistic"),
        Symbol(r"\sigma", "The population's known standard deviation", "sigma"),
        Symbol(r"\chi^2", "The chi-square statistic", "statistic"),
        Symbol(
            r"\sigma_0",
            "The standard deviation under the null hypothesis",
            "hypothesized_sd",
        ),
        Symbol("F", "The F statistic", "statistic"),
    ),
    assumptions=(
        (
            "Samples are independent random samples; the t and z tests assume "
            "normal means, and the chi-square and F tests normal data."
        ),
        (
            "Standard deviations are sample standard deviations with n - 1 in "
            "the denominator; sigma in the z test is known."
        ),
        (
            "The confidence interval is always two-sided at 1 - alpha, whatever "
            "the alternative."
        ),
    ),
    limitations=(
        (
            "The chi-square and F tests are sensitive to non-normal data; "
            "summary statistics cannot reveal it."
        ),
        "Welch's degrees of freedom are an approximation.",
        "No correction is made for multiple comparisons.",
    ),
    references=(
        _nist("nist_mean", "1.3.5.2", "Confidence Limits for the Mean", "eda352"),
        _nist(
            "nist_two_sample", "1.3.5.3", "Two-Sample t-Test for Equal Means", "eda353"
        ),
        _nist(
            "nist_chi_square", "1.3.5.8", "Chi-Square Test for the Variance", "eda358"
        ),
        _nist("nist_f", "1.3.5.9", "F-Test for Equality of Two Variances", "eda359"),
        _STUDENT,
        _WELCH,
    ),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("hypothesis test", "t test", "chi-square", "f test", "confidence interval"),
    invariants=(
        Invariant(
            id="p_value_in_unit_interval",
            statement="Every p-value lies in [0, 1].",
        ),
        Invariant(
            id="interval_contains_estimate",
            statement="The confidence interval contains the point estimate.",
        ),
        Invariant(
            id="two_sided_p_is_twice_one_sided",
            statement=(
                "The two-sided p-value is twice the smaller of the two one-sided "
                "p-values, capped at 1."
            ),
        ),
    ),
    examples=(
        Example(
            name="mean_against_five",
            inputs={
                "calculation": "one_sample_t",
                "n": 195,
                "mean": 9.26146,
                "sd": 0.022789,
                "hypothesized_mean": 5,
            },
        ),
        Example(
            name="two_car_fleets",
            inputs={
                "calculation": "two_sample_t",
                "n1": 249,
                "mean1": 20.14458,
                "sd1": 6.4147,
                "n2": 79,
                "mean2": 30.48101,
                "sd2": 6.10771,
            },
        ),
        Example(
            name="before_and_after",
            inputs={
                "calculation": "paired_t",
                "n": 10,
                "mean_difference": 1.2,
                "sd_difference": 2.1,
            },
        ),
        Example(
            name="known_sigma",
            inputs={
                "calculation": "z_mean",
                "n": 36,
                "mean": 102.0,
                "sigma": 6.0,
                "hypothesized_mean": 100.0,
            },
        ),
        Example(
            name="gear_diameters",
            inputs={
                "calculation": "chi_square_variance",
                "n": 100,
                "sd": 0.0063,
                "hypothesized_sd": 0.1,
            },
        ),
        Example(
            name="two_batches",
            inputs={
                "calculation": "f_variances",
                "n1": 240,
                "sd1": 65.54909,
                "n2": 240,
                "sd2": 61.85425,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def hypothesis_tests(inputs: HypothesisTestsInputs) -> HypothesisTestsOutputs:
    """Run the test the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[
    dict[type[ModelInputs], Callable[[Any], HypothesisTestsOutputs]]
] = {
    OneSampleTInputs: _one_sample_t,
    TwoSampleTInputs: _two_sample_t,
    PairedTInputs: _paired_t,
    ZMeanInputs: _z_mean,
    ChiSquareVarianceInputs: _chi_square_variance,
    FVariancesInputs: _f_variances,
}
