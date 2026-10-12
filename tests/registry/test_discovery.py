# tests/registry/test_discovery.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Discovery through the ``pyeconomics.models`` entry-point group."""

from __future__ import annotations

import importlib.metadata
import subprocess  # nosec B404: runs this interpreter with fixed arguments
import sys
import threading
from dataclasses import dataclass
from email.message import Message
from types import ModuleType
from typing import TYPE_CHECKING, Any, cast

import pytest
import toy_models as tm

from pyeconomics import registry
from pyeconomics.core import Model, Provider, Registry, RegistryError, discover
from pyeconomics.core import registry as core_registry

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

GROUP = "pyeconomics.models"


@dataclass(frozen=True)
class FakeDist:
    """Stands for ``importlib.metadata.Distribution``."""

    name: str
    requires: list[str] | None = None
    provides_extra: tuple[str, ...] = ()

    @property
    def metadata(self) -> Message:
        message = Message()
        message["Name"] = self.name
        for extra in self.provides_extra:
            message["Provides-Extra"] = extra
        return message


@dataclass(frozen=True)
class FakeEntryPoint:
    """Stands for ``importlib.metadata.EntryPoint``."""

    name: str
    value: str
    group: str = GROUP
    dist: FakeDist | None = FakeDist("toy-dist")


def run_discover(entry_points: Sequence[FakeEntryPoint]) -> Registry:
    return discover(cast("Any", entry_points))


def make_module(
    monkeypatch: pytest.MonkeyPatch, name: str, *models: Model[Any, Any]
) -> str:
    """Put a module in ``sys.modules`` whose ``__all__`` lists the models."""
    module = ModuleType(name)
    for model in models:
        setattr(module, model.id.split(".")[1], model)
    module.__all__ = [model.id.split(".")[1] for model in models]  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, name, module)
    return name


@pytest.fixture(autouse=True)
def fresh_cache() -> Iterator[None]:
    registry.refresh()
    yield
    registry.refresh()


def test_discovery_registers_the_models_a_module_lists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = make_module(monkeypatch, "toy_pkg_a", tm.zero_coupon, tm.mean_return)
    found = run_discover([FakeEntryPoint("toy", module)])
    assert found.ids() == tuple(sorted([tm.mean_return.id, tm.zero_coupon.id]))
    assert found.get(tm.zero_coupon.id) is tm.zero_coupon
    assert {r.provider.name for r in found.registrations} == {"toy-dist"}


def test_only_the_names_in_all_are_registered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = make_module(monkeypatch, "toy_pkg_b", tm.zero_coupon)
    sys.modules[module].helper = lambda: 1  # type: ignore[attr-defined]
    sys.modules[module].mean_return = tm.mean_return  # type: ignore[attr-defined]
    found = run_discover([FakeEntryPoint("toy", module)])
    assert found.ids() == (tm.zero_coupon.id,)


def test_importing_a_module_registers_nothing_by_itself() -> None:
    # The toy modules are imported, but only entry points register.
    toys = {model.id for model in tm.ALL_MODELS}
    assert not toys & set(core_registry.installed().ids())


def test_the_order_is_by_name_then_distribution_not_by_arrival(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    one = make_module(monkeypatch, "toy_pkg_one", tm.zero_coupon)
    two = make_module(monkeypatch, "toy_pkg_two", tm.mean_return)
    three = make_module(monkeypatch, "toy_pkg_three", tm.time_value)
    entry_points = [
        FakeEntryPoint("b", one, dist=FakeDist("aaa")),
        FakeEntryPoint("a", two, dist=FakeDist("zzz")),
        FakeEntryPoint("a", three, dist=FakeDist("bbb")),
    ]
    forward = run_discover(entry_points)
    backward = run_discover(entry_points[::-1])
    expected = [tm.time_value.id, tm.mean_return.id, tm.zero_coupon.id]
    assert [r.model.id for r in forward.registrations] == expected
    assert [r.model.id for r in backward.registrations] == expected


def test_two_entry_points_of_one_distribution_share_a_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    one = make_module(monkeypatch, "toy_same_one", tm.zero_coupon)
    two = make_module(monkeypatch, "toy_same_two", tm.mean_return)
    dist = FakeDist("shared-dist", provides_extra=("toy",))
    found = run_discover(
        [FakeEntryPoint("a", one, dist=dist), FakeEntryPoint("b", two, dist=dist)]
    )
    first, second = found.registrations
    assert first.provider is second.provider
    assert first.provider.declares("toy")


def test_other_groups_are_never_imported() -> None:
    other = FakeEntryPoint("evil", "toy_never_imported", group="other.models")
    assert run_discover([other]).ids() == ()
    assert "toy_never_imported" not in sys.modules


def test_no_entry_points_gives_an_empty_registry() -> None:
    found = run_discover([])
    assert found.ids() == ()
    assert found.domains() == ()
    found.validate()


@pytest.mark.parametrize(
    "value",
    ["toy_pkg_a:zero_coupon", "toy_pkg_a [extra]", "not a module", "", "a..b", "1abc"],
)
def test_a_malformed_entry_point_names_the_distribution(value: str) -> None:
    with pytest.raises(RegistryError) as caught:
        run_discover([FakeEntryPoint("toy", value)])
    message = str(caught.value)
    assert "malformed" in message
    assert "'toy-dist'" in message
    assert "entry point 'toy'" in message


def test_a_module_that_cannot_be_imported_names_the_distribution() -> None:
    with pytest.raises(RegistryError) as caught:
        run_discover([FakeEntryPoint("toy", "toy_missing_module")])
    assert "failed to import" in str(caught.value)
    assert "'toy-dist'" in str(caught.value)
    assert isinstance(caught.value.__cause__, ModuleNotFoundError)


def test_a_module_that_raises_when_imported_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "toy_boom.py").write_text(
        'raise RuntimeError("boom")\n', encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(RegistryError, match=r"RuntimeError: boom") as caught:
        run_discover([FakeEntryPoint("toy", "toy_boom", dist=FakeDist("loud-dist"))])
    assert "'loud-dist'" in str(caught.value)
    assert isinstance(caught.value.__cause__, RuntimeError)


def test_an_entry_point_without_a_distribution_says_so(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RegistryError, match="<unknown>"):
        run_discover([FakeEntryPoint("toy", "toy_missing_module", dist=None)])
    module = make_module(monkeypatch, "toy_pkg_c", tm.zero_coupon)
    found = run_discover([FakeEntryPoint("toy", module, dist=None)])
    assert found.registrations[0].provider.name == "<unknown>"


def test_a_module_without_all_is_malformed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "toy_no_all", ModuleType("toy_no_all"))
    with pytest.raises(RegistryError, match="must define __all__"):
        run_discover([FakeEntryPoint("toy", "toy_no_all")])


@pytest.mark.parametrize("names", ["zero_coupon", [1, 2], None])
def test_an_all_that_is_not_a_list_of_names_is_malformed(
    monkeypatch: pytest.MonkeyPatch, names: object
) -> None:
    module = ModuleType("toy_bad_all")
    module.__all__ = names  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "toy_bad_all", module)
    with pytest.raises(RegistryError, match="must define __all__"):
        run_discover([FakeEntryPoint("toy", "toy_bad_all")])


def test_a_name_in_all_that_is_not_a_model_is_malformed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = ModuleType("toy_not_model")
    module.helper = lambda: 1  # type: ignore[attr-defined]
    module.__all__ = ["helper", "missing"]  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "toy_not_model", module)
    with pytest.raises(RegistryError, match="'helper', which is not a Model"):
        run_discover([FakeEntryPoint("toy", "toy_not_model")])
    module.__all__ = ["missing"]  # type: ignore[attr-defined]
    with pytest.raises(RegistryError, match="'missing', which is not a Model"):
        run_discover([FakeEntryPoint("toy", "toy_not_model")])


def test_a_duplicate_id_across_entry_points_names_both_distributions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    one = make_module(monkeypatch, "toy_dup_one", tm.zero_coupon)
    two = make_module(monkeypatch, "toy_dup_two", tm.zero_coupon)
    with pytest.raises(RegistryError) as caught:
        run_discover(
            [
                FakeEntryPoint("a", one, dist=FakeDist("first-dist")),
                FakeEntryPoint("b", two, dist=FakeDist("second-dist")),
            ]
        )
    message = str(caught.value)
    assert tm.zero_coupon.id in message
    assert "'first-dist'" in message
    assert "'second-dist'" in message
    assert caught.value.problems


def test_a_duplicate_alias_across_entry_points_names_both_distributions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    one = make_module(monkeypatch, "toy_alias_one", tm.variant(tm.time_value))
    other = tm.variant(tm.mean_return, aliases=("foundations.toy_tvm",))
    two = make_module(monkeypatch, "toy_alias_two", other)
    with pytest.raises(RegistryError) as caught:
        run_discover(
            [
                FakeEntryPoint("a", one, dist=FakeDist("first-dist")),
                FakeEntryPoint("b", two, dist=FakeDist("second-dist")),
            ]
        )
    message = str(caught.value)
    assert "foundations.toy_tvm" in message
    assert "'first-dist'" in message
    assert "'second-dist'" in message


def test_an_alias_that_is_another_models_id_is_a_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    one = make_module(monkeypatch, "toy_clash_one", tm.zero_coupon)
    clashing = tm.variant(tm.time_value, aliases=(tm.zero_coupon.id,))
    two = make_module(monkeypatch, "toy_clash_two", clashing)
    with pytest.raises(RegistryError, match="is also a model id"):
        run_discover(
            [FakeEntryPoint("a", one), FakeEntryPoint("b", two, dist=FakeDist("other"))]
        )


# --- the installed registry --------------------------------------------------


def test_the_installed_registry_is_discovered_once_and_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, str]] = []

    def fake_entry_points(**selection: str) -> list[FakeEntryPoint]:
        calls.append(selection)
        return []

    monkeypatch.setattr(importlib.metadata, "entry_points", fake_entry_points)
    assert calls == []
    first = core_registry.installed()
    second = core_registry.installed()
    assert first is second
    assert calls == [{"group": GROUP}]


def test_refresh_discovers_again(monkeypatch: pytest.MonkeyPatch) -> None:
    module = make_module(monkeypatch, "toy_pkg_r", tm.zero_coupon)
    found: list[list[FakeEntryPoint]] = [[]]
    monkeypatch.setattr(
        importlib.metadata, "entry_points", lambda **_selection: found[0]
    )
    assert registry.ids() == ()
    found[0] = [FakeEntryPoint("toy", module)]
    assert registry.ids() == ()  # cached
    registry.refresh()
    assert registry.ids() == (tm.zero_coupon.id,)
    assert registry.get(tm.zero_coupon.id) is tm.zero_coupon


def test_concurrent_first_use_discovers_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def fake_entry_points(**_selection: str) -> list[FakeEntryPoint]:
        calls.append(1)
        return []

    monkeypatch.setattr(importlib.metadata, "entry_points", fake_entry_points)
    seen: list[Registry] = []
    threads = [
        threading.Thread(target=lambda: seen.append(core_registry.installed()))
        for _ in range(8)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(calls) == 1
    assert len({id(r) for r in seen}) == 1


def test_the_installed_registry_holds_the_catalog_and_validates() -> None:
    assert "foundations.time_value" in registry.ids()
    assert "foundations" in registry.domains()
    assert len(registry.models()) == len(registry.ids())
    registry.validate()


def test_importing_pyeconomics_does_not_discover() -> None:
    code = (
        "import importlib.metadata as m\n"
        "def boom(**selection):\n"
        "    raise SystemExit('discovery ran at import')\n"
        "m.entry_points = boom\n"
        "import pyeconomics\n"
        "import pyeconomics.registry\n"
        "assert pyeconomics.registry is not None\n"
        "print('quiet')\n"
    )
    shown = subprocess.run(  # noqa: S603 # nosec B603: fixed arguments, no shell
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, check=False
    )
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.strip() == "quiet"


# --- the extras a distribution declares --------------------------------------


def test_extras_are_read_from_the_distribution_metadata() -> None:
    dist = FakeDist(
        "toy-dist",
        requires=[
            'toy-lib>=1.2 ; extra == "toy"',
            "toy-lib-two ; python_version >= '3.12' and extra == 'toy'",
            'unrelated ; extra == "undeclared"',
            "always-installed>=1",
        ],
        provides_extra=("toy", "empty"),
    )
    provider = Provider.from_distribution(cast("Any", dist))
    assert provider.name == "toy-dist"
    assert dict(provider.extras) == {"toy": ("toy-lib", "toy-lib-two"), "empty": ()}


def test_an_extra_name_is_compared_as_pep_685_normalizes_it() -> None:
    provider = Provider("d", {"my-extra": ()})
    assert provider.declares("my_extra")
    assert provider.declares("My.Extra")
    assert not provider.declares("other")


def test_an_extra_is_installed_when_all_its_packages_are() -> None:
    provider = Provider(
        "d",
        {
            "present": ("pydantic", "numpy"),
            "absent": ("pydantic", tm.NOT_INSTALLED),
            "empty": (),
        },
    )
    assert provider.installed("present")
    assert not provider.installed("absent")
    assert provider.installed("empty")
    assert provider.installed("undeclared")  # nothing to install


def test_the_extras_of_a_real_distribution_are_read() -> None:
    dist = importlib.metadata.distribution("pyeconomics")
    provider = Provider.from_distribution(dist)
    assert provider.name == "pyeconomics"
    assert provider.declares("econometrics")
    assert provider.installed("econometrics")  # statsmodels, in the test group


def test_a_models_module_that_uses_the_registry_at_import_fails_instead_of_hanging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = "from pyeconomics import registry\nregistry.ids()\n__all__ = []\n"
    (tmp_path / "toy_reentrant.py").write_text(source, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(
        importlib.metadata,
        "entry_points",
        lambda **_selection: [FakeEntryPoint("toy", "toy_reentrant")],
    )
    done: list[BaseException | None] = []

    def attempt() -> None:
        try:
            registry.ids()
        except RegistryError as error:
            done.append(error)

    worker = threading.Thread(target=attempt, daemon=True)
    worker.start()
    worker.join(timeout=20)
    assert not worker.is_alive(), "discovery deadlocked"
    [error] = done
    assert "while it was being discovered" in str(error)
    # The failed attempt leaves no half-built registry and no held lock.
    monkeypatch.setattr(importlib.metadata, "entry_points", lambda **_selection: [])
    registry.refresh()
    assert registry.ids() == ()


def test_extra_names_match_after_normalization() -> None:
    dist = FakeDist(
        "toy-dist",
        requires=['toy-lib>=1 ; extra == "my_extra"', 'other ; extra == "Stats"'],
        provides_extra=("my-extra", "stats"),
    )
    provider = Provider.from_distribution(cast("Any", dist))
    assert dict(provider.extras) == {"my-extra": ("toy-lib",), "stats": ("other",)}
    assert not provider.installed("my_extra")  # toy-lib is not installed
