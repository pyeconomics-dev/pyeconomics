# docs/_ext/model_pages.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Generate documentation from the installed model registry.

Each model's page is its card, with a link to the model's page on the site
beside the card's id line; the site's page links back
(``web/src/lib/models.ts`` ``docsUrl``, and ``tests/docs/test_cross_links.py``
holds the two sets equal). When the syllabus crosswalks are given (the builder
hook loads them from ``syllabi/`` through ``scripts/web/syllabi.py``, the loader
the site data export uses too), the card's curriculum note is replaced by the
model's topic tags, each a title and a link to the issuing body's page (ADR-0013
decision 12).
"""

from __future__ import annotations

import importlib.util
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from pyeconomics.core.cards import CURRICULUM_NOTE, ModelCard

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import ModuleType

    from pyeconomics.core.binding import CandidateNote
    from pyeconomics.core.model import Model

#: The one loader of ``syllabi/``, beside the site data export.
SYLLABUS_LOADER = Path(__file__).resolve().parents[2] / "scripts" / "web" / "syllabi.py"

#: The web app's origin (web/src/lib/paths.ts ORIGIN).
SITE = "https://pyeconomics.dev"

#: Where the coverage matrix is published (ADR-0013 decision 12).
COVERAGE_URL = f"{SITE}/coverage/"


class Catalog(Protocol):
    """The registry operations used to generate pages."""

    def ids(self) -> tuple[str, ...]:
        """Return canonical ids."""
        ...

    def get(self, model_id: str) -> Model[Any, Any]:
        """Return a model."""
        ...


def check_pages(root: Path, model_ids: tuple[str, ...]) -> None:
    """Fail on missing, extra or misplaced pages, excluding indexes."""
    expected = {Path(*model_id.split(".")).with_suffix(".md") for model_id in model_ids}
    actual = {
        path.relative_to(root) for path in root.rglob("*.md") if path.name != "index.md"
    }
    if actual != expected or len(actual) != len(model_ids):
        message = (
            f"Model page count mismatch: expected {len(model_ids)}, got {len(actual)}"
        )
        raise ValueError(message)


def _candidates(model: Model[Any, Any]) -> dict[str, tuple[CandidateNote, ...]] | None:
    """List the sources that can fill a bound model's concepts, from metadata alone.

    Only a model that declares bindings needs the data layer, which core cannot
    import; the page of any other is built exactly as before.
    """
    if not model.spec.bindings:
        return None
    from pyeconomics.data.bindings import candidate_notes  # noqa: PLC0415

    return candidate_notes(model)


def web_url(model_id: str) -> str:
    """Return a model's page on the site: every underscore a hyphen (decision 2)."""
    return f"{SITE}/models/{model_id.replace('.', '/').replace('_', '-')}/"


def with_web_link(markdown: str, model_id: str) -> str:
    """Add the link to a model's page on the site, before the card's first section."""
    line = f"Try it in a calculator on [its web page]({web_url(model_id)})."
    return markdown.replace("\n\n## ", f"\n\n{line}\n\n## ", 1)


def syllabus_loader() -> ModuleType:
    """Return ``scripts/web/syllabi.py``, loaded by its path."""
    loaded = sys.modules.get("syllabi")
    if loaded is not None:
        return loaded
    spec = importlib.util.spec_from_file_location("syllabi", SYLLABUS_LOADER)
    if spec is None or spec.loader is None:  # pragma: no cover - a fixed file
        message = f"cannot load {SYLLABUS_LOADER}"
        raise ImportError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules["syllabi"] = module
    spec.loader.exec_module(module)
    return module


def curriculum_section(model_id: str, syllabi: Sequence[Any]) -> str:
    """Return the curriculum section's text: each syllabus's tags for the model.

    Each syllabus that maps the model gets a line naming it (its title carries
    the issuer's mark as an adjective) and one linked item per topic; a model
    no syllabus maps says so and points to the coverage matrix.
    """
    blocks: list[str] = []
    for syllabus in syllabi:
        topics = syllabus.topics_of(model_id)
        if not topics:
            continue
        items = [
            f"- [{syllabus.level(topic.level).title}: {topic.title}]({topic.url})"
            for topic in topics
        ]
        blocks.append(
            f"{syllabus.title} topic areas this model relates to, "
            f"as factual tags linking to {syllabus.issuer}:\n\n" + "\n".join(items)
        )
    if not blocks:
        return (
            "No syllabus topic is mapped to this model yet; the coverage matrix is "
            f"at <{COVERAGE_URL}>."
        )
    blocks.append(
        "pyeconomics is not affiliated with any issuing body; see {doc}`/notices`."
    )
    return "\n\n".join(blocks)


def write_pages(
    root: Path, catalog: Catalog, syllabi: Sequence[Any] = ()
) -> tuple[Path, ...]:
    """Write cards and indexes; remove stale generated Markdown only.

    ``root`` is the dedicated, ignored generation directory. Validate ids before
    any filesystem changes, so a malformed registry cannot escape it. With
    ``syllabi`` (loaded :class:`syllabi.Syllabus` objects), each card's
    curriculum note becomes the model's topic tags.
    """
    model_ids = catalog.ids()
    if len(set(model_ids)) != len(model_ids) or any(
        not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", model_id)
        or "index" in model_id.split(".")
        for model_id in model_ids
    ):
        message = "Invalid or duplicate canonical model ids"
        raise ValueError(message)
    pages: dict[Path, str] = {}
    domains: dict[str, list[str]] = defaultdict(list)
    for model_id in sorted(model_ids):
        domain, _, name = model_id.partition(".")
        model = catalog.get(model_id)
        markdown = ModelCard.from_model(model, _candidates(model)).to_markdown()
        if syllabi:
            markdown = markdown.replace(
                CURRICULUM_NOTE, curriculum_section(model_id, syllabi), 1
            )
        pages[Path(domain, *name.split(".")).with_suffix(".md")] = with_web_link(
            markdown, model_id
        )
        domains[domain].append(name.replace(".", "/"))
    for domain, names in sorted(domains.items()):
        pages[Path(domain, "index.md")] = (
            f"# {domain.replace('_', ' ').title()}\n\n"
            "```{toctree}\n:maxdepth: 1\n\n" + "\n".join(names) + "\n```\n"
        )
    pages[Path("index.md")] = (
        "# Model reference\n\n"
        "Each page comes from the registered model's specification and executes "
        "its worked example. Rates are decimals.\n\n"
        "```{toctree}\n:maxdepth: 2\n\n"
        + "\n".join(f"{domain}/index" for domain in sorted(domains))
        + "\n```\n"
    )
    root.mkdir(parents=True, exist_ok=True)
    for stale in root.rglob("*.md"):
        if stale.relative_to(root) not in pages:
            stale.unlink()
    for relative, markdown in pages.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(markdown.encode("utf-8"))
    check_pages(root, model_ids)
    return tuple(root / path for path in pages if path.name != "index.md")


def setup(app: Any) -> dict[str, object]:  # noqa: ANN401
    """Install the builder hook; pure functions do not require Sphinx."""
    from sphinx.errors import ExtensionError  # noqa: PLC0415

    from pyeconomics import registry  # noqa: PLC0415

    def generate(application: Any) -> None:  # noqa: ANN401
        try:
            registry.validate()
            write_pages(
                Path(application.srcdir) / "reference" / "models",
                registry,
                syllabus_loader().load(),
            )
        except ValueError as error:
            raise ExtensionError(str(error)) from error

    app.connect("builder-inited", generate)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}
