# scripts/web/export_site_data.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Export the data the web app builds from (ADR-0013 decision 2).

The site gains a model, a problem or a source only through this export, so
Phase 6's providers and Phase 7's models reach it with no web code. It writes
eight canonical JSON files (RFC 8785, no trailing newline) into a git-ignored
directory, ``web/src/data/generated/`` by default:

- ``registry.json``: every model, from
  :func:`pyeconomics.surfaces.registry_export.write_registry`;
- ``openapi.json``: the REST API's OpenAPI document, from which the site's
  TypeScript client is generated (it needs the ``server`` extra);
- ``problems.json``: the error table, one entry per problem slug, in the
  table's order, with what it means, what to do and, where the problem points
  to local mode, the command (``surfaces.problem_guide``), and what each exit
  code means;
- ``sources.json``: every provider's licence class, terms page, attribution,
  notice and whether hosted mode serves it, sorted by id;
- ``concepts.json``: every catalog concept with its unit, frequency and
  candidates, whether hosted mode may use one of them (``hosted``) and whether
  the hosted site serves it from the snapshot (``snapshot``: the snapshot set
  answers it, or every operand of one of its derived candidates; computed with
  :func:`~pyeconomics.data.snapshots.set.snapshot_set`, never by hand), the
  parameters it needs, whether it needs a window, and the command that reads
  it locally, sorted by id. The data explorer (``/data/``) offers a fetch only
  for a concept the snapshot serves (ADR-0013 decisions 6 and 11);
- ``surfaces.json``: where each model is reached beside its page: its REST
  route and methods (read back from ``openapi.json``), its MCP tool when it is
  a headline model, and its command line; and, for a bound model, each data
  profile's fields with whether hosted mode can serve each one (a field whose
  concept has a hosted-safe source), so a calculator offers live data only
  where the hosted site can read it (ADR-0013 decision 11). Sorted by id;
- ``syllabi.json``: every syllabus crosswalk in ``syllabi/`` (the 2027 CFA®
  Program seed first), its levels, topics and the models each topic covers,
  through ``scripts/web/syllabi.py``, which refuses an unknown model id and any
  text longer than a topic name (ADR-0013 decision 12);
- ``golden.json``: every golden case (``tests/golden/``, read with
  ``tomllib``) with its inputs as JSON and the answer the Python API gives in
  this environment: the status and the canonical bytes of the result, or of
  the problem a failed run becomes. The web parity suite
  (``web/tests/parity/``) sends each case through the calculator's own request
  builder and requires these bytes (ADR-0013 decision 8).

Everything but ``golden.json`` comes from metadata, and ``golden.json`` from
runs that read no data: the export makes no request, reads no key and no
setting, and holds no clock, host name, user name or path, so two runs on one
installation write the same bytes. A stale ``.json`` file in the output
directory is removed.

Usage, from anywhere (``npm run data`` in ``web/`` runs it):

    uv run --locked --all-extras python scripts/web/export_site_data.py [--out DIR]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core.canonical import canonical_json

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from types import ModuleType

    from pyeconomics.core.model import Model
    from pyeconomics.data import CandidateInfo, Concept
    from pyeconomics.data.providers.base import ProviderInfo

#: Changes only with an incompatible change to the shape of a file this writes.
SITE_DATA_FORMAT: Final = 1

ROOT: Final = Path(__file__).resolve().parents[2]
DEFAULT_OUT: Final = ROOT / "web" / "src" / "data" / "generated"
GOLDEN: Final = ROOT / "tests" / "golden"
FILES: Final = (
    "registry.json",
    "openapi.json",
    "problems.json",
    "sources.json",
    "concepts.json",
    "surfaces.json",
    "syllabi.json",
    "golden.json",
)


def problems_document() -> dict[str, Any]:
    """Describe the error table: one entry per slug, in the table's order."""
    from pyeconomics.surfaces.budgets import local_command  # noqa: PLC0415
    from pyeconomics.surfaces.problem_guide import EXIT_CODES, GUIDES  # noqa: PLC0415
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
                "meaning": GUIDES[row.slug].meaning,
                "action": GUIDES[row.slug].action,
                "local_command": (
                    (GUIDES[row.slug].command or local_command("<model-id>"))
                    if GUIDES[row.slug].local
                    else None
                ),
            }
            for row in ROWS
        ],
        "exit_codes": {str(code): meaning for code, meaning in EXIT_CODES.items()},
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


def _concept(concept: Concept, served: frozenset[str]) -> dict[str, Any]:
    from pyeconomics.data import candidates_by_mode  # noqa: PLC0415
    from pyeconomics.data.modes import Mode  # noqa: PLC0415
    from pyeconomics.surfaces.budgets import local_data_command  # noqa: PLC0415

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
        "snapshot": concept.id in served,
        "parameters": [
            {"name": parameter.name, "example": parameter.example}
            for parameter in concept.parameters
        ],
        "needs_window": concept.needs_window,
        "local_command": local_data_command(concept.id),
    }


def snapshot_concepts() -> frozenset[str]:
    """Return the concepts the hosted snapshot serves.

    A concept is served when a series the snapshot set keeps answers it
    (:attr:`~pyeconomics.data.snapshots.set.Entry.concepts`), or when every
    operand of one of its derived candidates is served.
    """
    from pyeconomics.data import catalog  # noqa: PLC0415
    from pyeconomics.data.catalog.definitions import Derived  # noqa: PLC0415
    from pyeconomics.data.snapshots.set import snapshot_set  # noqa: PLC0415

    served = {concept for entry in snapshot_set().entries for concept in entry.concepts}
    derived = [
        (concept.id, candidate)
        for concept in catalog.concepts()
        for candidate in concept.candidates
        if isinstance(candidate, Derived)
    ]
    grew = True
    while grew:
        grew = False
        for concept_id, candidate in derived:
            if concept_id not in served and all(
                operand.concept in served for operand in candidate.operands
            ):
                served.add(concept_id)
                grew = True
    return frozenset(served)


def concepts_document() -> dict[str, Any]:
    """Describe every catalog concept and its candidates, sorted by id."""
    from pyeconomics.data import catalog  # noqa: PLC0415

    served = snapshot_concepts()
    concepts = sorted(catalog.concepts(), key=lambda concept: concept.id)
    return {
        "format": SITE_DATA_FORMAT,
        "concepts": [_concept(c, served) for c in concepts],
    }


def hosted_profiles(model: Model[Any, Any]) -> list[dict[str, Any]]:
    """Each data profile of a model, in declared order, with its bound fields.

    A field is ``hosted`` when hosted mode can read its concept: one of the
    concept's candidates is usable there. A profile is ``hosted`` when every
    one of its fields is.
    """
    from pyeconomics.data import candidates_by_mode  # noqa: PLC0415
    from pyeconomics.data.modes import Mode  # noqa: PLC0415

    profiles: dict[str, list[dict[str, Any]]] = {}
    for binding in model.spec.bindings:
        hosted = bool(candidates_by_mode(binding.concept)[Mode.HOSTED])
        profiles.setdefault(binding.profile, []).append(
            {"field": binding.field, "hosted": hosted}
        )
    return [
        {
            "profile": profile,
            "hosted": all(field["hosted"] for field in fields),
            "fields": fields,
        }
        for profile, fields in profiles.items()
    ]


def surfaces_document(openapi: Mapping[str, Any]) -> dict[str, Any]:
    """Describe where each model is reached beside its page, sorted by id.

    Raises
    ------
    RegistryError
        If the OpenAPI document has no run route for a model.
    """
    from pyeconomics import registry  # noqa: PLC0415
    from pyeconomics.core.errors import RegistryError  # noqa: PLC0415
    from pyeconomics.mcp.headline import HEADLINE  # noqa: PLC0415
    from pyeconomics.mcp.tools import tool_name  # noqa: PLC0415

    models = []
    for model_id in sorted(registry.ids()):
        route = f"/v1/models/{model_id}/run"
        operations = openapi["paths"].get(route)
        if not operations:
            msg = f"{model_id}: openapi.json has no run route {route}"
            raise RegistryError(msg, problems=(msg,))
        models.append(
            {
                "id": model_id,
                "rest": route,
                "methods": sorted(method.upper() for method in operations),
                "mcp_tool": tool_name(model_id) if model_id in HEADLINE else None,
                "cli": f"pyeconomics models run {model_id}",
                "profiles": hosted_profiles(registry.get(model_id)),
            }
        )
    return {"format": SITE_DATA_FORMAT, "models": models}


def syllabus_loader() -> ModuleType:
    """Return ``scripts/web/syllabi.py``, the one loader of ``syllabi/``.

    It is loaded by its path, so this script works however it is started.
    """
    loaded = sys.modules.get("syllabi")
    if loaded is not None:
        return loaded
    path = Path(__file__).resolve().with_name("syllabi.py")
    spec = importlib.util.spec_from_file_location("syllabi", path)
    if spec is None or spec.loader is None:  # pragma: no cover - a fixed file
        msg = f"cannot load {path}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules["syllabi"] = module
    spec.loader.exec_module(module)
    return module


def syllabi_document() -> dict[str, Any]:
    """Describe every syllabus crosswalk, sorted by id.

    Raises
    ------
    ValueError
        A ``SyllabusError`` naming every problem with the files in ``syllabi/``.
    """
    syllabi = syllabus_loader().load()
    return {
        "format": SITE_DATA_FORMAT,
        "syllabi": [syllabus.to_json() for syllabus in syllabi],
    }


def _answer(model_id: str, inputs: Mapping[str, Any]) -> tuple[int, str]:
    """Return the Python API's answer to a run: its status and canonical text."""
    import pyeconomics  # noqa: PLC0415
    from pyeconomics.surfaces.problems import problem_for  # noqa: PLC0415

    try:
        result = pyeconomics.run(model_id, dict(inputs))
    except Exception as error:  # noqa: BLE001 - every failure is an answer
        made = problem_for(error)
        return made.status, made.to_json().decode("utf-8")
    return 200, result.to_json()


def golden_document(golden: Path = GOLDEN) -> dict[str, Any]:
    """Every golden case with its JSON inputs and the Python API's answer.

    The cases are in the order of their files' paths, then of each file; the
    inputs are the case's TOML values as JSON (a date as its ISO text), which
    is what a calculator posts.
    """
    cases = []
    for path in sorted(golden.rglob("*.toml")):
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        model_id = str(data["model"])
        for case in data["cases"]:
            inputs = dict(case["inputs"])
            status, body = _answer(model_id, inputs)
            cases.append(
                {
                    "model": model_id,
                    "case": str(case["id"]),
                    "inputs": json.loads(canonical_json(inputs)),
                    "status": status,
                    "body": body,
                }
            )
    return {"format": SITE_DATA_FORMAT, "cases": cases}


def _write_openapi(path: Path) -> None:
    from pyeconomics.core._optional import import_optional  # noqa: PLC0415

    import_optional("fastapi", extra="server")
    from pyeconomics.server.openapi import write_openapi  # noqa: PLC0415

    write_openapi(path)


def write_site_data(
    out: Path, *, figures: bool = True, golden: Path = GOLDEN
) -> tuple[Path, ...]:
    """Write the eight site data files into ``out``; return their paths.

    Parameters
    ----------
    out
        The dedicated output directory, created if missing; any other ``.json``
        file in it is removed.
    figures
        Include each model's example figure in ``registry.json`` (the ``plot``
        extra); ``False`` writes ``null`` for every figure.
    golden
        The golden files ``golden.json`` is written from.

    Raises
    ------
    MissingOptionalDependencyError
        If the ``server`` extra, which ``openapi.json`` needs, is not installed.
    """
    from pyeconomics.surfaces.registry_export import write_registry  # noqa: PLC0415

    out.mkdir(parents=True, exist_ok=True)
    write_registry(out / "registry.json", figures=figures)
    _write_openapi(out / "openapi.json")
    openapi = json.loads((out / "openapi.json").read_bytes())
    documents = {
        "problems.json": problems_document(),
        "sources.json": sources_document(),
        "concepts.json": concepts_document(),
        "surfaces.json": surfaces_document(openapi),
        "syllabi.json": syllabi_document(),
        "golden.json": golden_document(golden),
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
