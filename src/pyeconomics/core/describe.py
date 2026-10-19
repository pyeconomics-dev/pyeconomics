# src/pyeconomics/core/describe.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The JSON description of a model: what Phase 4's registry export is built from.

``registry.describe(id)`` returns one dictionary of JSON-ready values, which
:func:`~pyeconomics.core.canonical.canonical_json` accepts. Phase 4's
``registry.json`` is a list of these, so the keys are part of the contract:

``id``, ``version``, ``domain``, ``title``, ``summary``, ``tags``, ``formula``,
``assumptions``, ``limitations``, ``evidence``, ``cost``, ``references``,
``invariants``, ``no_invariants_reason``, ``examples`` (each with ``name``,
``note`` and ``inputs`` as the model validates them), ``charts``, ``aliases``,
``bindings`` (each with ``field``, ``concept``, ``transform``, ``as_of``,
``window``, ``vintage`` and ``profile``; empty for a model that reads no data),
``extra``, ``changelog``, ``input_schema``, ``output_schema`` and ``card``
(the card's Markdown).

Examples
--------
>>> from pyeconomics.core.describe import DESCRIPTION_KEYS
>>> DESCRIPTION_KEYS[:3]
('id', 'version', 'domain')
>>> DESCRIPTION_KEYS.index("bindings") < DESCRIPTION_KEYS.index("extra")
True
"""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core.cards import ModelCard
from pyeconomics.core.schema import input_schema, output_schema

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from pyeconomics.core.binding import CandidateNote
    from pyeconomics.core.model import Model

__all__ = ["DESCRIPTION_KEYS", "describe"]

#: The keys of every description, in order.
DESCRIPTION_KEYS: Final = (
    "id",
    "version",
    "domain",
    "title",
    "summary",
    "tags",
    "formula",
    "assumptions",
    "limitations",
    "evidence",
    "cost",
    "references",
    "invariants",
    "no_invariants_reason",
    "examples",
    "charts",
    "aliases",
    "bindings",
    "extra",
    "changelog",
    "input_schema",
    "output_schema",
    "card",
)


def describe(
    model: Model[Any, Any],
    candidates: Mapping[str, Sequence[CandidateNote]] | None = None,
) -> dict[str, Any]:
    """Describe a model as JSON-ready values; see the module docstring.

    ``candidates`` are the sources that can fill each bound concept, which the
    card's "Data" section lists; core cannot read the catalog, so the data layer
    supplies them (``pyeconomics.registry.describe`` does).
    """
    spec = model.spec
    description: dict[str, Any] = {
        "id": spec.id,
        "version": spec.version,
        "domain": spec.domain,
        "title": spec.title,
        "summary": spec.summary,
        "tags": list(spec.tags),
        "formula": list(spec.formula),
        "assumptions": list(spec.assumptions),
        "limitations": list(spec.limitations),
        "evidence": spec.evidence.value if spec.evidence else None,
        "cost": spec.cost.value if spec.cost else None,
        "references": [asdict(reference) for reference in spec.references],
        "invariants": [asdict(invariant) for invariant in spec.invariants],
        "no_invariants_reason": spec.no_invariants_reason,
        "examples": [
            {
                "name": example.name,
                "note": example.note,
                "inputs": model.validate_inputs(example.inputs).model_dump(mode="json"),
            }
            for example in spec.examples
        ],
        "charts": [
            {**asdict(chart), "kind": chart.kind.value, "y": list(chart.y)}
            for chart in spec.charts
        ],
        "aliases": [asdict(alias) for alias in spec.aliases],
        "bindings": [binding.to_dict() for binding in spec.bindings],
        "extra": spec.extra,
        "changelog": [asdict(entry) for entry in spec.changelog],
        "input_schema": input_schema(model),
        "output_schema": output_schema(model),
        "card": ModelCard.from_model(model, candidates).to_markdown(),
    }
    return description
