# src/pyeconomics/surfaces/budgets.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Hosted budgets and size limits, in one place (ADR-0012 decision 10).

Hosted mode bounds what a request may cost before it runs:

- :data:`HOSTED_BUDGETS`: the wall-clock seconds a run may take, by its model's
  :class:`~pyeconomics.core.spec.CostClass`. A run past its budget, an input
  above what the budget allows, is stopped and answered with
  :class:`BudgetExceededError` (the ``budget-exceeded`` problem), whose detail
  gives the command that runs it locally (:func:`local_command`).
- :data:`HOSTED_BODY_LIMIT`: the largest request body hosted mode decodes. A
  larger one is refused with the ``input-too-large`` problem (HTTP 413) before
  it is read, with the same pointer to local mode, whose codec takes up to
  :data:`~pyeconomics.surfaces.codec.MAX_INPUT_BYTES`.
- :data:`GET_INPUTS_LIMIT`: the longest ``?inputs=`` value of a run's ``GET``
  form, the base64url text of the inputs' canonical JSON.

Local mode has no budget: a user's own machine runs what it is asked to.

Examples
--------
>>> from pyeconomics.core import CostClass
>>> budget_for(CostClass.LIGHT), HOSTED_BODY_LIMIT, GET_INPUTS_LIMIT
(10.0, 1048576, 8192)
>>> local_command("risk.var")
'pyeconomics models run risk.var --inputs FILE'
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

from pyeconomics.core.errors import PyeconomicsError
from pyeconomics.core.spec import CostClass

__all__ = [
    "GET_INPUTS_LIMIT",
    "HOSTED_BODY_LIMIT",
    "HOSTED_BUDGETS",
    "BudgetExceededError",
    "budget_for",
    "local_command",
]

#: The wall-clock seconds a hosted run may take, by its model's cost class.
HOSTED_BUDGETS: Final = MappingProxyType(
    {CostClass.INSTANT: 2.0, CostClass.LIGHT: 10.0, CostClass.HEAVY: 30.0}
)
#: The largest request body hosted mode decodes, in bytes: 1 MiB.
HOSTED_BODY_LIMIT: Final = 1_048_576
#: The longest ``?inputs=`` value of a run's ``GET`` form, in characters: 8 KiB.
GET_INPUTS_LIMIT: Final = 8_192


def local_command(model_id: str) -> str:
    """Return the command that runs a model locally on inputs in a JSON file."""
    return f"pyeconomics models run {model_id} --inputs FILE"


def budget_for(cost: CostClass) -> float:
    """Return the seconds a hosted run of a model of this cost class may take.

    Raises
    ------
    ValueError
        If ``cost`` is not a cost class or one of their values.
    """
    return HOSTED_BUDGETS[CostClass(cost)]


class BudgetExceededError(PyeconomicsError):
    """A hosted run ran past its wall-clock budget and was stopped.

    Parameters
    ----------
    model_id
        The model that ran, or the series a fetch asked for.
    seconds
        Its budget.
    command
        The command that does the same locally; by default the model's run on
        inputs in a file (:func:`local_command`).

    Examples
    --------
    >>> print(BudgetExceededError("risk.toy", 30.0))
    risk.toy ran past its hosted budget of 30 s; run it locally: pyeconomics models run risk.toy --inputs FILE

    """  # noqa: E501 - doctest output lines cannot wrap

    def __init__(
        self, model_id: str, seconds: float, *, command: str | None = None
    ) -> None:
        super().__init__(
            f"{model_id} ran past its hosted budget of {seconds:g} s; run it "
            f"locally: {command or local_command(model_id)}"
        )
        self.model_id = model_id
        self.seconds = seconds
