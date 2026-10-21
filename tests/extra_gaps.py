# tests/extra_gaps.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The gap a model names where its extra's environment marker leaves a package out.

An optional extra may gate a library with an environment marker when the
library has no wheel for some interpreter yet (the Wheel rule: arch has none
for CPython 3.15). The extra is then installed without it, and a model that
needs it raises :class:`~pyeconomics.core.MissingOptionalDependencyError`
naming the extra and the package. A suite that runs every model (the golden
harness, the contract) asserts that gap there instead of failing or skipping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyeconomics.core import MissingOptionalDependencyError, run_model
from pyeconomics.core.registry import installed

if TYPE_CHECKING:
    from pyeconomics.core import Model

__all__ = ["excluded_gap"]


def excluded_gap(model: Model[Any, Any]) -> MissingOptionalDependencyError | None:
    """Return the error naming the gap, if the model's extra leaves its package out.

    Runs the model's first example. Returns ``None`` when the model runs, or
    names no extra; re-raises a missing package the extra should have installed.
    """
    extra = model.spec.extra
    if extra is None:
        return None
    try:
        run_model(model, model.spec.examples[0].inputs)
    except MissingOptionalDependencyError as error:
        registration = next(
            r for r in installed().registrations if r.model.id == model.id
        )
        if error.extra == extra and registration.provider.excludes(
            extra, error.package
        ):
            return error
        raise
    return None
