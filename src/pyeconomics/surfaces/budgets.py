# src/pyeconomics/surfaces/budgets.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Hosted budgets and size limits, in one place (ADR-0012 decision 10).

Hosted mode bounds what a request may cost before it runs:

- :data:`HOSTED_BUDGETS`: the wall-clock seconds a run may take, by its model's
  :class:`~pyeconomics.core.spec.CostClass`. A run past its budget is stopped and
  answered with :class:`BudgetExceededError` (the ``budget-exceeded`` problem).
- :data:`HOSTED_BODY_LIMIT`: the largest request body hosted mode decodes. A
  larger one is refused with the ``input-too-large`` problem (HTTP 413) before
  it is read, pointing to local mode, whose codec takes up to
  :data:`~pyeconomics.surfaces.codec.MAX_INPUT_BYTES`.
- :data:`GET_INPUTS_LIMIT`: the longest ``?inputs=`` value of a run's ``GET``
  form, the base64url text of the inputs' canonical JSON.

Local mode has no budget: a user's own machine runs what it is asked to.

Examples
--------
>>> from pyeconomics.core import CostClass
>>> budget_for(CostClass.LIGHT), HOSTED_BODY_LIMIT, GET_INPUTS_LIMIT
(10.0, 1048576, 8192)
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
]

#: The wall-clock seconds a hosted run may take, by its model's cost class.
HOSTED_BUDGETS: Final = MappingProxyType(
    {CostClass.INSTANT: 2.0, CostClass.LIGHT: 10.0, CostClass.HEAVY: 30.0}
)
#: The largest request body hosted mode decodes, in bytes: 1 MiB.
HOSTED_BODY_LIMIT: Final = 1_048_576
#: The longest ``?inputs=`` value of a run's ``GET`` form, in characters: 8 KiB.
GET_INPUTS_LIMIT: Final = 8_192


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
        The model that ran.
    seconds
        Its budget.

    Examples
    --------
    >>> print(BudgetExceededError("risk.toy", 30.0))
    risk.toy ran past its hosted budget of 30 s; run it locally for longer runs

    """

    def __init__(self, model_id: str, seconds: float) -> None:
        super().__init__(
            f"{model_id} ran past its hosted budget of {seconds:g} s; "
            "run it locally for longer runs"
        )
        self.model_id = model_id
        self.seconds = seconds
