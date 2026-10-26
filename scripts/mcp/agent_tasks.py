# scripts/mcp/agent_tasks.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The agent tasks the MCP server's tool descriptions are tested with.

Each :class:`AgentTask` is a question an assistant answers through the tools:

- in CI, tests/mcp/test_mcp_agent_tasks.py runs its scripted :attr:`~AgentTask.calls`
  against the server in memory (over stand-ins for every provider) and checks
  the value they reach against the Python API's (:attr:`~AgentTask.expected`);
- on the maintainer's machine, scripts/mcp_agent_eval.py gives its
  :attr:`~AgentTask.prompt` to a real agent (Claude Code headless) with
  ``pyeconomics mcp`` as its only server, records the agent's tool calls and
  answer, and checks that it called the task's :attr:`~AgentTask.tools` in order
  and answered the expected value within :attr:`~AgentTask.tolerance`, computed
  then through the Python API from live data.

A refusal task (:attr:`~AgentTask.refusal`) succeeds when the tool answers that
problem and the agent reports the data as unavailable. Expected values read data
with the policy an MCP server holds by default
(:attr:`~pyeconomics.core.LlmUsePolicy.ALLOWED_ONLY`).
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

__all__ = ["DISCOVERY", "TASKS", "AgentTask", "Call"]

#: The discovery tools; every other tool is a model's own.
DISCOVERY: Final = frozenset(
    {"search_models", "describe_model", "run_model", "get_series", "list_sources"}
)


@dataclass(frozen=True, slots=True, kw_only=True)
class Call:
    """One scripted tool call."""

    tool: str
    arguments: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class AgentTask:
    """One question, the tools that answer it and the value they reach.

    ``tools`` lists the tools an agent must call, in this order (others may come
    between): a headline tool's name is also matched by ``run_model`` naming its
    model. ``answer`` reads the value from the last scripted call's structured
    content; ``expected`` computes it through the Python API. ``mentions`` are
    texts the answer must include (an attribution).
    """

    id: str
    prompt: str
    tools: tuple[str, ...]
    calls: tuple[Call, ...]
    answer: Callable[[Mapping[str, Any]], Any] | None = None
    expected: Callable[[], Any] | None = None
    tolerance: float = 1e-3
    refusal: str | None = None
    mentions: tuple[str, ...] = ()


BOND: Final = {
    "settlement": "2026-01-15",
    "maturity": "2036-01-15",
    "coupon_rate": 0.045,
    "yield_to_maturity": 0.05,
}
_BOND_TEXT: Final = (
    "a bond that settles on 2026-01-15 and matures on 2036-01-15, with a 4.5% "
    "coupon paid semiannually and a 5% yield to maturity"
)
OPTION: Final = {
    "calculation": "price",
    "option_type": "call",
    "spot": 100,
    "strike": 105,
    "years": 0.5,
    "risk_free_rate": 0.04,
    "volatility": 0.25,
}
MORTGAGE: Final = {
    "calculation": "solve",
    "rate": 0.005,
    "periods": 360,
    "present_value": 250_000,
    "future_value": 0,
}
#: A date inside every bound source's archive (CBO's begins 2024-02, issue #195).
BOUND_DATE: Final = dt.date(2025, 6, 30)
UNEMPLOYMENT: Final = "us.unemployment.rate"
FORBIDDEN_SERIES: Final = "fred:GDP"


def _output(name: str) -> Callable[[Mapping[str, Any]], Any]:
    def read(document: Mapping[str, Any]) -> Any:  # noqa: ANN401 - a JSON value
        return document["outputs"][name]

    return read


def _run_output(model_id: str, inputs: Mapping[str, Any], name: str) -> Any:  # noqa: ANN401
    import pyeconomics  # noqa: PLC0415 - loads on use

    return pyeconomics.run(model_id, dict(inputs)).outputs.model_dump(mode="json")[name]


def _policy() -> Any:  # noqa: ANN401 - LlmUsePolicy
    from pyeconomics.core import LlmUsePolicy  # noqa: PLC0415

    return LlmUsePolicy.ALLOWED_ONLY


def _recession_probability() -> float:
    from pyeconomics.surfaces.invoke import BindRequest, invoke  # noqa: PLC0415

    result = invoke(
        "macro.recession_probability",
        {},
        bind=BindRequest(as_of=BOUND_DATE),
        llm_use=_policy(),
    )
    probability: float = result.outputs.probability
    return probability


def _june_2025(document: Mapping[str, Any]) -> float:
    frame = document["frame"]
    value: float = dict(zip(frame["index"], frame["values"], strict=True))["2025-06-30"]
    return value


def _unemployment() -> float:
    from pyeconomics.core.canonical import canonical_json  # noqa: PLC0415
    from pyeconomics.data import api  # noqa: PLC0415
    from pyeconomics.surfaces.documents import data_document  # noqa: PLC0415

    resolved = api.get(
        UNEMPLOYMENT,
        start=dt.date(2025, 1, 1),
        end=dt.date(2025, 12, 31),
        llm_use=_policy(),
    )
    return _june_2025(json.loads(canonical_json(data_document(resolved))))


def _withheld(document: Mapping[str, Any]) -> int:
    return sum(1 for source in document["sources"] if not source["llm_permitted"])


def _withheld_count() -> int:
    from pyeconomics.data import api  # noqa: PLC0415

    policy = _policy()
    return sum(
        1
        for source in api.sources(check_keys=False)
        if not policy.permits(source.llm_use)
    )


#: The task set, discovery first.
TASKS: Final[tuple[AgentTask, ...]] = (
    AgentTask(
        id="discover_convexity",
        prompt=(
            f"Using the pyeconomics tools, find the model for bond convexity and "
            f"compute the analytical convexity of {_BOND_TEXT}."
        ),
        tools=("search_models", "describe_model", "run_model"),
        calls=(
            Call(tool="search_models", arguments={"query": "bond convexity"}),
            Call(
                tool="describe_model", arguments={"model_id": "fixed_income.convexity"}
            ),
            Call(
                tool="run_model",
                arguments={
                    "model_id": "fixed_income.convexity",
                    "inputs": {"calculation": "analytical", **BOND},
                },
            ),
        ),
        answer=_output("convexity"),
        expected=lambda: _run_output(
            "fixed_income.convexity", {"calculation": "analytical", **BOND}, "convexity"
        ),
    ),
    AgentTask(
        id="bond_duration",
        prompt=f"What is the modified duration of {_BOND_TEXT}?",
        tools=("fixed_income_duration",),
        calls=(
            Call(
                tool="fixed_income_duration",
                arguments={"calculation": "macaulay_modified", **BOND},
            ),
        ),
        answer=_output("modified_duration"),
        expected=lambda: _run_output(
            "fixed_income.duration",
            {"calculation": "macaulay_modified", **BOND},
            "modified_duration",
        ),
    ),
    AgentTask(
        id="bond_price",
        prompt=f"What is the full price, per 100 of face value, of {_BOND_TEXT}?",
        tools=("fixed_income_bond_pricing",),
        calls=(
            Call(
                tool="fixed_income_bond_pricing",
                arguments={"calculation": "price_from_yield", **BOND},
            ),
        ),
        answer=_output("full_price"),
        expected=lambda: _run_output(
            "fixed_income.bond_pricing",
            {"calculation": "price_from_yield", **BOND},
            "full_price",
        ),
    ),
    AgentTask(
        id="option_price",
        prompt=(
            "Price a European call option with the Black-Scholes-Merton model: "
            "spot 100, strike 105, six months to expiry, a 4% risk-free rate, 25% "
            "volatility and no dividends."
        ),
        tools=("derivatives_black_scholes_merton",),
        calls=(Call(tool="derivatives_black_scholes_merton", arguments=OPTION),),
        answer=_output("price"),
        expected=lambda: _run_output(
            "derivatives.black_scholes_merton", OPTION, "price"
        ),
    ),
    AgentTask(
        id="mortgage_payment",
        prompt=(
            "What is the monthly payment on a 250,000 mortgage over 30 years at 6% "
            "a year, compounded monthly? Give the payment as a positive amount."
        ),
        tools=("foundations_time_value",),
        calls=(Call(tool="foundations_time_value", arguments=MORTGAGE),),
        answer=lambda document: abs(document["outputs"]["payment"]),
        expected=lambda: abs(
            _run_output("foundations.time_value", MORTGAGE, "payment")
        ),
    ),
    AgentTask(
        id="recession_probability_bound",
        prompt=(
            "What probability of a US recession twelve months ahead did the New "
            "York Fed's yield-curve model give as of 2025-06-30, with its inputs "
            "bound to the data catalog as of that date?"
        ),
        tools=("run_model",),
        calls=(
            Call(
                tool="run_model",
                arguments={
                    "model_id": "macro.recession_probability",
                    "as_of": BOUND_DATE.isoformat(),
                },
            ),
        ),
        answer=_output("probability"),
        expected=_recession_probability,
    ),
    AgentTask(
        id="unemployment_series",
        prompt=(
            "What was the US unemployment rate for June 2025 in the data catalog, "
            "and which source must the figure be credited to?"
        ),
        tools=("get_series",),
        calls=(
            Call(
                tool="get_series",
                arguments={
                    "target": UNEMPLOYMENT,
                    "start": "2025-01-01",
                    "end": "2025-12-31",
                },
            ),
        ),
        answer=_june_2025,
        expected=_unemployment,
        mentions=("Bureau of Labor Statistics",),
    ),
    AgentTask(
        id="withheld_sources",
        prompt=(
            "How many of the data providers does this server's policy keep from "
            "reaching an AI assistant?"
        ),
        tools=("list_sources",),
        calls=(Call(tool="list_sources"),),
        answer=_withheld,
        expected=_withheld_count,
        tolerance=0.0,
    ),
    AgentTask(
        id="forbidden_series",
        prompt=("Fetch the FRED series GDP (fred:GDP) and tell me its latest value."),
        tools=("get_series",),
        calls=(Call(tool="get_series", arguments={"target": FORBIDDEN_SERIES}),),
        refusal="llm-use-forbidden",
    ),
)
