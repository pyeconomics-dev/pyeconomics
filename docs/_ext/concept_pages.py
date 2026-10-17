# docs/_ext/concept_pages.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Generate the catalog's concept pages and the sources summary, offline, at build time.

One page per catalog concept comes from the concept's own metadata
(:mod:`pyeconomics.data.catalog`) and the provider registry: the definition, the
unit, frequency and seasonal adjustment every answer guarantees, the parameters it
takes, and its candidates in fallback order for library mode and for hosted mode,
each with the provider, series key, licence class, key, extra, transforms and
whether it keeps vintages. A second page, the sources summary, lists every provider
with its licence class, key and required notice.

The build blocks the network and reads no key, so nothing here fetches anything and
nothing depends on the reader's configuration: ``candidates_by_mode`` reads provider
metadata only. Pages are written to git-ignored directories (``reference/concepts``
and ``reference/sources.md``) and a stale page is removed. A concept id becomes
``<id>.md``; ``index.md`` lists them by section.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from pyeconomics.data import CandidateInfo, Concept, SourceInfo

_ID = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z0-9]+(?:_[a-z0-9]+)*){2,3}")
_ESCAPED = re.compile(r"([\\`*_{}\[\]<>#|~$])")
_PROVIDERS = "../providers"
_DATA_GUIDE = "../../data/index.md"


class Source(Protocol):
    """What the generator needs: concepts, their candidates by mode, and providers."""

    def concepts(self) -> tuple[Concept, ...]:
        """Return every concept, sorted by id."""
        ...

    def describe(self, concept: Concept) -> dict[str, tuple[CandidateInfo, ...]]:
        """Return a concept's candidates, keyed by mode: ``library``, ``hosted``."""
        ...

    def sources(self) -> tuple[SourceInfo, ...]:
        """Return every provider's summary."""
        ...


def escape_text(value: str) -> str:
    """Escape Markdown and MyST syntax in text taken from the catalog or a provider."""
    return _ESCAPED.sub(r"\\\1", " ".join(value.split()))


def code_span(value: str) -> str:
    """Write text as a code span, which needs no escaping and holds no backtick."""
    return "`" + value.replace("`", "'") + "`"


def _cell(value: str) -> str:
    """Make text safe for a table cell: no pipe and no line break."""
    return value.replace("|", "\\|").replace("\n", " ")


def table_row(*cells: str) -> str:
    """Join cells into a Markdown table row, each cell made safe on its own."""
    return "| " + " | ".join(_cell(cell) for cell in cells) + " |"


def _candidate_row(candidate: CandidateInfo) -> str:
    if candidate.provider == "derived":
        source = "built from " + " and ".join(
            f"[{c}]({c}.md)" for c in candidate.derived_from
        )
        series = code_span(candidate.series)
        licence = "per operand"
        key = "per operand"
    else:
        source = f"[{candidate.provider}]({_PROVIDERS}/{candidate.provider}.md)"
        series = code_span(candidate.series)
        licence = code_span(candidate.licence.value) if candidate.licence else "unknown"
        if candidate.key_variable and candidate.key_required:
            key = f"{code_span(candidate.key_variable)} (required)"
        elif candidate.key_variable:
            key = f"{code_span(candidate.key_variable)} (optional)"
        else:
            key = "none"
    extra = (
        code_span(f'pip install "pyeconomics[{candidate.extra}]"')
        if candidate.extra
        else "none"
    )
    transforms = ", ".join(code_span(t) for t in candidate.transforms) or "none"
    vintages = "yes" if candidate.keeps_vintages else "no"
    note = escape_text(candidate.note) if candidate.note else ""
    return table_row(
        source,
        series,
        candidate.tier.value,
        licence,
        key,
        extra,
        vintages,
        transforms,
        note,
    )


_HEADER = (
    "| Source | Series | Tier | Licence class | Key | Extra | Vintages | "
    "Transforms | Note |\n"
    "|--------|--------|------|---------------|-----|-------|----------|"
    "------------|------|\n"
)


def _table(candidates: tuple[CandidateInfo, ...]) -> str:
    if not candidates:
        return (
            "None. Hosted mode serves only `hosted-safe` and `user-supplied` data, "
            "and this concept has no such source, so asking for it in hosted mode "
            "raises a `LicenceError` that names the classes it found.\n"
        )
    rows = "\n".join(_candidate_row(c) for c in candidates)
    return f"{_HEADER}{rows}\n"


def _glance(concept: Concept) -> str:
    kind = concept.unit_kind.value if concept.unit_kind else "mixed"
    parameters = (
        ", ".join(f"`{p.name}` (such as `{p.example}`)" for p in concept.parameters)
        or "none"
    )
    window = "yes: both `start` and `end`" if concept.needs_window else "no"
    rows = [
        ("Id", code_span(concept.id)),
        ("Shape", concept.shape.value),
        ("Unit kind", kind),
        ("Unit", escape_text(concept.unit_text or "see the definition")),
        ("Frequency", concept.frequency.value),
        ("Seasonal adjustment", concept.seasonal_adjustment.value.replace("_", " ")),
        ("Parameters", parameters),
        ("Needs a window", window),
    ]
    body = "\n".join(f"* - {name}\n  - {value}" for name, value in rows)
    return f"```{{list-table}}\n:widths: 30 70\n\n{body}\n```\n"


def render(concept: Concept, by_mode: dict[str, tuple[CandidateInfo, ...]]) -> str:
    """Return the Markdown page for one concept."""
    notes = "".join(f"- {escape_text(note)}\n" for note in concept.notes)
    notes_section = f"\n## Notes\n\n{notes}" if notes else ""
    return (
        f"# {escape_text(concept.title)}\n\n"
        f"{escape_text(concept.definition)}\n\n"
        "## At a glance\n\n"
        f"{_glance(concept)}\n"
        "## Candidates in library mode\n\n"
        "Library mode runs on your machine under your own keys. The resolver tries "
        "these in order and uses the first that can answer; it fails over only "
        "between identical definitions, and records every candidate it passed over.\n\n"
        f"{_table(by_mode['library'])}\n"
        "## Candidates in hosted mode\n\n"
        "Hosted mode serves only `hosted-safe` and `user-supplied` data, so it "
        "resolves the originator or refuses; it never falls back to a library-only "
        "aggregator.\n\n"
        f"{_table(by_mode['hosted'])}"
        f"{notes_section}\n"
        "## See also\n\n"
        f"- [Data sources and keys]({_DATA_GUIDE}) for how to fetch it and set a key.\n"
        f"- [Sources summary](../sources.md) for each provider's class and notice.\n"
    )


def hosted_mark(by_mode: dict[str, tuple[CandidateInfo, ...]]) -> str:
    return "yes" if by_mode["hosted"] else "no"


def _index(concepts: tuple[Concept, ...], source: Source) -> str:
    if not concepts:
        return "# Concept reference\n\nNo concept is defined in this build.\n"
    sections: dict[str, list[Concept]] = {}
    for concept in concepts:
        sections.setdefault(concept.section, []).append(concept)
    blocks: list[str] = []
    for section in sorted(sections):
        rows = "\n".join(
            table_row(
                f"[{escape_text(c.title)}]({c.id}.md)",
                code_span(c.id),
                c.frequency.value,
                hosted_mark(source.describe(c)),
            )
            for c in sections[section]
        )
        blocks.append(
            f"## {escape_text(section)}\n\n"
            "| Concept | Id | Frequency | Hosted mode |\n"
            "|---------|----|-----------|-------------|\n"
            f"{rows}\n"
        )
    names = "\n".join(c.id for c in concepts)
    return (
        "# Concept reference\n\n"
        "A concept is one quantity with an id, a definition and a fixed unit, "
        "frequency and seasonal adjustment. Ask for it by id and the resolver finds "
        "the right source for your mode and keys; the "
        f"[data guide]({_DATA_GUIDE}) explains how. Each page below is generated from "
        "the catalog and lists the candidate sources by mode.\n\n"
        + "\n".join(blocks)
        + f"\n```{{toctree}}\n:hidden:\n:maxdepth: 1\n\n{names}\n```\n"
    )


def render_sources(sources: tuple[SourceInfo, ...]) -> str:
    """Return the sources summary: each provider's class, key and required notice."""
    rows: list[str] = []
    for info in sources:
        if info.key_variable:
            key = f"{code_span(info.key_variable)}" + (
                "" if info.key_required else " (optional)"
            )
        else:
            key = "none"
        notice = escape_text(info.notice) if info.notice else "none"
        rows.append(
            table_row(
                f"[{escape_text(info.name)}](providers/{info.id}.md)",
                code_span(info.id),
                code_span(info.licence.value),
                "yes" if info.hosted_allowed else "no",
                key,
                code_span(info.llm_use.value),
                notice,
            )
        )
    return (
        "# Sources summary\n\n"
        "Every data provider with its licence class, whether hosted mode may serve it, "
        "its key and the notice it requires wherever its data appears. A library-only "
        "source stays on your machine; a source whose class does not allow hosted use "
        "is refused by the resolver before any request. Each provider's own page "
        "has its terms, attribution, limits and hosts. The table is generated from "
        "the provider registry; the "
        "[keys guide](../data/keys.md) says where to get each key.\n\n"
        "| Source | Id | Licence class | Hosted mode | Key | Language-model use | "
        "Required notice |\n"
        "|--------|----|---------------|-------------|-----|--------------------|"
        "-----------------|\n" + "\n".join(rows) + "\n"
    )


def check_pages(root: Path, concept_ids: tuple[str, ...]) -> None:
    """Fail on missing, extra or misplaced pages, excluding the index."""
    expected = {Path(f"{concept_id}.md") for concept_id in concept_ids}
    actual = {
        path.relative_to(root) for path in root.rglob("*.md") if path.name != "index.md"
    }
    if actual != expected or len(actual) != len(concept_ids):
        message = (
            f"Concept page count mismatch: expected {len(concept_ids)}, "
            f"got {len(actual)}"
        )
        raise ValueError(message)


def write_pages(root: Path, source: Source) -> tuple[Path, ...]:
    """Write concept pages and the index; remove stale generated Markdown only.

    ``root`` is the dedicated, ignored generation directory. Ids are validated
    before any filesystem change, so a malformed catalog cannot escape it.
    """
    concepts = source.concepts()
    concept_ids = tuple(c.id for c in concepts)
    if (
        len(set(concept_ids)) != len(concept_ids)
        or any(not _ID.fullmatch(concept_id) for concept_id in concept_ids)
        or "index" in concept_ids
    ):
        message = "Invalid or duplicate concept ids"
        raise ValueError(message)
    pages = {Path(f"{c.id}.md"): render(c, source.describe(c)) for c in concepts}
    pages[Path("index.md")] = _index(concepts, source)
    root.mkdir(parents=True, exist_ok=True)
    for stale in root.rglob("*.md"):
        if stale.relative_to(root) not in pages:
            stale.unlink()
    for relative, markdown in pages.items():
        (root / relative).write_bytes(markdown.encode("utf-8"))
    check_pages(root, concept_ids)
    return tuple(root / path for path in pages if path.name != "index.md")


def write_sources(path: Path, source: Source) -> Path:
    """Write the sources summary page."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render_sources(source.sources()).encode("utf-8"))
    return path


class _Live:
    """The installed catalog and registry, read for metadata only."""

    def __init__(self) -> None:
        from pyeconomics import data  # noqa: PLC0415

        self._data = data

    def concepts(self) -> tuple[Concept, ...]:
        return self._data.catalog.concepts()

    def describe(self, concept: Concept) -> dict[str, tuple[CandidateInfo, ...]]:
        by_mode = self._data.candidates_by_mode(concept)
        return {mode.value: found for mode, found in by_mode.items()}

    def sources(self) -> tuple[SourceInfo, ...]:
        return self._data.sources(check_keys=False)


def setup(app: Any) -> dict[str, object]:  # noqa: ANN401
    """Install the builder hook; pure functions do not require Sphinx."""
    from sphinx.errors import ExtensionError  # noqa: PLC0415

    from pyeconomics.data import registry  # noqa: PLC0415

    def generate(application: Any) -> None:  # noqa: ANN401
        try:
            registry.validate()
            live = _Live()
            reference = Path(application.srcdir) / "reference"
            write_pages(reference / "concepts", live)
            write_sources(reference / "sources.md", live)
        except ValueError as error:
            raise ExtensionError(str(error)) from error

    app.connect("builder-inited", generate)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}
