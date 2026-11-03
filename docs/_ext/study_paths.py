# docs/_ext/study_paths.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Generate the study paths from ``syllabi/`` (ADR-0013 decision 12).

One page per syllabus level lists, topic by topic, the models the crosswalk maps
to that topic: each model's documentation page and its page on the site. The
pages hold what the crosswalk holds, the issuing body's topic names and links
through ``scripts/web/syllabi.py``, and our own pages: no wording of a syllabus
ever reaches them. A page's path carries the syllabus's neutral id, never a mark
(ROADMAP section 5 "CFA Institute marks and content").
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from model_pages import COVERAGE_URL, syllabus_loader, web_url

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

#: What an issuing body's marks require (ROADMAP section 5, docs/notices.md).
NOTICES: Final[Mapping[str, str]] = {
    "CFA Institute": (
        "CFA® and Chartered Financial Analyst® are trademarks owned by CFA "
        "Institute. pyeconomics is not affiliated with, endorsed by, or a Prep "
        "Provider of CFA Institute."
    ),
}


def notice(syllabus: Any) -> str:  # noqa: ANN401 - a syllabi.Syllabus, loaded by path
    """Return the non-affiliation notice a syllabus's pages carry."""
    issuer = syllabus.issuer
    return NOTICES.get(issuer, f"pyeconomics is not affiliated with {issuer}.")


def level_path(level: Any) -> str:  # noqa: ANN401 - a syllabi.Level, loaded by path
    """Return a level's page name: its number, never its title."""
    return f"level-{level.level}"


def _rows(
    model_ids: Sequence[str], titles: Mapping[str, str]
) -> list[str]:  # one model per row: its title, its reference page, its web page
    return [
        f"| {titles[model_id]} "
        f"| {{doc}}`{model_id} </reference/models/{model_id.replace('.', '/')}>` "
        f"| [Calculator]({web_url(model_id)}) |"
        for model_id in sorted(model_ids)
    ]


def render_level(
    syllabus: Any,  # noqa: ANN401 - a syllabi.Syllabus, loaded by path
    level: Any,  # noqa: ANN401 - a syllabi.Level, loaded by path
    titles: Mapping[str, str],
) -> str:
    """Return one level's page: per topic, the models the crosswalk maps to it."""
    models: dict[str, list[str]] = defaultdict(list)
    for model_id in syllabus.models:
        for topic in syllabus.topics_of(model_id):
            models[topic.id].append(model_id)
    lines = [
        f"# {syllabus.title}: {level.title}",
        "",
        (
            f"Our own model pages for each {level.title} topic area of the "
            f"{syllabus.title}, with each model's reference page and its calculator. "
            f"The topic names and links are {syllabus.issuer}'s; every other page "
            "here is ours, and teaches the formulas in our own words. This is a "
            "list of models, not a course, and it holds none of the syllabus's own "
            "text."
        ),
        "",
    ]
    for topic in syllabus.topics:
        if topic.level != level.level:
            continue
        lines += [
            f"## {topic.title}",
            "",
            f"[This topic area at {syllabus.issuer}]({topic.url})",
            "",
        ]
        if models[topic.id]:
            lines += [
                "| Model | Reference | Web |",
                "| --- | --- | --- |",
                *_rows(models[topic.id], titles),
            ]
        else:
            lines.append(f"No model covers this topic area yet: see <{COVERAGE_URL}>.")
        lines.append("")
    lines += [
        "---",
        "",
        notice(syllabus),
        "See {doc}`/notices`.",
        "",
    ]
    return "\n".join(lines)


def render_index(syllabi: Sequence[Any]) -> str:
    """Return the index: each syllabus and its levels, in a table of contents."""
    lines = [
        "# Study paths",
        "",
        (
            "Which of our model pages belong to which topic of a syllabus, level by "
            "level. Each page is generated from a crosswalk in the repository: the "
            "topic names and links are the issuing body's, and the pages they lead "
            f"to are ours. The whole mapping is the coverage matrix at "
            f"<{COVERAGE_URL}>."
        ),
        "",
    ]
    for syllabus in syllabi:
        lines += [
            "```{toctree}",
            ":maxdepth: 1",
            f":caption: {syllabus.title}",
            "",
            *(
                f"{level.title} <{syllabus.id}/{level_path(level)}>"
                for level in syllabus.levels
            ),
            "```",
            "",
            notice(syllabus),
            "",
        ]
    return "\n".join(lines)


def write_pages(
    root: Path, syllabi: Sequence[Any], titles: Mapping[str, str]
) -> tuple[Path, ...]:
    """Write the index and every level's page; remove stale generated Markdown.

    ``root`` is the dedicated, ignored generation directory. A syllabus's id is
    checked before any filesystem change, so it can name no other directory.
    """
    if any(not re.fullmatch(r"[a-z0-9-]+", syllabus.id) for syllabus in syllabi):
        message = "A syllabus id must be a neutral slug"
        raise ValueError(message)
    pages = {Path("index.md"): render_index(syllabi)}
    for syllabus in syllabi:
        for level in syllabus.levels:
            pages[Path(syllabus.id, f"{level_path(level)}.md")] = render_level(
                syllabus, level, titles
            )
    root.mkdir(parents=True, exist_ok=True)
    for stale in root.rglob("*.md"):
        if stale.relative_to(root) not in pages:
            stale.unlink()
    for relative, markdown in pages.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(markdown.encode("utf-8"))
    return tuple(root / path for path in pages)


def setup(app: Any) -> dict[str, object]:  # noqa: ANN401
    """Install the builder hook; pure functions do not require Sphinx."""
    from sphinx.errors import ExtensionError  # noqa: PLC0415

    from pyeconomics import registry  # noqa: PLC0415

    def generate(application: Any) -> None:  # noqa: ANN401
        titles = {
            model_id: registry.get(model_id).spec.title for model_id in registry.ids()
        }
        try:
            write_pages(
                Path(application.srcdir) / "study-paths",
                syllabus_loader().load(),
                titles,
            )
        except ValueError as error:
            raise ExtensionError(str(error)) from error

    app.connect("builder-inited", generate)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}
