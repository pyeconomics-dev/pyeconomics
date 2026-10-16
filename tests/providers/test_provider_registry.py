# tests/providers/test_provider_registry.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Provider discovery: entry points, lookup, caching and the facade."""

from __future__ import annotations

import importlib.metadata
import sys
import types
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

import pytest
from stubs import Stub
from toys import ToyJson, ToyVintage

from pyeconomics.core.errors import RegistryError
from pyeconomics.data import ProviderNotFoundError, registry
from pyeconomics.data.registry import (
    ENTRY_POINT_GROUP,
    ProviderRegistry,
    discover,
    installed,
    refresh,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


class FakeMetadata:
    def __init__(self, extras: list[str]) -> None:
        self.extras = extras

    def get_all(self, name: str) -> list[str] | None:
        return self.extras if name == "Provides-Extra" else None


@dataclass
class FakeDistribution:
    name: str
    extras: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()

    @property
    def metadata(self) -> FakeMetadata:
        return FakeMetadata(list(self.extras))


@dataclass
class FakeEntryPoint:
    name: str
    value: str
    group: str = ENTRY_POINT_GROUP
    dist: Any = None


def module(monkeypatch: pytest.MonkeyPatch, name: str, **attributes: object) -> str:
    made = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(made, key, value)
    monkeypatch.setitem(sys.modules, name, made)
    return name


@pytest.fixture(autouse=True)
def _fresh_cache() -> Iterator[None]:
    refresh()
    yield
    refresh()


#: The providers this distribution registers (Phase 3 Step 6 on).
BUILT_IN = ("bea", "bls", "census", "fred")


def test_the_installed_registry_holds_the_built_in_providers_and_validates() -> None:
    assert set(BUILT_IN) <= set(registry.ids())
    registry.validate()
    assert installed() is installed()


def test_the_entry_point_group_names_each_built_in_providers_module() -> None:
    assert ENTRY_POINT_GROUP == "pyeconomics.providers"
    points = {
        point.name: point.value
        for point in importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
        if point.dist is not None and point.dist.name == "pyeconomics"
    }
    assert points == {name: f"pyeconomics.data.providers.{name}" for name in BUILT_IN}


def test_the_facade_looks_providers_up_by_id(monkeypatch: pytest.MonkeyPatch) -> None:
    name = module(
        monkeypatch, "fake_providers_ok", __all__=["ToyJson"], ToyJson=ToyJson
    )
    point = FakeEntryPoint("toys", name, dist=FakeDistribution("toypack"))
    monkeypatch.setattr(importlib.metadata, "entry_points", lambda *, group: [point])
    assert registry.ids() == ("toy_json",)
    provider = registry.get("toy_json")
    assert isinstance(provider, ToyJson)
    assert registry.get("toy_json") is provider
    assert registry.installed().infos() == (ToyJson.info,)
    assert registry.installed().provider_class("toy_json") is ToyJson


def test_an_unknown_id_names_close_matches() -> None:
    reg = ProviderRegistry.from_providers(ToyJson, ToyVintage)
    with pytest.raises(ProviderNotFoundError) as caught:
        reg.get("toy_jsno")
    assert caught.value.close_matches == ("toy_json",)
    assert "did you mean 'toy_json'" in str(caught.value)
    with pytest.raises(ProviderNotFoundError):
        reg.provider_class(7)  # type: ignore[arg-type]


def test_a_registry_lists_ids_and_infos_sorted() -> None:
    reg = ProviderRegistry.from_providers(ToyVintage, ToyJson)
    assert reg.ids() == ("toy_json", "toy_vintage")
    assert [info.id for info in reg.infos()] == ["toy_json", "toy_vintage"]
    assert [r.provider for r in reg.registrations] == [ToyVintage, ToyJson]


def test_discovery_collects_the_listed_classes_and_the_extras(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Extra(Stub):
        info = replace(Stub.info, id="needs_extra", extra="plot")

    name = module(monkeypatch, "fake_providers_extra", __all__=["Extra"], Extra=Extra)
    dist = FakeDistribution(
        "pack", extras=("plot",), requires=("plotly; extra == 'plot'",)
    )
    found = discover([FakeEntryPoint("a", name, dist=dist)])
    assert found.ids() == ("needs_extra",)
    found.validate()  # the distribution declares the extra


def test_discovery_ignores_other_groups_and_sorts_entry_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    one = module(monkeypatch, "fake_one", __all__=["ToyJson"], ToyJson=ToyJson)
    two = module(monkeypatch, "fake_two", __all__=["ToyVintage"], ToyVintage=ToyVintage)
    points = [
        FakeEntryPoint("z", two, dist=FakeDistribution("pack")),
        FakeEntryPoint("a", one, dist=FakeDistribution("pack")),
        FakeEntryPoint("m", "does_not_matter", group="pyeconomics.models"),
    ]
    assert discover(points).ids() == ("toy_json", "toy_vintage")
    assert discover([]).ids() == ()


def test_an_entry_point_without_a_distribution_is_still_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    name = module(monkeypatch, "fake_nodist", __all__=["ToyJson"], ToyJson=ToyJson)
    assert discover([FakeEntryPoint("a", name)]).ids() == ("toy_json",)


@pytest.mark.parametrize(
    ("value", "text"),
    [
        ("pkg.mod:attribute", "must name a module"),
        ("pkg.mod [extra]", "must name a module"),
        ("no_such_module_anywhere", "failed to import"),
    ],
)
def test_a_malformed_or_missing_module_is_reported(value: str, text: str) -> None:
    with pytest.raises(RegistryError, match=text):
        discover([FakeEntryPoint("bad", value, dist=FakeDistribution("pack"))])


def test_a_module_that_raises_on_import_is_reported_with_its_distribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "fake_raises", None)  # import raises ImportError
    with pytest.raises(RegistryError, match="'pack' failed to import"):
        discover([FakeEntryPoint("bad", "fake_raises", dist=FakeDistribution("pack"))])


@pytest.mark.parametrize(
    ("attributes", "text"),
    [
        ({}, "must define __all__"),
        ({"__all__": "ToyJson"}, "must define __all__"),
        ({"__all__": [7]}, "must define __all__"),
        ({"__all__": ["Missing"]}, "not a DataProvider subclass"),
        ({"__all__": ["Plain"], "Plain": object}, "not a DataProvider subclass"),
        ({"__all__": ["Inst"], "Inst": ToyJson()}, "not a DataProvider subclass"),
    ],
)
def test_a_module_must_list_provider_classes_in_all(
    monkeypatch: pytest.MonkeyPatch, attributes: dict[str, object], text: str
) -> None:
    name = module(monkeypatch, "fake_malformed", **attributes)
    with pytest.raises(RegistryError, match=text):
        discover([FakeEntryPoint("bad", name, dist=FakeDistribution("pack"))])


def test_a_duplicate_id_across_distributions_is_a_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    one = module(monkeypatch, "fake_dup_one", __all__=["ToyJson"], ToyJson=ToyJson)
    two = module(monkeypatch, "fake_dup_two", __all__=["ToyJson"], ToyJson=ToyJson)
    points = [
        FakeEntryPoint("a", one, dist=FakeDistribution("first")),
        FakeEntryPoint("b", two, dist=FakeDistribution("second")),
    ]
    with pytest.raises(RegistryError, match="conflict") as caught:
        discover(points)
    text = str(caught.value)
    assert "[duplicate-id]" in text
    assert "'first'" in text
    assert "'second'" in text


def test_a_providers_module_that_uses_the_registry_while_loading_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reenter() -> None:
        installed()

    name = module(monkeypatch, "fake_reenter", __all__=[])

    # An entry point whose import calls back into the registry.
    class Reentrant(types.ModuleType):
        def __getattr__(self, attribute: str) -> Any:
            reenter()
            raise AttributeError(attribute)

    monkeypatch.setitem(sys.modules, name, Reentrant(name))
    point = FakeEntryPoint("a", name, dist=FakeDistribution("pack"))
    monkeypatch.setattr(importlib.metadata, "entry_points", lambda *, group: [point])
    with pytest.raises(RegistryError, match="while it was being discovered"):
        installed()


def test_refresh_makes_the_next_use_discover_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = installed()
    refresh()
    assert installed() is not first
    name = module(monkeypatch, "fake_refreshed", __all__=["ToyJson"], ToyJson=ToyJson)
    point = FakeEntryPoint("a", name, dist=FakeDistribution("pack"))
    monkeypatch.setattr(importlib.metadata, "entry_points", lambda *, group: [point])
    assert "toy_json" not in registry.ids()  # still the cached registry
    refresh()
    assert registry.ids() == ("toy_json",)


def test_the_providers_ledger_is_empty_until_step_19() -> None:
    from pyeconomics.data._released import PROVIDERS  # noqa: PLC0415

    assert len(PROVIDERS) == 0
    with pytest.raises(TypeError):
        PROVIDERS["x"] = None  # type: ignore[index]
