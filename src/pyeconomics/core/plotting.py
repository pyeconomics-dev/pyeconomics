# src/pyeconomics/core/plotting.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Plotly figures from a result and its model's chart specifications.

Plotly belongs to the ``plot`` extra and is imported only when a figure is
asked for. A figure's JSON renders unchanged in notebooks, the docs, the web app
(Plotly.js) and MCP Apps (ROADMAP section 4 2.3). The charts come from the
model's :class:`~pyeconomics.core.spec.ChartSpec` list, so a model draws
nothing itself.

Examples
--------
>>> from pyeconomics.core.plotting import PLOTLY_EXTRA
>>> PLOTLY_EXTRA
'plot'
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core._optional import import_optional
from pyeconomics.core.spec import ChartKind

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pyeconomics.core.model import Model
    from pyeconomics.core.results import Result
    from pyeconomics.core.spec import ChartSpec

__all__ = ["PLOTLY_EXTRA", "applicable", "charts_for", "figure", "figure_of"]

#: The extra that installs Plotly.
PLOTLY_EXTRA: Final = "plot"


def charts_for(model: Model[Any, Any], calculation: object) -> tuple[ChartSpec, ...]:
    """Return a model's charts that apply to a calculation, in declared order.

    ``calculation`` is a result's ``calculation`` input, ``None`` for a model
    that is not a family. Reading the specification needs no Plotly.
    """
    return tuple(
        chart
        for chart in model.spec.charts
        if chart.calculation is None or chart.calculation == calculation
    )


def applicable(result: Result[Any, Any]) -> tuple[ChartSpec, ...]:
    """Return the charts that apply to a result, in the order the model declares.

    A chart tied to one calculation of a family applies only to a result of that
    calculation. Reading the specification needs no Plotly.
    """
    return charts_for(result.model, getattr(result.inputs, "calculation", None))


def _pick(
    model_id: str, charts: tuple[ChartSpec, ...], chart_id: str | None
) -> ChartSpec:
    if chart_id is not None:
        for chart in charts:
            if chart.id == chart_id:
                return chart
        known = ", ".join(chart.id for chart in charts) or "none"
        msg = f"model {model_id!r} has no chart {chart_id!r}; its charts: {known}"
        raise ValueError(msg)
    if not charts:
        msg = f"model {model_id!r} declares no chart for this result"
        raise ValueError(msg)
    if len(charts) > 1:
        known = ", ".join(chart.id for chart in charts)
        msg = f"model {model_id!r} has several charts; name one of: {known}"
        raise ValueError(msg)
    return charts[0]


def figure(result: Result[Any, Any], chart_id: str | None = None) -> Any:  # noqa: ANN401 - a Plotly figure
    """Build the Plotly figure of one chart of a result.

    Parameters
    ----------
    result
        The result to draw.
    chart_id
        The chart's id; optional when exactly one chart applies.

    Raises
    ------
    MissingOptionalDependencyError
        If Plotly is not installed; the message names ``pyeconomics[plot]``.
    ValueError
        If no chart, or more than one, applies and none was named.
    """
    graph_objects = import_optional("plotly.graph_objects", extra=PLOTLY_EXTRA)
    spec = _pick(result.model_id, applicable(result), chart_id)
    return _draw(graph_objects, spec, result.outputs.model_dump(mode="python"))


def figure_of(
    model: Model[Any, Any], document: Mapping[str, Any], chart_id: str | None = None
) -> Any:  # noqa: ANN401 - a Plotly figure
    """Build the Plotly figure of one chart of a result's JSON document.

    ``document`` is a result in the shape of
    :meth:`~pyeconomics.core.results.Result.to_dict` (or its canonical JSON,
    parsed), as a surface holds it after the run: the figure is the one
    :func:`figure` builds from the result itself.

    Raises
    ------
    MissingOptionalDependencyError
        If Plotly is not installed; the message names ``pyeconomics[plot]``.
    ValueError
        If no chart, or more than one, applies and none was named.
    """
    graph_objects = import_optional("plotly.graph_objects", extra=PLOTLY_EXTRA)
    calculation = document["inputs"].get("calculation")
    spec = _pick(model.id, charts_for(model, calculation), chart_id)
    return _draw(graph_objects, spec, document["outputs"])


def _draw(graph_objects: Any, spec: ChartSpec, outputs: Mapping[str, Any]) -> Any:  # noqa: ANN401 - Plotly
    x = list(outputs[spec.x])
    fig = graph_objects.Figure()
    lines = spec.y
    if spec.kind is ChartKind.BAND:
        lower, upper, *rest = spec.y
        lines = tuple(rest)
        # The upper edge fills down to the lower one; an empty band draws nothing.
        fig.add_trace(
            graph_objects.Scatter(
                x=x, y=list(outputs[lower]), mode="lines", line={"width": 0}, name=lower
            )
        )
        fig.add_trace(
            graph_objects.Scatter(
                x=x,
                y=list(outputs[upper]),
                mode="lines",
                line={"width": 0},
                fill="tonexty",
                name=upper,
            )
        )
    for name in lines:
        values = list(outputs[name])
        if spec.kind is ChartKind.BAR:
            fig.add_trace(graph_objects.Bar(x=x, y=values, name=name))
        else:
            mode = "markers" if spec.kind is ChartKind.SCATTER else "lines"
            fig.add_trace(graph_objects.Scatter(x=x, y=values, mode=mode, name=name))
    fig.update_layout(
        title={"text": spec.title},
        xaxis={"title": {"text": spec.x_label or spec.x}},
        yaxis={"title": {"text": spec.y_label or ", ".join(spec.y)}},
    )
    return fig
