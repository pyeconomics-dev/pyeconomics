# src/pyeconomics/core/cards.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Model cards: one readable page per model, generated from its specification.

A :class:`ModelCard` has the sections ROADMAP section 5 asks of a model: the
title and summary, the formula (LaTeX), a variables table for the inputs and the
outputs, assumptions, limitations, the evidence status and what it means, a worked
example, references, a curriculum-mapping placeholder, the changelog and a
notice. A model that declares data bindings gains a "Data" section after the
variables: each binding's concept, transform, as-of rule and vintage policy, and,
when the caller supplies them, the licence classes and notices of the sources that
can fill each concept. It renders to MyST Markdown (:meth:`ModelCard.to_markdown`)
and in notebooks (``_repr_markdown_``). Phase 2 Step 7 builds the docs pages on it.

The worked example runs the specification's first example. A model whose extra is
not installed shows why instead of outputs.

Examples
--------
>>> from pyeconomics.core.cards import BOUND_SECTION_TITLES, SECTION_TITLES, NOTICE
>>> SECTION_TITLES[0], NOTICE
('Formula', 'Educational and informational use only; not investment advice.')
>>> BOUND_SECTION_TITLES[2]
'Data'
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core.binding import AsOf, VintagePolicy, calculations
from pyeconomics.core.context import collect_warnings
from pyeconomics.core.errors import MissingOptionalDependencyError
from pyeconomics.core.schema import input_schema, output_schema
from pyeconomics.core.spec import Evidence

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from pyeconomics.core.binding import Binding, CandidateNote
    from pyeconomics.core.model import Model

__all__ = [
    "BOUND_SECTION_TITLES",
    "CURRICULUM_NOTE",
    "EVIDENCE_MEANING",
    "NOTICE",
    "SECTION_TITLES",
    "ModelCard",
    "Variable",
    "WorkedExample",
]

#: The fixed notice that closes every card.
NOTICE: Final = "Educational and informational use only; not investment advice."

#: The curriculum-mapping section until Phase 7 supplies crosswalks.
CURRICULUM_NOTE: Final = "Not yet mapped; syllabus crosswalks arrive in Phase 7."

#: What each evidence status tells a reader (ROADMAP section 5).
EVIDENCE_MEANING: Final = {
    Evidence.STANDARD: "Textbook consensus, such as bond duration or the CAPM formula.",
    Evidence.PRACTITIONER: "A widely used rule of thumb or convention.",
    Evidence.CONTESTED: "Under active academic or policy debate.",
    Evidence.REJECTED: "Failed out of sample; kept for history and teaching.",
    Evidence.HISTORICAL: "A superseded methodology, kept for reproducibility.",
}

#: The card's section headings after the title, in order.
SECTION_TITLES: Final = (
    "Formula",
    "Variables",
    "Assumptions",
    "Limitations",
    "Evidence",
    "Worked example",
    "References",
    "Curriculum mapping",
    "Changelog",
    "Notice",
)

#: The headings of a model with data bindings: the "Data" section follows the
#: variables.
BOUND_SECTION_TITLES: Final = (*SECTION_TITLES[:2], "Data", *SECTION_TITLES[2:])

#: How a card words each as-of rule and vintage policy.
_AS_OF_WORDS: Final = {
    AsOf.LAST_ON_OR_BEFORE: "last observation on or before the date",
    AsOf.PERIOD: "the observation of the period containing the date",
    AsOf.WINDOW: "the last {window} observations on or before the date",
}
_VINTAGE_WORDS: Final = {
    VintagePolicy.REAL_TIME: "real time: as published by the date",
    VintagePolicy.LATEST: "latest: revised data",
}


@dataclass(frozen=True, slots=True)
class Variable:
    """One row of a variables table."""

    name: str
    unit: str
    """The ``x-unit`` kind, ``"text"`` or ``"flag"`` for a field with none."""
    bounds: str
    description: str


@dataclass(frozen=True, slots=True)
class WorkedExample:
    """The first example, run: its inputs and the outputs the model computed."""

    name: str
    inputs: Mapping[str, object]
    outputs: Mapping[str, object] | None
    """``None`` when the example could not run; see ``unavailable``."""
    unavailable: str | None = None
    note: str | None = None


def _number(value: float) -> str:
    return f"{value:g}"


def _bounds(node: Mapping[str, Any]) -> str:
    """Describe a schema node's numeric range and, for an array, its length."""
    parts: list[str] = []
    items = node.get("items")
    if isinstance(items, dict):
        length = [
            f"{key[:3]} {node[key]}" for key in ("minItems", "maxItems") if key in node
        ]
        if length:
            parts.append("length " + ", ".join(length))
        inner = _bounds(items)
        if inner:
            parts.append("each " + inner)
        return "; ".join(parts)
    low = node.get("minimum", node.get("exclusiveMinimum"))
    high = node.get("maximum", node.get("exclusiveMaximum"))
    if low is None and high is None:
        return f"at most {node['maxLength']} characters" if "maxLength" in node else ""
    open_low = "exclusiveMinimum" in node
    open_high = "exclusiveMaximum" in node
    return (
        f"{'(' if open_low else '['}"
        f"{_number(low) if low is not None else '-inf'}, "
        f"{_number(high) if high is not None else 'inf'}"
        f"{')' if open_high else ']'}"
    )


def _unit(node: Mapping[str, Any]) -> str:
    items = node.get("items")
    inner = _unit(items) if isinstance(items, dict) else ""
    if "x-unit" in node:
        return str(node["x-unit"])
    if inner:
        return f"{inner} (array)"
    if node.get("type") == "boolean":
        return "flag"
    return "text"


def _unwrap(node: Mapping[str, Any]) -> Mapping[str, Any]:
    """Look through an optional field's ``anyOf`` with null."""
    options = node.get("anyOf")
    if isinstance(options, list):
        rest = [option for option in options if option.get("type") != "null"]
        if len(rest) == 1:
            return {**rest[0], **{k: v for k, v in node.items() if k != "anyOf"}}
    return node


def _members(schema: Mapping[str, Any]) -> list[tuple[str | None, Mapping[str, Any]]]:
    """Return a schema's object schemas, with their calculation if it has a union."""
    definitions = schema.get("$defs", {})
    options = schema.get("oneOf")
    if not options:
        return [(None, schema)]
    found: list[tuple[str | None, Mapping[str, Any]]] = []
    for option in options:
        node = (
            definitions[option["$ref"].rpartition("/")[2]]
            if "$ref" in option
            else option
        )
        label = node.get("properties", {}).get("calculation", {}).get("const")
        found.append((label, node))
    return found


def _variables(
    schema: Mapping[str, Any],
) -> list[tuple[str | None, tuple[Variable, ...]]]:
    tables: list[tuple[str | None, tuple[Variable, ...]]] = []
    for label, node in _members(schema):
        rows = []
        for name, raw in node.get("properties", {}).items():
            prop = _unwrap(raw)
            rows.append(
                Variable(
                    name=name,
                    unit=_unit(prop),
                    bounds=_bounds(prop),
                    description=str(prop.get("description", "")),
                )
            )
        tables.append((label, tuple(rows)))
    return tables


def _cell(text: str) -> str:
    """Make text safe inside a Markdown table cell."""
    return " ".join(text.split()).replace("|", "\\|")


def _table(rows: tuple[Variable, ...]) -> list[str]:
    lines = ["| Name | Unit | Bounds | Description |", "| --- | --- | --- | --- |"]
    lines += [
        f"| `{row.name}` | {_cell(row.unit)} | {_cell(row.bounds)} | "
        f"{_cell(row.description)} |"
        for row in rows
    ]
    return lines


def _bullets(items: tuple[str, ...]) -> list[str]:
    return [f"- {' '.join(item.split())}" for item in items] or ["None."]


def _json_block(value: Mapping[str, object]) -> list[str]:
    return ["```json", json.dumps(value, indent=2, ensure_ascii=False), "```"]


def _binding_row(binding: Binding) -> str:
    """Render one binding as a table row."""
    rule = _AS_OF_WORDS.get(binding.as_of, str(binding.as_of)).format(
        window=binding.window
    )
    vintage = _VINTAGE_WORDS.get(binding.vintage, str(binding.vintage))
    transform = f"`{binding.transform}`" if binding.transform else "none"
    field = f"`{binding.field}`"
    if binding.tenors is not None:
        # A curve: its row on the date fills the values and their tenors.
        field = f"`{binding.field}`, tenors in `{binding.tenors}`"
        rule = "the curve on or before the date: its last row, a value per tenor"
    elif binding.columns:
        # A matrix: each row is a period, one value per named column.
        named = ", ".join(f"`{name}`" for name in binding.columns)
        field = f"`{binding.field}`, columns {named}"
    return (
        f"| {_cell(field)} | `{binding.concept}` | {_cell(transform)} | "
        f"{_cell(rule)} | {_cell(vintage)} |"
    )


def _candidate_line(note: CandidateNote) -> str:
    """Render one source that can fill a concept: its class, attribution, notice."""
    licence = note.licence.value if note.licence else "derived"
    pieces = [f"- **{note.provider}** ({licence})", note.attribution, note.notice]
    return " ".join(" ".join(piece.split()) for piece in pieces if piece)


def _worked_example(model: Model[Any, Any]) -> WorkedExample | None:
    if not model.spec.examples:
        return None
    example = model.spec.examples[0]
    inputs = model.validate_inputs(example.inputs)
    try:
        with collect_warnings():
            outputs = model.validate_outputs(model.compute(inputs))
    except MissingOptionalDependencyError as error:
        return WorkedExample(
            name=example.name,
            inputs=inputs.model_dump(mode="json"),
            outputs=None,
            unavailable=str(error),
            note=example.note,
        )
    return WorkedExample(
        name=example.name,
        inputs=inputs.model_dump(mode="json"),
        outputs=outputs.model_dump(mode="json"),
        note=example.note,
    )


@dataclass(frozen=True, slots=True)
class ModelCard:
    """A model's card: structured sections that render to Markdown."""

    model_id: str
    version: int
    title: str
    summary: str
    formula: tuple[str, ...]
    inputs: tuple[tuple[str | None, tuple[Variable, ...]], ...]
    """The input variables, one table per calculation (``None`` if there is one)."""
    outputs: tuple[tuple[str | None, tuple[Variable, ...]], ...]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    evidence: Evidence | None
    example: WorkedExample | None
    references: tuple[str, ...]
    """Each reference as one line: citation, then DOI or URL, then locator."""
    changelog: tuple[str, ...]
    bindings: tuple[Binding, ...] = ()
    """The model's data bindings; a non-empty tuple adds the "Data" section."""
    candidates: tuple[tuple[str, tuple[CandidateNote, ...]], ...] = ()
    """For each bound concept, the sources that can fill it, when known."""
    calculation: str | None = None
    """For a model with several calculations, the one the card's bind call names."""

    @classmethod
    def from_model(
        cls,
        model: Model[Any, Any],
        candidates: Mapping[str, Sequence[CandidateNote]] | None = None,
    ) -> ModelCard:
        """Build the card of a model, running its first example.

        Parameters
        ----------
        model
            The model.
        candidates
            For each concept a binding names, the sources that can fill it, as
            :class:`~pyeconomics.core.binding.CandidateNote` values. Core cannot
            read the catalog, so the data layer supplies them
            (``pyeconomics.data.bindings.candidate_notes``); without them the
            "Data" section lists the bindings alone.
        """
        spec = model.spec
        references = []
        for reference in spec.references:
            link = (
                f"https://doi.org/{reference.doi}"
                if reference.doi
                else reference.url or ""
            )
            where = f"({reference.locator})" if reference.locator else ""
            pieces = [reference.citation, link, where]
            references.append(" ".join(piece for piece in pieces if piece))
        return cls(
            model_id=spec.id,
            version=spec.version,
            title=spec.title,
            summary=spec.summary,
            formula=spec.formula,
            inputs=tuple(_variables(input_schema(model))),
            outputs=tuple(_variables(output_schema(model))),
            assumptions=spec.assumptions,
            limitations=spec.limitations,
            evidence=spec.evidence,
            example=_worked_example(model),
            references=tuple(references),
            changelog=tuple(
                f"Version {entry.version}: {entry.note}" for entry in spec.changelog
            ),
            bindings=spec.bindings,
            calculation=next(iter(calculations(spec.inputs)), None),
            candidates=tuple(
                (concept, tuple(notes)) for concept, notes in (candidates or {}).items()
            ),
        )

    def _variables_section(self) -> list[str]:
        lines = ["## Variables", ""]
        for heading, groups in (("Inputs", self.inputs), ("Outputs", self.outputs)):
            lines += [f"### {heading}", ""]
            for label, rows in groups:
                if label is not None:
                    lines += [f"#### Calculation `{label}`", ""]
                lines += [*_table(rows), ""]
        return lines

    def _bind_call(self) -> str:
        """Return the call that binds the model; a family names a calculation."""
        if self.calculation is None:
            return f'pyeconomics.bind("{self.model_id}")'
        return f'pyeconomics.bind("{self.model_id}", calculation="{self.calculation}")'

    def _data_section(self) -> list[str]:
        """List each profile's bindings, then the sources that can fill them."""
        lines = [
            "## Data",
            "",
            (
                "This model reads data through bindings: resolve a profile with "
                f"`{self._bind_call()}` and run the result. A value read as revised "
                "data carries the `revised_data` warning."
            ),
            "",
        ]
        for profile in dict.fromkeys(binding.profile for binding in self.bindings):
            lines += [
                f"### Profile `{profile}`",
                "",
                "| Field | Concept | Transform | As of | Vintage |",
                "| --- | --- | --- | --- | --- |",
            ]
            lines += [
                _binding_row(binding)
                for binding in self.bindings
                if binding.profile == profile
            ]
            lines.append("")
        if self.candidates:
            lines += ["### Sources", ""]
            for concept, notes in self.candidates:
                lines += [f"Concept `{concept}`:", ""]
                lines += [_candidate_line(note) for note in notes] or ["- None."]
                lines.append("")
        return lines

    def _example_section(self) -> list[str]:
        lines = ["## Worked example", ""]
        example = self.example
        if example is None:
            return [*lines, "The model declares no example.", ""]
        if example.note:
            lines += [example.note, ""]
        lines += [
            f"Example `{example.name}`. Inputs:",
            "",
            *_json_block(example.inputs),
            "",
        ]
        if example.outputs is None:
            lines += [f"Outputs are not available here: {example.unavailable}", ""]
        else:
            lines += ["Outputs:", "", *_json_block(example.outputs), ""]
        return lines

    def to_markdown(self) -> str:
        """Render the card as MyST Markdown (LF line endings, one trailing newline)."""
        meaning = EVIDENCE_MEANING.get(self.evidence) if self.evidence else None
        evidence = self.evidence.value if self.evidence else "not declared"
        lines = [
            f"# {self.title}",
            "",
            self.summary,
            "",
            f"Model `{self.model_id}`, version {self.version}.",
            "",
            "## Formula",
            "",
        ]
        for formula in self.formula:
            lines += ["$$", formula, "$$", ""]
        lines += self._variables_section()
        if self.bindings:
            lines += self._data_section()
        lines += ["## Assumptions", "", *_bullets(self.assumptions), ""]
        lines += ["## Limitations", "", *_bullets(self.limitations), ""]
        lines += [
            "## Evidence",
            "",
            f"Status: **{evidence}**." + (f" {meaning}" if meaning else ""),
            "",
        ]
        lines += self._example_section()
        lines += ["## References", "", *_bullets(self.references), ""]
        lines += ["## Curriculum mapping", "", CURRICULUM_NOTE, ""]
        lines += ["## Changelog", "", *_bullets(self.changelog), ""]
        lines += ["## Notice", "", NOTICE, ""]
        return "\n".join(lines)

    def _repr_markdown_(self) -> str:
        """Render in a notebook."""
        return self.to_markdown()

    def __str__(self) -> str:
        """Return the Markdown."""
        return self.to_markdown()
