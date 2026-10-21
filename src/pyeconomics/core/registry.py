# src/pyeconomics/core/registry.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The model registry: discovery, lookup, aliases and validation.

A package registers models by naming a module in the ``pyeconomics.models``
entry-point group. The module's ``__all__`` lists the
:class:`~pyeconomics.core.model.Model` objects it registers, so importing the
module registers nothing by itself and a helper in the module is never mistaken
for a model.

Discovery is lazy: the first call that needs the installed registry imports the
modules, and ``import pyeconomics`` imports none of them. It reads only the
``pyeconomics.models`` group, in a fixed order, and fails closed: a duplicate id
or alias, a malformed entry point or a module that fails to import raises
:class:`~pyeconomics.core.errors.RegistryError` naming the distribution.
Importing third-party code is the point of an entry-point group, so install
only distributions you trust.

The public functions are re-exported by :mod:`pyeconomics.registry`.

Examples
--------
>>> from pyeconomics.core.registry import Registry
>>> empty = Registry.from_models()
>>> empty.ids(), empty.domains()
((), ())
>>> empty.validate(released={}) is None
True
"""

from __future__ import annotations

import difflib
import importlib
import importlib.metadata
import re
import threading
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final, Protocol

from pyeconomics.core._released import RELEASED
from pyeconomics.core._rules import RULES, Problem, check_model, check_released
from pyeconomics.core.errors import InputError, ModelNotFoundError, RegistryError
from pyeconomics.core.model import Model
from pyeconomics.core.spec import DOMAINS
from pyeconomics.core.warnings import deprecated

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from pyeconomics.core._released import Released

__all__ = [
    "ENTRY_POINT_GROUP",
    "RULES",
    "Provider",
    "Registration",
    "Registry",
    "discover",
    "installed",
    "refresh",
    "validate",
]

#: The entry-point group that registers models.
ENTRY_POINT_GROUP: Final = "pyeconomics.models"

_MODULE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*")
_REQUIREMENT_NAME = re.compile(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_REQUIREMENT_EXTRA = re.compile(r"""extra\s*==\s*['"]([^'"]+)['"]""")
_ONLY_EXTRA = re.compile(r"""\s*\(?\s*extra\s*==\s*['"][^'"]+['"]\s*\)?\s*""")
_UNKNOWN: Final = "<unknown>"


def _normalize(name: str) -> str:
    """Normalise a distribution or extra name as PEP 503 and PEP 685 do."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _is_installed(distribution: str) -> bool:
    try:
        importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


def _applies_here(requirement: str, extra: str) -> bool:
    """Return whether a requirement of ``extra`` applies to this interpreter.

    A requirement whose marker tests only the extra always applies. One whose
    marker also tests the environment (``python_full_version < '3.15'``) is
    evaluated with ``packaging``, which every package an extra installs today
    depends on; without it the requirement is taken to apply, so an extra is
    never reported installed on a guess.
    """
    _, _, marker = requirement.partition(";")
    if _ONLY_EXTRA.fullmatch(marker):
        return True
    try:
        from packaging.markers import Marker  # noqa: PLC0415 - optional, on use
    except ImportError:
        return True
    return Marker(marker).evaluate({"extra": extra})


@dataclass(frozen=True, slots=True)
class Provider:
    """The distribution that registered a model, and the extras it declares.

    A model may name an extra in its spec (``extra="econometrics"``). The
    registry checks that the model's own distribution declares it, and whether
    its packages are installed. A package whose environment marker leaves it
    out of this interpreter (a library with no wheel for it yet) is listed in
    :attr:`excluded`, not :attr:`extras`: the extra is installed without it,
    and a model that needs it names the gap.
    """

    name: str
    """The distribution name."""
    extras: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    """Each declared extra with the distributions it installs here."""
    excluded: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    """Each declared extra with the distributions its markers leave out here."""

    def declares(self, extra: str) -> bool:
        """Return whether the distribution declares ``extra`` (Provides-Extra)."""
        return _normalize(extra) in {_normalize(name) for name in self.extras}

    def installed(self, extra: str) -> bool:
        """Return whether every package ``extra`` installs here is present."""
        wanted = _normalize(extra)
        return all(
            _is_installed(package)
            for name, packages in self.extras.items()
            if _normalize(name) == wanted
            for package in packages
        )

    def excludes(self, extra: str, package: str) -> bool:
        """Return whether ``extra`` leaves ``package`` out of this interpreter."""
        wanted = _normalize(extra)
        return any(
            _normalize(name) == wanted and _normalize(package) in map(_normalize, left)
            for name, left in self.excluded.items()
        )

    @classmethod
    def from_distribution(
        cls, distribution: importlib.metadata.Distribution
    ) -> Provider:
        """Read the extras a distribution declares from its metadata."""
        extras: dict[str, list[str]] = {
            name: [] for name in distribution.metadata.get_all("Provides-Extra") or []
        }
        excluded: dict[str, list[str]] = {}
        by_normal_name = {_normalize(name): name for name in extras}
        for requirement in distribution.requires or []:
            package = _REQUIREMENT_NAME.match(requirement)
            marker = _REQUIREMENT_EXTRA.search(requirement)
            declared = (
                by_normal_name.get(_normalize(marker.group(1))) if marker else None
            )
            if package and declared is not None:
                if _applies_here(requirement, declared):
                    extras[declared].append(package.group(1))
                else:
                    excluded.setdefault(declared, []).append(package.group(1))
        return cls(
            name=distribution.name or _UNKNOWN,
            extras=MappingProxyType({k: tuple(v) for k, v in extras.items()}),
            excluded=MappingProxyType({k: tuple(v) for k, v in excluded.items()}),
        )


@dataclass(frozen=True, slots=True)
class Registration:
    """A model and the distribution that registered it."""

    model: Model[Any, Any]
    provider: Provider


class Registry:
    """An immutable set of registered models.

    Build one with :meth:`from_models` (an isolated registry, as tests do) or
    :func:`discover` (from entry points). Construction never raises on a
    conflict; it records the conflicts, which :func:`discover` and
    :meth:`validate` report, so a registry with a duplicate can be inspected.
    Where ids collide, the first registration wins lookups.
    """

    def __init__(self, registrations: Iterable[Registration]) -> None:
        self._registrations = tuple(registrations)
        self._by_id: dict[str, Registration] = {}
        self._aliases: dict[str, tuple[Registration, str]] = {}
        self._conflicts = self._index()

    def _index(self) -> tuple[Problem, ...]:
        conflicts: list[Problem] = []

        def conflict(rule: str, model_id: str, detail: str) -> None:
            conflicts.append(Problem(model_id, rule, detail))

        for registration in self._registrations:
            model_id = registration.model.id
            if model_id in self._by_id:
                first = self._by_id[model_id].provider.name
                conflict(
                    "duplicate-id",
                    model_id,
                    f"is registered by both {first!r} and "
                    f"{registration.provider.name!r}",
                )
            else:
                self._by_id[model_id] = registration
        for registration in self._registrations:
            for alias in registration.model.spec.aliases:
                owner = f"{registration.model.id!r} ({registration.provider.name!r})"
                if alias.id in self._by_id:
                    conflict(
                        "aliases",
                        registration.model.id,
                        f"alias {alias.id!r} of {owner} is also a model id "
                        f"({self._by_id[alias.id].provider.name!r})",
                    )
                elif alias.id in self._aliases:
                    other = self._aliases[alias.id][0]
                    conflict(
                        "aliases",
                        registration.model.id,
                        f"alias {alias.id!r} of {owner} is also an alias of "
                        f"{other.model.id!r} ({other.provider.name!r})",
                    )
                else:
                    self._aliases[alias.id] = (registration, alias.removed_in)
        return tuple(conflicts)

    @classmethod
    def from_models(
        cls,
        *models: Model[Any, Any],
        distribution: str = "local",
        extras: Mapping[str, Iterable[str]] | None = None,
        excluded: Mapping[str, Iterable[str]] | None = None,
    ) -> Registry:
        """Build an isolated registry from model objects.

        Parameters
        ----------
        models
            The models to register.
        distribution
            The name reported as their distribution.
        extras
            The extras that distribution declares, each with the distribution
            names it installs.
        excluded
            Distribution names an extra's environment markers leave out here.
        """
        provider = Provider(
            name=distribution,
            extras=MappingProxyType(
                {name: tuple(packages) for name, packages in (extras or {}).items()}
            ),
            excluded=MappingProxyType(
                {name: tuple(packages) for name, packages in (excluded or {}).items()}
            ),
        )
        return cls(Registration(model, provider) for model in models)

    @property
    def conflicts(self) -> tuple[Problem, ...]:
        """The duplicate ids and colliding aliases found while indexing."""
        return self._conflicts

    @property
    def registrations(self) -> tuple[Registration, ...]:
        """Every registration, in registration order."""
        return self._registrations

    def ids(self) -> tuple[str, ...]:
        """Return every canonical id, sorted."""
        return tuple(sorted(self._by_id))

    def aliases(self) -> Mapping[str, str]:
        """Return each alias with the canonical id it resolves to."""
        return MappingProxyType(
            {alias: found[0].model.id for alias, found in self._aliases.items()}
        )

    def get(self, model_id: str, *, stacklevel: int = 2) -> Model[Any, Any]:
        """Return the model with this id.

        An alias returns the canonical model and issues a
        :class:`~pyeconomics.core.warnings.PyeconomicsDeprecationWarning` that
        names the canonical id and the release that removes the alias.

        Parameters
        ----------
        model_id
            A canonical id or an alias.
        stacklevel
            The frame the warning points at, counted as
            :func:`~pyeconomics.core.warnings.deprecated` counts it: 2, the
            default, is the caller of this method.

        Raises
        ------
        ModelNotFoundError
            If no model or alias has the id; the error lists close matches.
        """
        registration = self._by_id.get(model_id)
        if registration is not None:
            return registration.model
        found = self._aliases.get(model_id)
        if found is None:
            asked: object = model_id  # a caller may pass something that is no str
            known = [*self._by_id, *self._aliases]
            matches = (
                difflib.get_close_matches(asked, known, n=3)
                if isinstance(asked, str)
                else []
            )
            raise ModelNotFoundError(str(asked), close_matches=matches)
        registration, removed_in = found
        deprecated(
            model_id,
            replacement=registration.model.id,
            removed_in=removed_in,
            stacklevel=stacklevel,
        )
        return registration.model

    def resolve(self, model_id: str, *, stacklevel: int = 2) -> Model[Any, Any]:
        """Resolve an id or alias to the canonical model; see :meth:`get`."""
        return self.get(model_id, stacklevel=stacklevel + 1)

    def models(self, domain: str | None = None) -> tuple[Model[Any, Any], ...]:
        """Return the models, sorted by id, optionally of one domain.

        Raises
        ------
        InputError
            If ``domain`` is not one of the fifteen domains.
        """
        if domain is not None and domain not in DOMAINS:
            msg = f"unknown domain {domain!r}; the domains are {', '.join(DOMAINS)}"
            raise InputError(msg)
        return tuple(
            self._by_id[model_id].model
            for model_id in sorted(self._by_id)
            if domain is None or self._by_id[model_id].model.spec.domain == domain
        )

    def domains(self) -> tuple[str, ...]:
        """Return the domains that have a registered model, in domain order."""
        present = {
            registration.model.spec.domain for registration in self._by_id.values()
        }
        return tuple(domain for domain in DOMAINS if domain in present)

    def problems(
        self, *, released: Mapping[str, Released] | None = None
    ) -> list[Problem]:
        """Return every problem with the registry; empty when it is sound."""
        problems = list(self._conflicts)
        for model_id in sorted(self._by_id):
            registration = self._by_id[model_id]
            problems += check_model(registration.model, registration.provider)
        problems += check_released(
            RELEASED if released is None else released,
            set(self._by_id),
            {alias: found[0].model.id for alias, found in self._aliases.items()},
        )
        return problems

    def validate(self, *, released: Mapping[str, Released] | None = None) -> None:
        """Check every model against the rules; see :func:`validate`."""
        problems = self.problems(released=released)
        if problems:
            lines = [str(problem) for problem in problems]
            noun = "problem" if len(lines) == 1 else "problems"
            detail = "\n".join(f"  {line}" for line in lines)
            msg = f"the model registry has {len(lines)} {noun}:\n{detail}"
            raise RegistryError(msg, problems=lines)


def validate(
    registry: Registry | None = None, *, released: Mapping[str, Released] | None = None
) -> None:
    """Check every model, or raise one error listing every problem.

    Each problem names the model and the rule it breaks. The rules are ROADMAP
    section 5's "Model quality and governance" definition of done and
    ADR-0003's permanent ids: identity, citations, units, bounds and lengths on
    every field, runnable examples, invariants, aliases, and the released-id
    ledger.

    Parameters
    ----------
    registry
        The registry to check; the installed one by default.
    released
        The released-id ledger; the shipped one by default.

    Raises
    ------
    RegistryError
        Listing every problem, each as ``<model>: [<rule>] <detail>``.
    """
    (registry or installed()).validate(released=released)


# --- discovery ---------------------------------------------------------------


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


def _load_models(entry_point: _EntryPoint, provider: Provider) -> list[Registration]:
    """Import an entry point's module and collect the models it lists."""
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
        msg = f"{where} is malformed: its module must define __all__ as the model names"
        raise RegistryError(msg)
    registrations: list[Registration] = []
    for name in names:
        candidate = getattr(module, name, None)
        if not isinstance(candidate, Model):
            msg = f"{where} is malformed: __all__ lists {name!r}, which is not a Model"
            raise RegistryError(msg)
        registrations.append(Registration(candidate, provider))
    return registrations


def discover(entry_points: Iterable[_EntryPoint] | None = None) -> Registry:
    """Import the ``pyeconomics.models`` entry points and build a registry.

    Parameters
    ----------
    entry_points
        The entry points to read; the installed distributions' by default. Only
        those in the ``pyeconomics.models`` group are loaded, sorted by name,
        distribution and module.

    Raises
    ------
    RegistryError
        For a malformed entry point, a module that fails to import, or a
        duplicate id or alias, naming the distribution.
    """
    if entry_points is None:
        entry_points = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
    selected = sorted(
        (ep for ep in entry_points if ep.group == ENTRY_POINT_GROUP),
        key=lambda ep: (ep.name, ep.dist.name if ep.dist else _UNKNOWN, ep.value),
    )
    providers: dict[str, Provider] = {}
    registrations: list[Registration] = []
    for entry_point in selected:
        dist = entry_point.dist
        key = dist.name if dist else _UNKNOWN
        if key not in providers:
            providers[key] = Provider.from_distribution(dist) if dist else Provider(key)
        registrations += _load_models(entry_point, providers[key])
    registry = Registry(registrations)
    if registry.conflicts:
        lines = [str(problem) for problem in registry.conflicts]
        detail = "\n".join(f"  {line}" for line in lines)
        msg = f"the registered models conflict:\n{detail}"
        raise RegistryError(msg, problems=lines)
    return registry


@dataclass(slots=True)
class _Cache:
    """The installed registry, built on first use."""

    registry: Registry | None = None
    loading: bool = False
    lock: threading.RLock = field(default_factory=threading.RLock)


_CACHE: Final = _Cache()


def installed() -> Registry:
    """Return the registry of installed distributions, discovering it once.

    Raises
    ------
    RegistryError
        If a models module calls the registry while it is being imported, which
        would wait on its own discovery.
    """
    with _CACHE.lock:
        if _CACHE.registry is None:
            if _CACHE.loading:
                msg = (
                    "a models module used the registry while it was being "
                    "discovered; build models at import time, and look them up later"
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
