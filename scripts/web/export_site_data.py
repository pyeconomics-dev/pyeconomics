# scripts/web/export_site_data.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Export the data the web app builds from (ADR-0013 decision 2).

The site gains a model, a problem or a source only through this export, so
Phase 6's providers and Phase 7's models reach it with no web code. It writes
five canonical JSON files (RFC 8785, no trailing newline) into a git-ignored
directory, ``web/src/data/generated/`` by default:

- ``registry.json``: every model, from
  :func:`pyeconomics.surfaces.registry_export.write_registry`;
- ``openapi.json``: the REST API's OpenAPI document, from which the site's
  TypeScript client is generated (it needs the ``server`` extra);
- ``problems.json``: the error table, one entry per problem slug, in the
  table's order;
- ``sources.json``: every provider's licence class, terms page, attribution,
  notice and whether hosted mode serves it, sorted by id;
- ``concepts.json``: every catalog concept with its unit, frequency and
  candidates, and whether hosted mode can serve it, sorted by id.

Everything comes from metadata: the export makes no request, reads no key and
no setting, and holds no clock, host name, user name or path, so two runs on
one installation write the same bytes. A stale ``.json`` file in the output
directory is removed.

Usage, from anywhere (``npm run data`` in ``web/`` runs it):

    uv run --locked --all-extras python scripts/web/export_site_data.py [--out DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core.canonical import canonical_json

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data import CandidateInfo, Concept
    from pyeconomics.data.providers.base import ProviderInfo

#: Changes only with an incompatible change to the shape of a file this writes.
SITE_DATA_FORMAT: Final = 1

ROOT: Final = Path(__file__).resolve().parents[2]
DEFAULT_OUT: Final = ROOT / "web" / "src" / "data" / "generated"
FILES: Final = (
    "registry.json",
    "openapi.json",
    "problems.json",
    "sources.json",
    "concepts.json",
)


def problems_document() -> dict[str, Any]:
    """Describe the error table: one entry per slug, in the table's order."""
    from pyeconomics.surfaces.problems import ROWS  # noqa: PLC0415

    return {
        "format": SITE_DATA_FORMAT,
        "problems": [
            {
                "slug": row.slug,
                "title": row.title,
                "status": row.status,
                "exit_code": row.exit_code,
                "type": row.type_uri,
                "error": row.error_name,
            }
            for row in ROWS
        ],
    }


def _source(info: ProviderInfo) -> dict[str, Any]:
    from pyeconomics.data.providers.base import AuthKind  # noqa: PLC0415

    terms = info.terms
    uses_key = info.auth.kind is AuthKind.KEY
    return {
        "id": info.id,
        "name": info.name,
        "licence": terms.licence.value,
        "hosted": terms.licence.hosted_allowed,
        "terms_url": terms.terms_url,
        "terms_checked": terms.checked,
        "attribution": terms.attribution,
        "notice": terms.notice,
        "llm_use": terms.llm_use.value,
        "storage": terms.cache.value,
        "key_variable": info.key_variable,
        "key_required": uses_key and info.auth.required,
        "extra": info.extra,
    }


def sources_document() -> dict[str, Any]:
    """Describe every installed provider from its metadata, sorted by id."""
    from pyeconomics.data import registry  # noqa: PLC0415

    infos = sorted(registry.installed().infos(), key=lambda info: info.id)
    return {"format": SITE_DATA_FORMAT, "sources": [_source(i) for i in infos]}


def _candidate(candidate: CandidateInfo) -> dict[str, Any]:
    return {
        "provider": candidate.provider,
        "series": candidate.series,
        "tier": candidate.tier.value,
        "licence": None if candidate.licence is None else candidate.licence.value,
        "hosted": candidate.hosted_allowed,
        "vintages": candidate.keeps_vintages,
        "transforms": list(candidate.transforms),
        "derived_from": list(candidate.derived_from),
    }


def _concept(concept: Concept) -> dict[str, Any]:
    from pyeconomics.data import candidates_by_mode  # noqa: PLC0415
    from pyeconomics.data.modes import Mode  # noqa: PLC0415

    by_mode = candidates_by_mode(concept)
    return {
        "id": concept.id,
        "title": concept.title,
        "definition": concept.definition,
        "section": concept.section,
        "shape": concept.shape.value,
        "unit_kind": None if concept.unit_kind is None else concept.unit_kind.value,
        "unit": concept.unit_text,
        "frequency": concept.frequency.value,
        "seasonal_adjustment": concept.seasonal_adjustment.value,
        "candidates": [_candidate(c) for c in by_mode[Mode.LIBRARY]],
        "hosted": bool(by_mode[Mode.HOSTED]),
    }


def concepts_document() -> dict[str, Any]:
    """Describe every catalog concept and its candidates, sorted by id."""
    from pyeconomics.data import catalog  # noqa: PLC0415

    concepts = sorted(catalog.concepts(), key=lambda concept: concept.id)
    return {"format": SITE_DATA_FORMAT, "concepts": [_concept(c) for c in concepts]}


def _write_openapi(path: Path) -> None:
    from pyeconomics.core._optional import import_optional  # noqa: PLC0415

    import_optional("fastapi", extra="server")
    from pyeconomics.server.openapi import write_openapi  # noqa: PLC0415

    write_openapi(path)


def write_site_data(out: Path, *, figures: bool = True) -> tuple[Path, ...]:
    """Write the five site data files into ``out``; return their paths.

    Parameters
    ----------
    out
        The dedicated output directory, created if missing; any other ``.json``
        file in it is removed.
    figures
        Include each model's example figure in ``registry.json`` (the ``plot``
        extra); ``False`` writes ``null`` for every figure.

    Raises
    ------
    MissingOptionalDependencyError
        If the ``server`` extra, which ``openapi.json`` needs, is not installed.
    """
    from pyeconomics.surfaces.registry_export import write_registry  # noqa: PLC0415

    out.mkdir(parents=True, exist_ok=True)
    write_registry(out / "registry.json", figures=figures)
    _write_openapi(out / "openapi.json")
    documents = {
        "problems.json": problems_document(),
        "sources.json": sources_document(),
        "concepts.json": concepts_document(),
    }
    for name, document in documents.items():
        (out / name).write_bytes(canonical_json(document))
    for stale in out.glob("*.json"):
        if stale.name not in FILES:
            stale.unlink()
    return tuple(out / name for name in FILES)


def main(argv: Sequence[str] | None = None) -> int:
    """Write the site data; return the process exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT, help="the directory to write to"
    )
    arguments = parser.parse_args(argv)
    from pyeconomics.core.errors import MissingOptionalDependencyError  # noqa: PLC0415

    try:
        written = write_site_data(arguments.out)
    except MissingOptionalDependencyError as error:
        sys.stderr.write(
            f"export_site_data: {error}\n"
            "Run it with every extra: uv run --locked --all-extras python "
            "scripts/web/export_site_data.py\n"
        )
        return 1
    sys.stdout.write("".join(f"{path}\n" for path in written))
    return 0


if __name__ == "__main__":
    sys.exit(main())
