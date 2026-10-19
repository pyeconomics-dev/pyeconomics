# tests/results/test_plotting.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``Result.plot()``: Plotly figures from the specification's charts."""

from __future__ import annotations

import sys
from typing import Any

import plotly.graph_objects as go
import pytest
import toy_models as tm
import toy_results_models as rm

from pyeconomics.core import MissingOptionalDependencyError, Model, run_model


def growth() -> object:
    return run_model(rm.growth, start=100, rate=0.1, periods=2)


def test_a_line_chart_plots_the_named_outputs() -> None:
    figure = run_model(rm.growth, start=100, rate=0.1, periods=2).plot("path")
    assert isinstance(figure, go.Figure)
    (trace,) = figure.data
    assert isinstance(trace, go.Scatter)
    assert trace.mode == "lines"
    assert list(trace.x) == [0, 1, 2]
    assert list(trace.y) == pytest.approx([100, 110, 121])
    assert trace.name == "balance"
    assert figure.layout.title.text == "Balance over time"
    assert figure.layout.xaxis.title.text == "Period"
    assert figure.layout.yaxis.title.text == "Balance"


def test_bar_and_scatter_charts() -> None:
    result = run_model(rm.growth, start=100, rate=0.1, periods=2)
    bars = result.plot("bars")
    assert isinstance(bars.data[0], go.Bar)
    # Without labels the axes carry the output names.
    assert bars.layout.xaxis.title.text == "period"
    assert bars.layout.yaxis.title.text == "balance"
    dots = result.plot("dots")
    assert dots.data[0].mode == "markers"


def test_the_only_chart_needs_no_name() -> None:
    figure = run_model(rm.one_chart, periods=3).plot()
    assert list(figure.data[0].y) == [0.0, 1.0, 2.0, 3.0]


def test_several_charts_need_a_name() -> None:
    result = run_model(rm.growth, start=100, rate=0.1, periods=2)
    with pytest.raises(ValueError, match="name one of: path, bars, dots"):
        result.plot()
    with pytest.raises(ValueError, match=r"no chart .nope.*path, bars, dots"):
        result.plot("nope")


def test_a_model_without_charts_cannot_plot() -> None:
    result = run_model(rm.no_chart, x=1)
    with pytest.raises(ValueError, match="declares no chart"):
        result.plot()
    with pytest.raises(ValueError, match="its charts: none"):
        result.plot("anything")


def test_a_chart_belongs_to_its_calculation() -> None:
    import dataclasses  # noqa: PLC0415

    from pyeconomics.core import ChartKind, ChartSpec, Model  # noqa: PLC0415

    charts = (
        ChartSpec(
            id="pv",
            title="Present value",
            kind=ChartKind.LINE,
            x="present_value",
            y=("present_value",),
            calculation="present_value",
        ),
    )
    model = Model(
        dataclasses.replace(tm.time_value.spec, charts=charts), tm.time_value.compute
    )
    future = run_model(
        model, calculation="future_value", present_value=1, rate=0.1, years=1
    )
    with pytest.raises(ValueError, match="declares no chart"):
        future.plot()


def test_without_plotly_the_error_names_the_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "plotly", None)
    monkeypatch.setitem(sys.modules, "plotly.graph_objects", None)
    result = run_model(rm.growth, start=100, rate=0.1, periods=2)
    with pytest.raises(MissingOptionalDependencyError) as caught:
        result.plot("path")
    assert "pyeconomics[plot]" in str(caught.value)
    assert caught.value.extra == "plot"
    assert isinstance(caught.value, ImportError)


def test_the_figure_json_is_plain_json() -> None:
    import json  # noqa: PLC0415

    figure = run_model(rm.growth, start=100, rate=0.1, periods=2).plot("path")
    assert json.loads(figure.to_json())["data"][0]["type"] == "scatter"


def _banded(*y: str) -> Model[Any, Any]:
    import dataclasses  # noqa: PLC0415

    from pyeconomics.core import ChartKind, ChartSpec  # noqa: PLC0415

    band = ChartSpec(
        id="band", title="A band", kind=ChartKind.BAND, x="period", y=tuple(y)
    )
    return Model(dataclasses.replace(rm.growth.spec, charts=(band,)), rm.growth.compute)


def test_a_band_shades_between_its_first_two_fields_and_draws_the_rest() -> None:
    model = _banded("balance", "balance", "balance")
    figure = run_model(model, start=100, rate=0.1, periods=2).plot()
    lower, upper, line = figure.data
    assert lower.line.width == 0
    assert upper.fill == "tonexty"
    assert line.mode == "lines"
    assert list(upper.y) == pytest.approx([100, 110, 121])


def test_a_band_needs_a_lower_and_an_upper_edge() -> None:
    from pyeconomics.core import Registry  # noqa: PLC0415

    problems = Registry.from_models(_banded("balance")).problems()
    assert any(
        p.rule == "charts" and "lower and upper edges" in p.detail for p in problems
    )
    sound = Registry.from_models(_banded("balance", "balance")).problems()
    assert not [p for p in sound if p.rule == "charts"]
