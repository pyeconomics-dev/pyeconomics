# scripts/new_model.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Scaffold a new catalog model: its module, golden file and property test.

Usage, from the repository root:

    uv run python scripts/new_model.py <domain>.<name> [--bound]

It creates three files for the id, each a skeleton the checks reject until it is
completed:

- ``src/pyeconomics/models/<domain>/<name>.py``: a specification that fails
  ``registry.validate()`` (no formula, assumptions, limitations or references);
- ``tests/golden/<domain>/<name>.toml``: a golden file the harness rejects (one
  placeholder source and case, no edge case);
- ``tests/models/<domain>/test_<name>.py``: a property test marked for the
  skeleton's one invariant, which fails until it asserts something.

With ``--bound`` the skeleton reads data: its input is a rate, the specification
declares one :class:`~pyeconomics.core.binding.Binding` of it to a catalog concept
(``us.unemployment.rate``), its example is the value that binding would read, and
the property test carries a bound example to complete (bind the model with a
replay transport, run it and assert on the manifest's records).

An id with a family, ``<domain>.<family>.<name>``, uses ``<family>_<name>`` as the
file name. For a domain with no package yet it also creates the package's
``__init__.py`` and prints the entry-point line to add to ``pyproject.toml``;
otherwise it prints the two lines to add to the domain's ``__init__.py``.

The id is validated first (ADR-0003's shape, no "cfa" per ADR-0009, one of the
fifteen domains, a name that is a Python identifier). The script writes only
below ``src/`` and ``tests/``, refuses to overwrite any file and creates nothing
if one exists.
"""

from __future__ import annotations

import argparse
import datetime as dt
import keyword
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pyeconomics.core.spec import DOMAINS, MODEL_ID

__all__ = ["Scaffold", "ScaffoldError", "plan", "write"]

REPO: Final = Path(__file__).resolve().parents[1]

_MODULE: Final = '''\
# src/pyeconomics/models/{domain}/{stem}.py
# Copyright {year} Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""TODO: one line saying what {model_id} computes."""

from __future__ import annotations

from pydantic import Field

from pyeconomics.core import (
{binding_import}    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    {unit},
    model,
)

__all__ = ["{stem}"]


class {camel}Inputs(ModelInputs):
    """The inputs: each declares a unit, bounds and a description."""

    value: {unit} = Field({bounds}, description="TODO: describe this input")


class {camel}Outputs(ModelOutputs):
    """The outputs: each declares a unit, bounds and a description."""

    result: {unit} = Field({bounds}, description="TODO: describe this output")


@model(
    id="{model_id}",
    version=1,
    title="TODO: a title",
    summary="TODO: one sentence saying what the model computes.",
    formula=(),
    assumptions=(),
    limitations=(),
    references=(),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    invariants=(
        Invariant(id="todo_invariant", statement="TODO: a property of every output."),
    ),
    examples=(Example(name="todo_example", inputs={{"value": {example}}}),),
{bindings}    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def {stem}(inputs: {camel}Inputs) -> {camel}Outputs:
    """Compute the outputs from the inputs. A pure function: no I/O."""
    return {camel}Outputs(result=inputs.value)
'''

_PACKAGE: Final = '''\
# src/pyeconomics/models/{domain}/__init__.py
# Copyright {year} Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The {domain} models."""

from pyeconomics.models.{domain}.{stem} import {stem}

__all__ = ["{stem}"]
'''

_GOLDEN: Final = """\
# tests/golden/{domain}/{stem}.toml
# Fill this in as tests/golden/README.md says; the harness rejects it until you do.
model = "{model_id}"

[[sources]]
key = "TODO"
kind = "official"
citation = "TODO: author, year, title, publisher"
url = "TODO: a link to the source"

[[cases]]
id = "TODO"
source = "TODO"
locator = "TODO: page, table, section or equation"
edge = false
inputs = {{}}
expected = {{ result = 0.0 }}
"""

_TEST: Final = '''\
# tests/models/{domain}/test_{stem}.py
# Copyright {year} Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Property tests for {model_id}: one per invariant in its specification."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from hypothesis import given
from strategies import inputs

from pyeconomics.core import run_model
from pyeconomics.models.{domain}.{stem} import {stem}

if TYPE_CHECKING:
    from collections.abc import Mapping


@pytest.mark.invariant("{model_id}", "todo_invariant")
@given(inputs({stem}))
def test_todo_invariant(raw: Mapping[str, Any]) -> None:
    run_model({stem}, raw)
    msg = "state the invariant and assert it"
    raise NotImplementedError(msg)
{bound_test}'''

_BOUND_TEST: Final = '''

def test_bound_example() -> None:
    """Bind the model's data offline, run it and check the manifest's records."""
    msg = (
        "complete the bound example: pyeconomics.data.bind_model({stem}, as_of=..., "
        "transport=<a replay transport>) reads the model's binding; run the Bound "
        "with run_model and assert on result.manifest.data_sources"
    )
    raise NotImplementedError(msg)
'''

#: What ``--bound`` changes in the module skeleton, and what its absence leaves.
_BOUND_MODULE: Final = {
    "binding_import": "    Binding,\n",
    "unit": "Rate",
    "bounds": "ge=-0.99, le=10.0",
    "example": "0.04",
    "bindings": (
        "    # Real time by default: the value published by the evaluation date.\n"
        "    # Binding(..., vintage=VintagePolicy.LATEST) reads revised data.\n"
        '    bindings=(Binding("value", "us.unemployment.rate"),),\n'
    ),
}
_UNBOUND_MODULE: Final = {
    "binding_import": "",
    "unit": "Ratio",
    "bounds": "ge=-1e6, le=1e6",
    "example": "0.0",
    "bindings": "",
}


class ScaffoldError(ValueError):
    """The id is not a valid new model id, or a file would be overwritten."""


@dataclass(frozen=True, slots=True)
class Scaffold:
    """What the script will create for one id."""

    model_id: str
    domain: str
    stem: str
    new_domain: bool
    files: dict[Path, str]


def parse_id(model_id: str) -> tuple[str, str]:
    """Validate an id and return its domain and file stem.

    Raises
    ------
    ScaffoldError
        If the id is not ``<domain>.<name>`` (or ``<domain>.<family>.<name>``) in
        snake_case, the domain is not one of the fifteen, or the name is a Python
        keyword.
    """
    if not MODEL_ID.fullmatch(model_id):
        msg = (
            f"{model_id!r} is not <domain>.<name> in snake_case "
            "(optionally <domain>.<family>.<name>)"
        )
        raise ScaffoldError(msg)
    if "cfa" in model_id.lower():
        msg = f"{model_id!r} contains 'cfa', which no id may (ADR-0009)"
        raise ScaffoldError(msg)
    domain, _, rest = model_id.partition(".")
    if domain not in DOMAINS:
        msg = f"{domain!r} is not one of the domains: {', '.join(DOMAINS)}"
        raise ScaffoldError(msg)
    stem = rest.replace(".", "_")
    if keyword.iskeyword(stem) or keyword.issoftkeyword(stem):
        msg = f"{stem!r} is a Python keyword and cannot name a module"
        raise ScaffoldError(msg)
    return domain, stem


def _confined(target: Path, root: Path) -> None:
    """Refuse a path that resolves outside ``src/`` and ``tests/`` under ``root``."""
    resolved = target.resolve()
    if not any(
        resolved.is_relative_to((root / top).resolve()) for top in ("src", "tests")
    ):
        msg = f"{target} resolves outside src/ and tests/"
        raise ScaffoldError(msg)


def plan(
    model_id: str, root: Path = REPO, *, year: int | None = None, bound: bool = False
) -> Scaffold:
    """Decide what to create for ``model_id`` below ``root``.

    With ``bound`` the skeleton declares one data binding and a bound example.

    Raises
    ------
    ScaffoldError
        If the id is invalid, a target would leave ``src/`` and ``tests/``, or any
        target already exists (nothing is created then).
    """
    domain, stem = parse_id(model_id)
    values: dict[str, object] = {
        "model_id": model_id,
        "domain": domain,
        "stem": stem,
        "camel": "".join(part.capitalize() for part in stem.split("_")),
        "year": year or dt.datetime.now(tz=dt.UTC).year,
        **(_BOUND_MODULE if bound else _UNBOUND_MODULE),
    }
    values["bound_test"] = _BOUND_TEST.format(**values) if bound else ""
    package = root / "src" / "pyeconomics" / "models" / domain
    new_domain = not (package / "__init__.py").exists()
    files = {
        package / f"{stem}.py": _MODULE.format(**values),
        root / "tests" / "golden" / domain / f"{stem}.toml": _GOLDEN.format(**values),
        root / "tests" / "models" / domain / f"test_{stem}.py": _TEST.format(**values),
    }
    if new_domain:
        files[package / "__init__.py"] = _PACKAGE.format(**values)
    for target in files:
        _confined(target, root)
    taken = [str(p) for p in files if p.exists() or p.is_symlink()]
    twins = [
        str(p) for p in (root / "tests").rglob(f"test_{stem}.py") if p not in files
    ]
    if taken or twins:
        found = ", ".join([*taken, *twins])
        msg = f"refusing to overwrite or duplicate: {found}"
        raise ScaffoldError(msg)
    return Scaffold(model_id, domain, stem, new_domain, files)


def write(scaffold: Scaffold) -> list[Path]:
    """Create the files of a plan, never overwriting one; return them in order."""
    created: list[Path] = []
    for path, text in scaffold.files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        created.append(path)
    return created


def instructions(scaffold: Scaffold) -> str:
    """Say what to add by hand to register the model."""
    domain, stem = scaffold.domain, scaffold.stem
    if scaffold.new_domain:
        return (
            f"{domain} is a new domain. Add this line to pyproject.toml under "
            '[project.entry-points."pyeconomics.models"]:\n'
            f'    {domain} = "pyeconomics.models.{domain}"'
        )
    return (
        f"Register the model in src/pyeconomics/models/{domain}/__init__.py:\n"
        f"    from pyeconomics.models.{domain}.{stem} import {stem}\n"
        f'and add "{stem}" to __all__.'
    )


def main(argv: list[str], root: Path = REPO) -> int:
    """Scaffold the model named in ``argv`` below ``root``; return the exit code."""
    parser = argparse.ArgumentParser(
        prog="new_model.py", description="Scaffold a new catalog model."
    )
    parser.add_argument("model_id", help="the permanent id, <domain>.<name>")
    parser.add_argument(
        "--bound",
        action="store_true",
        help="declare a data binding (on us.unemployment.rate) and a bound example",
    )
    arguments = parser.parse_args(argv[1:])
    try:
        scaffold = plan(arguments.model_id, root, bound=arguments.bound)
        created = write(scaffold)
    except ScaffoldError as error:
        print(f"new_model: {error}", file=sys.stderr)
        return 2
    for path in created:
        print(f"created {path.relative_to(root).as_posix()}")
    print(instructions(scaffold))
    print(
        "Next: complete all three files, then run "
        '`uv run python -c "from pyeconomics import registry; registry.validate()"` '
        "and `uv run pytest`."
    )
    if arguments.bound:
        check = "from pyeconomics import data; data.validate_bindings()"
        print(
            "The model is bound: replace the example binding with the model's own, "
            f'then run `uv run python -c "{check}"`.'
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
