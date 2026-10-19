# tests/repo/test_smoke.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``scripts/smoke.py``: its checks pass, and it refuses a source checkout.

CI runs the script itself against the installed wheel (ci.yml's ``package``
and ``pyodide`` jobs). The test suite imports pyeconomics from the checkout's
``src/`` tree, so here the script must refuse to run, while each of its
checks still passes against this package.
"""

from __future__ import annotations

import importlib.util
import itertools
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import toy_models as tm

import pyeconomics
import pyeconomics.core
from pyeconomics.core import (
    MissingOptionalDependencyError,
    Model,
    Registry,
    RegistryError,
)
from pyeconomics.core import registry as core_registry

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "smoke.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("smoke_script", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


smoke = load_script()


def test_every_check_passes_against_this_package() -> None:
    for name, check in smoke.CHECKS:
        assert isinstance(check(pyeconomics), str), name


def test_it_refuses_the_checkout_src_tree(capsys: pytest.CaptureFixture[str]) -> None:
    assert smoke.inside_a_checkout(pyeconomics.__file__)
    assert smoke.main([]) == 2
    assert "refused" in capsys.readouterr().err


def test_an_installed_package_is_not_a_checkout(tmp_path: Path) -> None:
    module = tmp_path / "site-packages" / "pyeconomics" / "__init__.py"
    module.parent.mkdir(parents=True)
    module.touch()
    assert not smoke.inside_a_checkout(str(module))
    # A src/ directory without a pyproject.toml beside it is not a checkout.
    other = tmp_path / "src" / "pyeconomics" / "__init__.py"
    other.parent.mkdir(parents=True)
    other.touch()
    assert not smoke.inside_a_checkout(str(other))


def test_it_reports_each_check_and_fails_on_one(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def broken(_: ModuleType) -> str:
        msg = "deliberately broken"
        raise AssertionError(msg)

    monkeypatch.setattr(smoke, "inside_a_checkout", lambda _: False)
    monkeypatch.setattr(smoke, "CHECKS", (*smoke.CHECKS, ("broken", broken)))
    assert smoke.main([]) == 1
    out = capsys.readouterr().out
    assert "ok    version:" in out
    assert "ok    compounding: 6% compounded monthly is 6.1678%" in out
    assert "FAIL  broken: AssertionError: deliberately broken" in out


def test_it_passes_when_every_check_does(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(smoke, "inside_a_checkout", lambda _: False)
    assert smoke.main([]) == 0
    assert "FAIL" not in capsys.readouterr().out


# --- the model checks (Phase 2 Step 4) -------------------------------------------
# These run against isolated toy registries, installed as the registry for the
# duration of a test, so each check meets a model built to break it.


@pytest.fixture
def toy_installed(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    def install(*models: Model[Any, Any]) -> None:
        registry = Registry.from_models(
            *(models or tm.ALL_MODELS), distribution="toy-dist", extras=tm.EXTRAS
        )
        monkeypatch.setattr(core_registry._CACHE, "registry", registry)  # noqa: SLF001
        monkeypatch.setattr(core_registry, "RELEASED", {})

    return install


def test_the_models_check_covers_one_model_per_domain(
    toy_installed: Callable[..., None], capsys: pytest.CaptureFixture[str]
) -> None:
    toy_installed()
    detail = smoke.check_models(pyeconomics)
    assert detail == "registry valid; 3 domain(s) covered"
    out = capsys.readouterr().out
    # The first model of each domain: econometrics, fixed_income, foundations.
    assert "econometrics.toy_extra: raises, naming pyeconomics[toy]" in out
    assert "fixed_income.toy_zero_coupon: 1 example(s) reproduce" in out
    assert "foundations.toy_mean_return: 1 example(s) reproduce" in out
    assert "foundations.toy_time_value" not in out


def test_all_runs_every_example_of_every_model(
    toy_installed: Callable[..., None], capsys: pytest.CaptureFixture[str]
) -> None:
    toy_installed()
    smoke.check_models(pyeconomics, run_all=True)
    out = capsys.readouterr().out
    assert "foundations.toy_time_value: 2 example(s) reproduce" in out
    assert "foundations.toy_mean_return: 1 example(s) reproduce" in out


def test_min_domains_fails_when_too_few_are_covered(
    toy_installed: Callable[..., None],
) -> None:
    toy_installed()
    assert smoke.check_models(pyeconomics, min_domains=3).endswith(
        "3 domain(s) covered"
    )
    with pytest.raises(AssertionError, match=r"3 domain\(s\) were covered, not the 11"):
        smoke.check_models(pyeconomics, min_domains=11)


def test_an_empty_registry_covers_no_domain_and_fails_any_minimum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    empty = Registry.from_models(distribution="toy-dist")
    monkeypatch.setattr(core_registry._CACHE, "registry", empty)  # noqa: SLF001
    monkeypatch.setattr(core_registry, "RELEASED", {})
    assert smoke.check_models(pyeconomics) == "registry valid; 0 domain(s) covered"
    with pytest.raises(AssertionError, match=r"0 domain.*none"):
        smoke.check_models(pyeconomics, min_domains=1)


def test_extras_fails_unless_every_extra_model_can_run(
    toy_installed: Callable[..., None],
) -> None:
    toy_installed()
    with pytest.raises(AssertionError, match="needs the 'toy' extra"):
        smoke.check_models(pyeconomics, extras=True)
    toy_installed(tm.zero_coupon)
    smoke.check_models(pyeconomics, extras=True)  # no model names an extra


def test_a_model_with_an_installed_extra_runs_and_must_return_outputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs = tm.variant(tm.zero_coupon, id="econometrics.toy_runs", extra="toy")
    registry = Registry.from_models(
        runs, distribution="toy-dist", extras={"toy": ("pytest",)}
    )
    monkeypatch.setattr(core_registry._CACHE, "registry", registry)  # noqa: SLF001
    monkeypatch.setattr(core_registry, "RELEASED", {})
    assert smoke.check_models(pyeconomics, extras=True).endswith("1 domain(s) covered")


def only_registration() -> Any:  # noqa: ANN401
    return core_registry.installed().registrations[0]


def test_a_model_that_should_have_raised_for_its_missing_extra_fails(
    toy_installed: Callable[..., None],
) -> None:
    quiet = tm.variant(tm.zero_coupon, id="econometrics.toy_quiet", extra="toy")
    toy_installed(quiet)
    with pytest.raises(RegistryError, match="ran although the extra 'toy'"):
        smoke.check_models(pyeconomics)  # validate() rejects it first
    with pytest.raises(AssertionError, match="ran although its 'toy' extra"):
        smoke.exercise(pyeconomics, only_registration(), run_all=False, extras=False)


def test_a_model_that_names_another_extra_fails(
    toy_installed: Callable[..., None],
) -> None:
    def other(_inputs: Any) -> Any:  # noqa: ANN401
        library = "somelib"
        raise MissingOptionalDependencyError(library, extra="other")

    wrong = tm.variant(tm.needs_extra, id="econometrics.toy_wrong")
    toy_installed(Model(wrong.spec, other))
    with pytest.raises(RegistryError, match="naming extra 'other'"):
        smoke.check_models(pyeconomics)
    with pytest.raises(AssertionError, match="named 'other', not the extra 'toy'"):
        smoke.exercise(pyeconomics, only_registration(), run_all=False, extras=False)


def test_a_model_that_does_not_reproduce_fails(
    toy_installed: Callable[..., None],
) -> None:
    counter = itertools.count()

    def drifting(inputs: Any) -> Any:  # noqa: ANN401
        return tm.ZeroCouponOutputs(price=1.0 + next(counter) / 1000 + inputs.rate * 0)

    drifts = Model(tm.zero_coupon.spec, drifting)
    toy_installed(drifts)
    with pytest.raises(AssertionError, match="different canonical JSON"):
        smoke.check_models(pyeconomics)


def test_a_model_without_an_example_fails(
    toy_installed: Callable[..., None],
) -> None:
    toy_installed(tm.variant(tm.zero_coupon, examples=()))
    with pytest.raises(RegistryError, match="declares no example"):
        smoke.check_models(pyeconomics)  # validate() rejects it first
    with pytest.raises(AssertionError, match="declares no example"):
        smoke.exercise(pyeconomics, only_registration(), run_all=False, extras=False)


def test_the_command_line_options(
    toy_installed: Callable[..., None],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    toy_installed()
    monkeypatch.setattr(smoke, "inside_a_checkout", lambda _: False)
    assert smoke.main(["--min-domains", "3", "--all"]) == 0
    assert (
        "ok    models: registry valid; 3 domain(s) covered" in capsys.readouterr().out
    )
    assert smoke.main(["--min-domains", "4"]) == 1
    assert "FAIL  models: AssertionError: 3 domain(s) were covered" in (
        capsys.readouterr().out
    )
    assert smoke.main(["--extras"]) == 1
    assert smoke.main(["--min-domains", "3", "--extras"]) == 1  # toy_extra


def test_argv_defaults_to_the_process_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(smoke, "inside_a_checkout", lambda _: False)
    monkeypatch.setattr(sys, "argv", ["smoke.py", "--min-domains", "99"])
    assert smoke.main() == 1  # the catalog spans fewer domains than that


# --- the econometrics extra, both ways (Phase 2 Step 12) -------------------------


@pytest.fixture
def without_statsmodels(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make statsmodels unimportable and its distribution look uninstalled."""
    for name in [m for m in sys.modules if m.split(".")[0] == "statsmodels"]:
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.setitem(sys.modules, "statsmodels", None)
    installed = core_registry._is_installed  # noqa: SLF001
    monkeypatch.setattr(
        core_registry,
        "_is_installed",
        lambda name: name != "statsmodels" and installed(name),
    )


@pytest.mark.usefixtures("without_statsmodels")
def test_without_the_extra_the_smoke_covers_econometrics_by_its_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    detail = smoke.check_models(pyeconomics, min_domains=11)
    # A floor of 11 (Phase 2's domains); the count grows as Phase 3 registers.
    assert (
        detail
        == f"registry valid; {len(pyeconomics.registry.domains())} domain(s) covered"
    )
    out = capsys.readouterr().out
    assert "econometrics.ols: raises, naming pyeconomics[econometrics]" in out
    with pytest.raises(AssertionError, match="needs the 'econometrics' extra"):
        smoke.check_models(pyeconomics, extras=True)


def test_with_the_extra_the_smoke_runs_ols_to_outputs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    smoke.check_models(pyeconomics, min_domains=11, extras=True)
    assert "econometrics.ols: 1 example(s) reproduce" in capsys.readouterr().out
