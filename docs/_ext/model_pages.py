# docs/_ext/model_pages.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Generate documentation from the installed model registry."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from pyeconomics.core.cards import ModelCard

if TYPE_CHECKING:
    from pyeconomics.core.binding import CandidateNote
    from pyeconomics.core.model import Model


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


def write_pages(root: Path, catalog: Catalog) -> tuple[Path, ...]:
    """Write cards and indexes; remove stale generated Markdown only.

    ``root`` is the dedicated, ignored generation directory. Validate ids before
    any filesystem changes, so a malformed registry cannot escape it.
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
        pages[Path(domain, *name.split(".")).with_suffix(".md")] = ModelCard.from_model(
            model, _candidates(model)
        ).to_markdown()
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
            write_pages(Path(application.srcdir) / "reference" / "models", registry)
        except ValueError as error:
            raise ExtensionError(str(error)) from error

    app.connect("builder-inited", generate)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}
