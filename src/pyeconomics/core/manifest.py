# src/pyeconomics/core/manifest.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The manifest: the provenance every result carries.

A manifest says what produced a result and fingerprints what went in and what
came out, so two runs can be compared without comparing their numbers. It holds
only facts that are the same on every run of the same inputs and the same data
in the same environment, so two such runs produce the same bytes:

- ``schema_version`` of the manifest itself;
- the model's id and version;
- the versions of pyeconomics, NumPy, SciPy, pandas and pydantic;
- for a model with a ``seed`` input, the seed and the bit generator
  (ADR-0008 decision 7; NumPy's version is among the dependencies);
- ``data_sources``, the :class:`~pyeconomics.core.provenance.DataSource`
  records of the data a bound run read, one per bound input field and sorted by
  field: provider, series, concept, vintage or real-time period, observation
  window, transforms, retrieval time, licence class, attribution, notice, terms
  page, ``llm_use``, whether the cache or offline mode served it, the fallback
  chain tried and the warning codes about the data. A run that read no data has
  none, and a record never holds a request URL, a path, a host or a key;
- ``inputs_sha256``, the SHA-256 of the canonical JSON (RFC 8785) of
  ``{"inputs": ..., "model_id": ..., "model_version": ...}``;
- ``result_sha256``, the SHA-256 of the canonical JSON of the result body:
  ``{"inputs": ..., "model_id": ..., "model_version": ..., "outputs": ...,
  "warnings": [{"code": ..., "message": ...}, ...]}``. The manifest itself is
  not part of the body, so the hash does not change with a dependency's patch
  release unless a number does.

There is no clock of the run, host name, user name, path or environment value
here, and none is ever added: a manifest travels with exports and shared files.
A data source's retrieval time is a fact about the data, recorded where it was
fetched, so a run on the same records gives the same bytes.

Examples
--------
>>> from pyeconomics.core.manifest import MANIFEST_SCHEMA_VERSION, inputs_sha256
>>> MANIFEST_SCHEMA_VERSION
2
>>> len(inputs_sha256("fixed_income.bond", 1, {"face_value": 100.0}))
64
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from importlib import metadata
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from pyeconomics.core.canonical import canonical_sha256
from pyeconomics.core.provenance import DataSource
from pyeconomics.core.random import BIT_GENERATOR, SEED_MAX, SEED_MIN

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

__all__ = [
    "DEPENDENCIES",
    "MANIFEST_SCHEMA_VERSION",
    "Manifest",
    "inputs_sha256",
    "result_sha256",
]

#: The manifest layout; it goes up whenever a field is added, removed or renamed.
#: Schema 2 (Phase 3 Step 12) fills ``data_sources`` with provenance records.
MANIFEST_SCHEMA_VERSION: Final = 2

#: The libraries whose versions a manifest records (ADR-0008 decisions 7 and 14).
DEPENDENCIES: Final = ("numpy", "pandas", "pydantic", "scipy")

_PACKAGE: Final = "pyeconomics"


@functools.cache
def _versions() -> tuple[str, tuple[tuple[str, str], ...]]:
    """Read the installed versions once: they cannot change within a process."""
    return (
        metadata.version(_PACKAGE),
        tuple((name, metadata.version(name)) for name in DEPENDENCIES),
    )


def inputs_sha256(
    model_id: str, model_version: int, inputs: Mapping[str, object]
) -> str:
    """Return the fingerprint of a model, its version and its inputs.

    ``inputs`` is the JSON form of the validated inputs, as
    ``model_dump(mode="json")`` gives it.
    """
    return canonical_sha256(
        {"inputs": inputs, "model_id": model_id, "model_version": model_version}
    )


def result_sha256(body: Mapping[str, object]) -> str:
    """Return the fingerprint of a result body (see the module docstring)."""
    return canonical_sha256(body)


def _frozen(mapping: Mapping[str, str]) -> Mapping[str, str]:
    return MappingProxyType(dict(sorted(mapping.items())))


def _sorted_sources(sources: Iterable[object]) -> tuple[DataSource, ...]:
    """Hold the records sorted by field; a field's own records keep their order.

    A derived concept's records stay in operand order (numerator first), so the
    sort is stable and looks at the field alone.
    """
    records: list[DataSource] = []
    for record in sources:
        if not isinstance(record, DataSource):
            msg = f"data_sources holds DataSource records, not {type(record).__name__}"
            raise TypeError(msg)
        records.append(record)
    return tuple(sorted(records, key=lambda record: record.field or ""))


@dataclass(frozen=True, slots=True, kw_only=True)
class Manifest:
    """What produced a result, and fingerprints of its inputs and its body.

    Build one with :meth:`create`; the runner does so for every result.
    """

    schema_version: int = MANIFEST_SCHEMA_VERSION
    model_id: str
    model_version: int
    package_version: str
    """The installed pyeconomics version."""
    dependencies: Mapping[str, str] = field(default_factory=dict)
    """The installed versions of NumPy, SciPy, pandas and pydantic."""
    seed: int | None = None
    """The seed input of a stochastic model, else ``None``."""
    bit_generator: str | None = None
    """The NumPy bit generator behind the draws, else ``None``."""
    data_sources: tuple[DataSource, ...] = ()
    """The data a bound run read, one record per bound field, sorted by field."""
    inputs_sha256: str
    result_sha256: str

    def __post_init__(self) -> None:
        """Hold the dependencies and the records read-only and sorted."""
        object.__setattr__(self, "dependencies", _frozen(self.dependencies))
        object.__setattr__(self, "data_sources", _sorted_sources(self.data_sources))

    @classmethod
    def create(
        cls,
        *,
        model_id: str,
        model_version: int,
        inputs: Mapping[str, object],
        body: Mapping[str, object],
        data_sources: Iterable[DataSource] = (),
    ) -> Manifest:
        """Build the manifest of a result from the JSON forms of its parts.

        Parameters
        ----------
        model_id, model_version
            The model that ran.
        inputs
            The validated inputs, as ``model_dump(mode="json")`` gives them.
        body
            The result body the manifest fingerprints: everything but the
            manifest.
        data_sources
            The records of the data a bound run read.
        """
        package, dependencies = _versions()
        seed = inputs.get("seed")
        has_seed = (
            isinstance(seed, int)
            and not isinstance(seed, bool)
            and SEED_MIN <= seed <= SEED_MAX
        )
        return cls(
            model_id=model_id,
            model_version=model_version,
            package_version=package,
            dependencies=dict(dependencies),
            seed=seed if has_seed else None,  # type: ignore[arg-type] # has_seed says int
            bit_generator=BIT_GENERATOR if has_seed else None,
            data_sources=tuple(data_sources),
            inputs_sha256=inputs_sha256(model_id, model_version, inputs),
            result_sha256=result_sha256(body),
        )

    def to_dict(self) -> dict[str, object]:
        """Return the manifest as JSON-ready values."""
        return {
            "schema_version": self.schema_version,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "package_version": self.package_version,
            "dependencies": dict(self.dependencies),
            "seed": self.seed,
            "bit_generator": self.bit_generator,
            "data_sources": [source.to_dict() for source in self.data_sources],
            "inputs_sha256": self.inputs_sha256,
            "result_sha256": self.result_sha256,
        }
