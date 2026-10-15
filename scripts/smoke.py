# scripts/smoke.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Smoke-test an installed pyeconomics: import it, exercise the core, run models.

CI runs this script against the built wheel, from a directory outside the
checkout, in a clean virtual environment (ci.yml's ``package`` job) and in
Pyodide (the ``pyodide`` job; ADR-0002, ADR-0008 decision 14);
release-smoke.yml runs it against every published release. It:

1. imports ``pyeconomics`` and refuses to run when the package resolves
   inside a checkout's ``src/`` tree, so it only ever tests an installed
   distribution;
2. checks ``pyeconomics.__version__`` against the distribution's metadata;
3. converts a monthly rate to its effective annual rate and compares it with
   the closed form;
4. checks the default rate tolerance accepts a rounding error and refuses a
   real difference;
5. checks ACT/360 and an observed federal holiday adjustment;
6. imports ``pyeconomics.data``, builds a monthly ``Series`` with a missing
   value, round-trips it through canonical JSON and pandas, and inspects the
   (possibly empty) cache without creating it (ADR-0011);
7. checks ``registry.validate()`` passes, then, for every registered domain,
   runs the first model's first example through ``pyeconomics.run`` twice and
   requires identical canonical JSON and manifests.

A model whose spec names an extra that is not installed is exercised by
asserting that running it raises ``MissingOptionalDependencyError`` naming the
extra, which covers its domain in an environment with no extras installed
(ADR-0002): ``econometrics.ols`` covers the econometrics domain that way
without the ``econometrics`` extra, and with ``--extras`` it must run to
outputs instead.

It prints one line per check and exits 0 when every check passes, 1 when one
fails and 2 when it refuses to run. Usage, from outside the checkout:

    python smoke.py [--all] [--min-domains N] [--extras]

--all            run every example of every model, not one model per domain
--min-domains N  fail when fewer than N domains were covered
--extras         fail unless every model that names an extra ran and returned
                 outputs, so the extras must be installed
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib
import platform
import sys
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from types import ModuleType

# (1 + 0.06 / 12) ** 12 - 1, computed independently with 40-digit decimals.
MONTHLY_6_PERCENT_EFFECTIVE = 0.0616778118644995687897


def inside_a_checkout(module_file: str) -> bool:
    """Return whether a package's ``__init__.py`` sits in a checkout's ``src/``."""
    source_tree = Path(module_file).resolve().parent.parent
    return (
        source_tree.name == "src" and (source_tree.parent / "pyproject.toml").is_file()
    )


def check_version(package: ModuleType) -> str:
    """Check the package reports the version in its distribution's metadata."""
    installed = metadata.version("pyeconomics")
    if package.__version__ != installed:
        msg = f"__version__ is {package.__version__}, the metadata says {installed}"
        raise AssertionError(msg)
    return f"__version__ equals the distribution's metadata ({installed})"


def check_compounding(package: ModuleType) -> str:
    """Check 6% compounded monthly is 6.1678% effective annual."""
    core = package.core
    effective = core.convert_rate(
        0.06,
        core.Compounding.PERIODIC,
        core.Compounding.PERIODIC,
        from_frequency=core.Frequency.MONTHLY,
        to_frequency=core.Frequency.ANNUAL,
    )
    tolerance = core.default_tolerance(core.UnitKind.RATE)
    if not tolerance.isclose(effective, MONTHLY_6_PERCENT_EFFECTIVE):
        msg = f"6% monthly gave {effective!r}, not {MONTHLY_6_PERCENT_EFFECTIVE!r}"
        raise AssertionError(msg)
    return f"6% compounded monthly is {core.format_percent(effective, decimals=4)}"


def check_tolerance(package: ModuleType) -> str:
    """Check the rate tolerance accepts rounding and refuses a difference."""
    core = package.core
    tolerance = core.default_tolerance(core.UnitKind.RATE)
    if not tolerance.isclose(0.05, 0.05 + 1e-14):
        msg = "the rate tolerance refuses a 1e-14 rounding error"
        raise AssertionError(msg)
    if tolerance.isclose(0.05, 0.0501):
        msg = "the rate tolerance accepts a 1bp difference"
        raise AssertionError(msg)
    return "the rate tolerance accepts 1e-14 and refuses 1bp"


def check_dates(package: ModuleType) -> str:
    """Exercise the installed day counter and holidays-backed adjustment."""
    core = package.core
    fraction = core.year_fraction(
        dt.date(2024, 1, 1), dt.date(2024, 7, 1), core.DayCount.ACT_360
    )
    if fraction != 182 / 360:
        msg = "ACT/360 did not count the leap-year half as 182 days"
        raise AssertionError(msg)
    payment = core.adjust(
        dt.date(2026, 7, 3), "us_federal", core.BusinessDayConvention.FOLLOWING
    )
    if payment != dt.date(2026, 7, 6):
        msg = "the observed federal holiday did not adjust to July 6"
        raise AssertionError(msg)
    return "ACT/360 and holidays-backed federal adjustment agree"


def check_data(package: ModuleType) -> str:
    """Build a monthly series and round-trip it through canonical JSON and pandas."""
    # Imported here, so that an installed wheel without it fails only this check.
    data = importlib.import_module("pyeconomics.data")

    terms = data.Terms(
        licence=data.LicenceClass.HOSTED_SAFE,
        terms_url="https://www.example.org/terms",
        checked=dt.date(2026, 10, 14),
        attribution="Source: a smoke test.",
        llm_use=data.LlmUse.ALLOWED,
        cache=data.CachePolicy.ALLOWED,
    )
    meta = data.SeriesMeta(
        provider="smoke",
        series_id="SMOKE_RATE",
        title="A smoke-test rate",
        unit=data.UnitRecord(text="Percent", kind=package.core.UnitKind.RATE),
        frequency=data.ObservationFrequency.MONTHLY,
        seasonal_adjustment=data.SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
        source_dating=data.DateConvention.PERIOD_START,
        terms=terms,
    )
    rate = package.core.percent_to_decimal(4.25)
    series = data.Series(
        (dt.date(2026, 1, 31), dt.date(2026, 2, 28)), (rate, None), meta
    )
    if data.Series.from_json(series.canonical_json()) != series:
        msg = "a Series did not survive its canonical JSON"
        raise AssertionError(msg)
    if data.Series.from_pandas(series.to_pandas()) != series:
        msg = "a Series did not survive pandas"
        raise AssertionError(msg)
    if [str(period) for period in series.periods()] != ["2026-01", "2026-02"]:
        msg = "a monthly Series' periods are not its months"
        raise AssertionError(msg)
    # The cache is imported without sqlite3 and inspecting it creates nothing; where
    # sqlite3 is absent (Pyodide without its package) it reports an empty cache.
    cache = data.cache
    if cache.path().name != "cache.sqlite3" or not isinstance(cache.entries(), tuple):
        msg = "the cache API did not answer"
        raise AssertionError(msg)
    return (
        f"pyeconomics.data round-trips a Series ({series.missing} missing value) "
        "and inspects its cache"
    )


def run_twice(package: ModuleType, model: Any, example: Any) -> str:  # noqa: ANN401
    """Run one example twice; require identical bytes and manifests."""
    first = package.run(model.id, example.inputs)
    second = package.run(model.id, example.inputs)
    if first.to_json().encode() != second.to_json().encode():
        msg = f"{model.id} gave different canonical JSON on two runs"
        raise AssertionError(msg)
    if first.manifest != second.manifest:
        msg = f"{model.id} gave different manifests on two runs"
        raise AssertionError(msg)
    return first.manifest.result_sha256[:12]


def exercise(
    package: ModuleType,
    registration: Any,  # noqa: ANN401
    *,
    run_all: bool,
    extras: bool,
) -> str:
    """Exercise one model; return a line saying how it was covered."""
    model = registration.model
    examples = model.spec.examples if run_all else model.spec.examples[:1]
    if not examples:
        msg = f"{model.id} declares no example"
        raise AssertionError(msg)
    extra = model.spec.extra
    if extra and not registration.provider.installed(extra):
        if extras:
            msg = f"{model.id} needs the {extra!r} extra, which is not installed"
            raise AssertionError(msg)
        try:
            package.run(model.id, examples[0].inputs)
        except package.core.MissingOptionalDependencyError as error:
            if error.extra != extra:
                msg = f"{model.id} named {error.extra!r}, not the extra {extra!r}"
                raise AssertionError(msg) from error
            return f"{model.id}: raises, naming pyeconomics[{extra}]"
        msg = f"{model.id} ran although its {extra!r} extra is not installed"
        raise AssertionError(msg)
    hashes = [run_twice(package, model, example) for example in examples]
    return f"{model.id}: {len(hashes)} example(s) reproduce (result {hashes[0]})"


def check_models(
    package: ModuleType,
    *,
    run_all: bool = False,
    min_domains: int = 0,
    extras: bool = False,
) -> str:
    """Validate the registry and run one model per registered domain.

    Raises ``AssertionError`` when validation fails, a model does not
    reproduce, or fewer than ``min_domains`` domains were covered.
    """
    from pyeconomics.core import registry as core_registry  # noqa: PLC0415

    package.registry.validate()
    registrations = {r.model.id: r for r in core_registry.installed().registrations}
    domains = package.registry.domains()
    for domain in domains:
        chosen = package.registry.models(domain)
        for model in chosen if run_all else chosen[:1]:
            line = exercise(
                package, registrations[model.id], run_all=run_all, extras=extras
            )
            print(f"        {line}")
    if len(domains) < min_domains:
        msg = (
            f"{len(domains)} domain(s) were covered, not the {min_domains} "
            f"required: {', '.join(domains) or 'none'}"
        )
        raise AssertionError(msg)
    return f"registry valid; {len(domains)} domain(s) covered"


CHECKS: tuple[tuple[str, Callable[[ModuleType], str]], ...] = (
    ("version", check_version),
    ("compounding", check_compounding),
    ("tolerance", check_tolerance),
    ("dates", check_dates),
    ("data", check_data),
)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Read the command line."""
    parser = argparse.ArgumentParser(description="Smoke-test an installed pyeconomics.")
    parser.add_argument("--all", action="store_true", dest="run_all")
    parser.add_argument("--min-domains", type=int, default=0, metavar="N")
    parser.add_argument("--extras", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run every check; return the process exit status."""
    options = parse_args(sys.argv[1:] if argv is None else argv)
    import pyeconomics  # noqa: PLC0415 - imported here so a failure is reported
    import pyeconomics.core  # noqa: PLC0415 - loads the core subpackage

    print(
        f"smoke: pyeconomics from {Path(pyeconomics.__file__).parent} on Python "
        f"{platform.python_version()} ({sys.platform})"
    )
    if inside_a_checkout(pyeconomics.__file__):
        print(
            "refused: pyeconomics was imported from a checkout's src/ tree; "
            "install the wheel and run this script from outside the checkout",
            file=sys.stderr,
        )
        return 2

    def models(package: ModuleType) -> str:
        return check_models(
            package,
            run_all=options.run_all,
            min_domains=options.min_domains,
            extras=options.extras,
        )

    failed = 0
    for name, check in (*CHECKS, ("models", models)):
        try:
            detail = check(pyeconomics)
        except Exception as error:  # noqa: BLE001 - every failure is reported
            failed += 1
            print(f"FAIL  {name}: {type(error).__name__}: {error}")
        else:
            print(f"ok    {name}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
