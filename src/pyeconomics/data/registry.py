# src/pyeconomics/data/registry.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The provider registry: discovery, lookup and validation (ADR-0011 decision 9).

A package registers providers by naming a module in the ``pyeconomics.providers``
entry-point group. The module's ``__all__`` lists the
:class:`~pyeconomics.data.providers.base.DataProvider` subclasses it registers,
so importing it registers nothing by itself. This is the pattern of the model
registry (:mod:`pyeconomics.core.registry`), and the same caveat holds: an entry
point imports third-party code, so install only distributions you trust.

It is imported as ``pyeconomics.data.registry`` so that it never shadows
``pyeconomics.registry``, the model registry. The functions are the facade:
:func:`ids`, :func:`get`, :func:`installed`, :func:`validate` and :func:`refresh`.
Discovery is lazy and cached, and fails closed: a malformed entry point, a module
that fails to import, or a duplicate id raises
:class:`~pyeconomics.core.errors.RegistryError` naming the distribution.

:func:`validate` checks every provider against the contract's rules
(:data:`~pyeconomics.data.providers.rules.RULES`) and the released-id ledger
(:mod:`pyeconomics.data._released`), and reports every problem as
``<id>: [<rule>] <detail>``. It reads no clock; the 13-month freshness of a
provider's terms is a test.

Examples
--------
>>> from pyeconomics.data import registry
>>> {"bea", "bls", "census", "fred"} <= set(registry.ids())
True
>>> registry.validate()

"""

from __future__ import annotations

import difflib
import importlib
import importlib.metadata
import re
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final, Protocol

from pyeconomics.core.errors import RegistryError
from pyeconomics.core.registry import Provider as Distribution
from pyeconomics.data._released import CONCEPTS, PROVIDERS
from pyeconomics.data.errors import ProviderNotFoundError
from pyeconomics.data.providers.base import DataProvider, ProviderInfo
from pyeconomics.data.providers.rules import (
    RULES,
    Problem,
    check_provider,
    check_released,
    check_released_concepts,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from pyeconomics.core._released import Released

__all__ = [
    "ENTRY_POINT_GROUP",
    "RULES",
    "ProviderRegistry",
    "Registration",
    "discover",
    "get",
    "ids",
    "installed",
    "refresh",
    "validate",
]

#: The entry-point group that registers providers.
ENTRY_POINT_GROUP: Final = "pyeconomics.providers"

_MODULE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*")
_UNKNOWN: Final = "<unknown>"


@dataclass(frozen=True, slots=True)
class Registration:
    """A provider class and the distribution that registered it."""

    provider: type[DataProvider]
    distribution: Distribution


def _id_of(provider: type[DataProvider]) -> str:
    info = getattr(provider, "info", None)
    return info.id if isinstance(info, ProviderInfo) else provider.__name__


class ProviderRegistry:
    """An immutable set of registered providers.

    Build one with :meth:`from_providers` (an isolated registry, as tests do) or
    :func:`discover` (from entry points). Construction never raises on a
    conflict; it records the conflicts, which :func:`discover` and
    :meth:`validate` report. Where ids collide, the first registration wins.
    """

    def __init__(self, registrations: Iterable[Registration]) -> None:
        self._registrations = tuple(registrations)
        self._by_id: dict[str, Registration] = {}
        conflicts: list[Problem] = []
        for registration in self._registrations:
            provider_id = _id_of(registration.provider)
            if provider_id in self._by_id:
                first = self._by_id[provider_id].distribution.name
                conflicts.append(
                    Problem(
                        provider_id,
                        "duplicate-id",
                        f"is registered by both {first!r} and "
                        f"{registration.distribution.name!r}",
                    )
                )
            else:
                self._by_id[provider_id] = registration
        self._conflicts = tuple(conflicts)
        self._instances: dict[str, DataProvider] = {}
        self._lock = threading.Lock()

    @classmethod
    def from_providers(
        cls,
        *providers: type[DataProvider],
        distribution: str = "local",
        extras: Mapping[str, Iterable[str]] | None = None,
    ) -> ProviderRegistry:
        """Build an isolated registry from provider classes.

        Parameters
        ----------
        providers
            The classes to register.
        distribution
            The name reported as their distribution.
        extras
            The extras that distribution declares, each with the distribution
            names it installs.
        """
        declared = Distribution(
            name=distribution,
            extras={name: tuple(packages) for name, packages in (extras or {}).items()},
        )
        return cls(Registration(provider, declared) for provider in providers)

    @property
    def conflicts(self) -> tuple[Problem, ...]:
        """The duplicate ids found while indexing."""
        return self._conflicts

    @property
    def registrations(self) -> tuple[Registration, ...]:
        """Every registration, in registration order."""
        return self._registrations

    def ids(self) -> tuple[str, ...]:
        """Return every provider id, sorted."""
        return tuple(sorted(self._by_id))

    def provider_class(self, provider_id: str) -> type[DataProvider]:
        """Return the provider class with this id.

        Raises
        ------
        ProviderNotFoundError
            If no provider has the id; the error lists close matches.
        """
        registration = self._by_id.get(provider_id)
        if registration is None:
            asked: object = provider_id
            matches = (
                difflib.get_close_matches(asked, list(self._by_id), n=3)
                if isinstance(asked, str)
                else []
            )
            raise ProviderNotFoundError(str(asked), close_matches=matches)
        return registration.provider

    def get(self, provider_id: str) -> DataProvider:
        """Return the provider with this id, created on first use.

        A provider holds no state, so one instance serves every caller.

        Raises
        ------
        ProviderNotFoundError
            If no provider has the id.
        """
        provider_class = self.provider_class(provider_id)
        with self._lock:
            instance = self._instances.get(provider_id)
            if instance is None:
                instance = self._instances[provider_id] = provider_class()
            return instance

    def infos(self) -> tuple[ProviderInfo, ...]:
        """Return every provider's :class:`ProviderInfo`, sorted by id."""
        return tuple(
            self._by_id[provider_id].provider.info
            for provider_id in sorted(self._by_id)
        )

    def problems(
        self,
        *,
        released: Mapping[str, Released] | None = None,
        released_concepts: Mapping[str, Released] | None = None,
    ) -> list[Problem]:
        """Return every problem with the registry; empty when it is sound."""
        from pyeconomics.data import catalog  # noqa: PLC0415 - the catalog imports us

        problems = list(self._conflicts)
        for provider_id in sorted(self._by_id):
            registration = self._by_id[provider_id]
            problems += check_provider(registration.provider, registration.distribution)
        problems += check_released(
            PROVIDERS if released is None else released, set(self._by_id)
        )
        problems += check_released_concepts(
            CONCEPTS if released_concepts is None else released_concepts,
            set(catalog.ids()),
        )
        return problems

    def validate(
        self,
        *,
        released: Mapping[str, Released] | None = None,
        released_concepts: Mapping[str, Released] | None = None,
    ) -> None:
        """Check every provider against the rules; see :func:`validate`."""
        self._raise(
            self.problems(released=released, released_concepts=released_concepts)
        )

    @staticmethod
    def _raise(problems: list[Problem]) -> None:
        """Raise one error listing every problem, if there are any."""
        if problems:
            lines = [str(problem) for problem in problems]
            noun = "problem" if len(lines) == 1 else "problems"
            detail = "\n".join(f"  {line}" for line in lines)
            msg = f"the provider registry has {len(lines)} {noun}:\n{detail}"
            raise RegistryError(msg, problems=lines)


def validate(
    registry: ProviderRegistry | None = None,
    *,
    released: Mapping[str, Released] | None = None,
    released_concepts: Mapping[str, Released] | None = None,
) -> None:
    """Check every provider, or raise one error listing every problem.

    Each problem names the provider and the rule it breaks: its id and name,
    complete terms, attribution, notice, ``llm_use`` and cache policy, exact
    HTTPS hosts, published rate limits, declared capabilities with the hooks that
    implement them, authentication the redaction layer can scrub, the extra it
    needs, its platforms and size cap, and the released-id ledger. It also holds
    the catalog to the released-concept ledger (rule ``released-concept``: a
    released concept id missing from the catalog) and, for the installed
    registry, checks that every catalog candidate names a registered provider and
    a series it accepts, and that derived concepts have operands and no loop (the
    ``concept-*`` rules of :mod:`pyeconomics.data.catalog.checks`).

    Parameters
    ----------
    registry
        The registry to check; the installed one by default.
    released
        The released-provider ledger; the shipped one by default.
    released_concepts
        The released-concept ledger; the shipped one by default.

    Raises
    ------
    RegistryError
        Listing every problem, each as ``<provider>: [<rule>] <detail>``.
    """
    checked = registry or installed()
    problems = checked.problems(released=released, released_concepts=released_concepts)
    if registry is None:
        from pyeconomics.data.catalog import checks  # noqa: PLC0415 - see problems()

        problems += checks.problems(checked)
    ProviderRegistry._raise(problems)  # noqa: SLF001 - one error format for both


def ids() -> tuple[str, ...]:
    """Return the id of every installed provider, sorted."""
    return installed().ids()


def get(provider_id: str) -> DataProvider:
    """Return the installed provider with this id.

    Raises
    ------
    ProviderNotFoundError
        If no installed provider has the id.
    """
    return installed().get(provider_id)


# --- discovery -----------------------------------------------------------------


class _EntryPoint(Protocol):
    """What discovery reads from an entry point."""

    @property
    def name(self) -> str: ...
    @property
    def value(self) -> str: ...
    @property
    def group(self) -> str: ...
    @property
    def dist(self) -> importlib.metadata.Distribution | None: ...


def _describe(entry_point: _EntryPoint) -> str:
    dist = entry_point.dist.name if entry_point.dist else _UNKNOWN
    return f"entry point {entry_point.name!r} ({entry_point.value}) of {dist!r}"


def _load(entry_point: _EntryPoint, distribution: Distribution) -> list[Registration]:
    """Import an entry point's module and collect the provider classes it lists."""
    where = _describe(entry_point)
    if not _MODULE.fullmatch(entry_point.value):
        msg = f"{where} is malformed: it must name a module, not an attribute or extras"
        raise RegistryError(msg)
    try:
        module = importlib.import_module(entry_point.value)
    except Exception as error:
        msg = f"{where} failed to import: {type(error).__name__}: {error}"
        raise RegistryError(msg) from error
    names = getattr(module, "__all__", None)
    if not isinstance(names, list | tuple) or not all(
        isinstance(n, str) for n in names
    ):
        msg = (
            f"{where} is malformed: its module must define __all__ as the "
            "provider names"
        )
        raise RegistryError(msg)
    registrations: list[Registration] = []
    for name in names:
        candidate = getattr(module, name, None)
        if not (isinstance(candidate, type) and issubclass(candidate, DataProvider)):
            msg = (
                f"{where} is malformed: __all__ lists {name!r}, which is not a "
                "DataProvider subclass"
            )
            raise RegistryError(msg)
        registrations.append(Registration(candidate, distribution))
    return registrations


def discover(entry_points: Iterable[_EntryPoint] | None = None) -> ProviderRegistry:
    """Import the ``pyeconomics.providers`` entry points and build a registry.

    Parameters
    ----------
    entry_points
        The entry points to read; the installed distributions' by default. Only
        those in the ``pyeconomics.providers`` group are loaded, sorted by name,
        distribution and module.

    Raises
    ------
    RegistryError
        For a malformed entry point, a module that fails to import, or a
        duplicate id, naming the distribution.
    """
    if entry_points is None:
        entry_points = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
    selected = sorted(
        (ep for ep in entry_points if ep.group == ENTRY_POINT_GROUP),
        key=lambda ep: (ep.name, ep.dist.name if ep.dist else _UNKNOWN, ep.value),
    )
    distributions: dict[str, Distribution] = {}
    registrations: list[Registration] = []
    for entry_point in selected:
        dist = entry_point.dist
        key = dist.name if dist else _UNKNOWN
        if key not in distributions:
            distributions[key] = (
                Distribution.from_distribution(dist) if dist else Distribution(key)
            )
        registrations += _load(entry_point, distributions[key])
    registry = ProviderRegistry(registrations)
    if registry.conflicts:
        lines = [str(problem) for problem in registry.conflicts]
        detail = "\n".join(f"  {line}" for line in lines)
        msg = f"the registered providers conflict:\n{detail}"
        raise RegistryError(msg, problems=lines)
    return registry


@dataclass(slots=True)
class _Cache:
    """The installed registry, built on first use."""

    registry: ProviderRegistry | None = None
    loading: bool = False
    lock: threading.RLock = field(default_factory=threading.RLock)


_CACHE: Final = _Cache()


def installed() -> ProviderRegistry:
    """Return the registry of installed distributions, discovering it once.

    Raises
    ------
    RegistryError
        If a providers module calls the registry while it is being imported,
        which would wait on its own discovery.
    """
    with _CACHE.lock:
        if _CACHE.registry is None:
            if _CACHE.loading:
                msg = (
                    "a providers module used the registry while it was being "
                    "discovered; build providers at import time, and look them up later"
                )
                raise RegistryError(msg)
            _CACHE.loading = True
            try:
                _CACHE.registry = discover()
            finally:
                _CACHE.loading = False
        return _CACHE.registry


def refresh() -> None:
    """Forget the cached registry, so the next use discovers again (for tests)."""
    with _CACHE.lock:
        _CACHE.registry = None
