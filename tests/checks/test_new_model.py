# tests/checks/test_new_model.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for scripts/new_model.py, the catalog model scaffold."""

from __future__ import annotations

import ast
import importlib.util
import subprocess  # nosec B404: runs this interpreter with fixed arguments
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from _loader import audit

from pyeconomics.core import Model, Registry, RegistryError

if TYPE_CHECKING:
    from types import ModuleType

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "new_model.py"
ID = "fixed_income.convexity"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("new_model_script", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # A dataclass looks its module up by name while it is being built.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


nm = load_script()


def files_under(root: Path) -> list[str]:
    return sorted(
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
    )


def create(root: Path, model_id: str = ID) -> list[Path]:
    return nm.write(nm.plan(model_id, root, year=2026))  # type: ignore[no-any-return]


def load_model(path: Path) -> Model[Any, Any]:
    """Import a scaffolded module from its file and return its model."""
    spec = importlib.util.spec_from_file_location("scaffolded_module", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    found = getattr(module, module.__all__[0])
    assert isinstance(found, Model)
    return found


# --- what it creates ----------------------------------------------------------


def test_a_new_domain_gets_four_files_and_an_entry_point_line(tmp_path: Path) -> None:
    scaffold = nm.plan(ID, tmp_path, year=2026)
    assert scaffold.new_domain
    message = nm.instructions(scaffold)
    nm.write(scaffold)
    assert files_under(tmp_path) == [
        "src/pyeconomics/models/fixed_income/__init__.py",
        "src/pyeconomics/models/fixed_income/convexity.py",
        "tests/golden/fixed_income/convexity.toml",
        "tests/models/fixed_income/test_convexity.py",
    ]
    assert 'fixed_income = "pyeconomics.models.fixed_income"' in message
    assert '[project.entry-points."pyeconomics.models"]' in message


def test_an_existing_domain_gets_three_files_and_two_lines_to_add(
    tmp_path: Path,
) -> None:
    create(tmp_path)
    plan = nm.plan("fixed_income.duration", tmp_path, year=2026)
    assert not plan.new_domain
    nm.write(plan)
    assert files_under(tmp_path)[:2] == [
        "src/pyeconomics/models/fixed_income/__init__.py",
        "src/pyeconomics/models/fixed_income/convexity.py",
    ]
    assert len(files_under(tmp_path)) == 7
    message = nm.instructions(plan)
    assert "from pyeconomics.models.fixed_income.duration import duration" in message
    assert 'add "duration" to __all__' in message


def test_a_family_id_joins_family_and_name(tmp_path: Path) -> None:
    create(tmp_path, "equity.dcf.gordon_growth")
    names = files_under(tmp_path)
    assert "src/pyeconomics/models/equity/dcf_gordon_growth.py" in names
    assert "tests/golden/equity/dcf_gordon_growth.toml" in names
    assert "tests/models/equity/test_dcf_gordon_growth.py" in names
    module = (
        tmp_path / "src/pyeconomics/models/equity/dcf_gordon_growth.py"
    ).read_text(encoding="utf-8")
    assert 'id="equity.dcf.gordon_growth"' in module
    assert "class DcfGordonGrowthInputs(ModelInputs)" in module


def test_every_python_skeleton_parses_and_carries_the_header(tmp_path: Path) -> None:
    for path in create(tmp_path):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(tmp_path).as_posix()
        assert text.startswith(f"# {relative}\n"), relative
        if path.suffix == ".py":
            assert "# Copyright 2026 Nathan Ramos, CFA\n" in text.split('"""')[0]
            assert "# SPDX-License-Identifier: Apache-2.0\n" in text.split('"""')[0]
            ast.parse(text)


def test_files_are_written_with_unix_line_endings(tmp_path: Path) -> None:
    assert all(b"\r" not in p.read_bytes() for p in create(tmp_path))


def test_the_skeletons_agree_on_the_invariant_and_the_module_path(
    tmp_path: Path,
) -> None:
    create(tmp_path)
    module = (tmp_path / "src/pyeconomics/models/fixed_income/convexity.py").read_text(
        encoding="utf-8"
    )
    test = (tmp_path / "tests/models/fixed_income/test_convexity.py").read_text(
        encoding="utf-8"
    )
    assert 'Invariant(id="todo_invariant"' in module
    assert f'@pytest.mark.invariant("{ID}", "todo_invariant")' in test
    assert "from pyeconomics.models.fixed_income.convexity import convexity" in test
    package = (tmp_path / "src/pyeconomics/models/fixed_income/__init__.py").read_text(
        encoding="utf-8"
    )
    assert '__all__ = ["convexity"]' in package


# --- the skeletons fail until completed ---------------------------------------


def test_the_specification_skeleton_fails_validate(tmp_path: Path) -> None:
    create(tmp_path)
    model = load_model(tmp_path / "src/pyeconomics/models/fixed_income/convexity.py")
    assert model.id == ID
    with pytest.raises(RegistryError) as raised:
        Registry.from_models(model).validate()
    rules = "\n".join(raised.value.problems)
    assert len(raised.value.problems) >= 3
    assert "[references]" in rules or "reference" in rules
    assert "formula" in rules


def test_the_golden_skeleton_fails_the_harness(tmp_path: Path) -> None:
    create(tmp_path)
    model = load_model(tmp_path / "src/pyeconomics/models/fixed_income/convexity.py")
    found = audit(Registry.from_models(model), tmp_path / "tests" / "golden").problems
    joined = "\n".join(found)
    assert "still a placeholder" in joined
    assert "1 case(s)" in joined
    assert "no case has edge = true" in joined


def test_the_test_skeleton_fails_until_it_asserts_something(tmp_path: Path) -> None:
    create(tmp_path)
    text = (tmp_path / "tests/models/fixed_income/test_convexity.py").read_text(
        encoding="utf-8"
    )
    assert "raise NotImplementedError" in text


# --- it refuses ---------------------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    [
        "src/pyeconomics/models/fixed_income/convexity.py",
        "tests/golden/fixed_income/convexity.toml",
        "tests/models/fixed_income/test_convexity.py",
    ],
)
def test_it_refuses_to_overwrite_any_file_and_creates_nothing(
    tmp_path: Path, relative: str
) -> None:
    existing = tmp_path / relative
    existing.parent.mkdir(parents=True)
    existing.write_text("mine\n", encoding="utf-8")
    with pytest.raises(nm.ScaffoldError, match="refusing to overwrite"):
        nm.plan(ID, tmp_path)
    assert files_under(tmp_path) == [relative]
    assert existing.read_text(encoding="utf-8") == "mine\n"


def test_the_writer_itself_never_overwrites(tmp_path: Path) -> None:
    scaffold = nm.plan(ID, tmp_path)
    nm.write(scaffold)
    before = {p: p.read_bytes() for p in scaffold.files}
    with pytest.raises(FileExistsError):
        nm.write(scaffold)
    assert {p: p.read_bytes() for p in scaffold.files} == before


def test_it_refuses_a_test_file_whose_name_is_taken_elsewhere(tmp_path: Path) -> None:
    other = tmp_path / "tests" / "models" / "risk" / "test_convexity.py"
    other.parent.mkdir(parents=True)
    other.write_text("", encoding="utf-8")
    with pytest.raises(nm.ScaffoldError, match="refusing to overwrite or duplicate"):
        nm.plan(ID, tmp_path)


@pytest.mark.parametrize(
    "model_id",
    [
        "",
        "convexity",
        "Fixed_Income.convexity",
        "fixed_income.Convexity",
        "fixed_income.1convexity",
        "fixed_income.convex-ity",
        "fixed_income.a.b.c",
        "fixed_income..convexity",
        ".convexity",
        "fixed_income.",
        "../tests.evil",
        "fixed_income.../evil",
        "fixed_income.x/../../evil",
        "fixed_income.x\\evil",
        "fixed_income.x y",
        "fixed_income.x\n",
        "fixed_income.convexity.py",
    ],
)
def test_an_invalid_id_is_rejected_before_anything_is_written(
    tmp_path: Path, model_id: str
) -> None:
    if model_id == "fixed_income.convexity.py":
        # Valid in shape: a family called convexity and a name called py.
        assert nm.plan(model_id, tmp_path).stem == "convexity_py"
        return
    with pytest.raises(nm.ScaffoldError):
        nm.plan(model_id, tmp_path)
    assert files_under(tmp_path) == []


@pytest.mark.parametrize("model_id", ["nowhere.thing", "cfa.thing", "Equity.thing"])
def test_the_domain_must_be_one_of_the_fifteen_domains(
    tmp_path: Path, model_id: str
) -> None:
    with pytest.raises(nm.ScaffoldError):
        nm.plan(model_id, tmp_path)


@pytest.mark.parametrize(
    "model_id", ["equity.cfa_beta", "equity.beta_cfa", "risk.cfa.x"]
)
def test_an_id_may_not_contain_cfa(tmp_path: Path, model_id: str) -> None:
    with pytest.raises(nm.ScaffoldError, match="contains 'cfa'"):
        nm.plan(model_id, tmp_path)
    assert files_under(tmp_path) == []


@pytest.mark.parametrize("model_id", ["nowhere.thing", "Equity.thing"])
def test_the_domain_must_be_one_of_the_fifteen(tmp_path: Path, model_id: str) -> None:
    with pytest.raises(nm.ScaffoldError):
        nm.plan(model_id, tmp_path)


@pytest.mark.parametrize("name", ["import", "class", "match", "type", "None"])
def test_a_python_keyword_cannot_name_a_module(tmp_path: Path, name: str) -> None:
    with pytest.raises(nm.ScaffoldError):
        nm.plan(f"equity.{name}", tmp_path)


# --- it stays inside src/ and tests/ ------------------------------------------


def test_every_target_is_inside_src_or_tests(tmp_path: Path) -> None:
    scaffold = nm.plan(ID, tmp_path)
    for target in scaffold.files:
        assert target.resolve().is_relative_to(
            (tmp_path / "src").resolve()
        ) or target.resolve().is_relative_to((tmp_path / "tests").resolve())


@pytest.mark.parametrize(
    "relative", ["../outside.py", "src/../outside.py", "other/x.py", "srcs/x.py"]
)
def test_the_confinement_check_refuses_other_places(
    tmp_path: Path, relative: str
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    with pytest.raises(nm.ScaffoldError, match="outside src/ and tests/"):
        nm._confined(tmp_path / relative, tmp_path)  # noqa: SLF001
    nm._confined(tmp_path / "src" / "x.py", tmp_path)  # noqa: SLF001
    nm._confined(tmp_path / "tests" / "a" / "b.py", tmp_path)  # noqa: SLF001


def test_plan_confines_targets_even_if_id_validation_were_bypassed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Defence in depth: should parse_id ever let a path segment through, no target
    # may leave src/ and tests/.
    monkeypatch.setattr(nm, "parse_id", lambda _model_id: ("../../..", "evil"))
    with pytest.raises(nm.ScaffoldError, match="outside src/ and tests/"):
        nm.plan(ID, tmp_path)
    assert files_under(tmp_path) == []


def test_a_symlink_out_of_the_tree_is_refused(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "repo"
    (root / "src" / "pyeconomics").mkdir(parents=True)
    (root / "tests").mkdir()
    link = root / "src" / "pyeconomics" / "models"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("this account cannot create symbolic links")
    with pytest.raises(nm.ScaffoldError, match="outside src/ and tests/"):
        nm.plan(ID, root)
    assert files_under(outside) == []


# --- the command line ---------------------------------------------------------


def test_main_creates_the_files_and_prints_what_to_do(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert nm.main(["new_model.py", ID], tmp_path) == 0
    out = capsys.readouterr().out
    assert "created src/pyeconomics/models/fixed_income/convexity.py" in out
    assert "created tests/golden/fixed_income/convexity.toml" in out
    assert "created tests/models/fixed_income/test_convexity.py" in out
    assert 'fixed_income = "pyeconomics.models.fixed_income"' in out
    assert "registry.validate()" in out
    assert len(files_under(tmp_path)) == 4


def test_main_reports_a_bad_id_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert nm.main(["new_model.py", "nowhere.thing"], tmp_path) == 2
    captured = capsys.readouterr()
    assert "new_model: 'nowhere' is not one of the domains" in captured.err
    assert captured.out == ""
    assert files_under(tmp_path) == []


def test_main_reports_a_file_it_would_overwrite(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert nm.main(["new_model.py", ID], tmp_path) == 0
    capsys.readouterr()
    assert nm.main(["new_model.py", ID], tmp_path) == 2
    assert "refusing to overwrite" in capsys.readouterr().err


def test_the_script_runs_as_a_command(tmp_path: Path) -> None:
    run = subprocess.run(  # noqa: S603 # nosec B603: fixed arguments, no shell
        [sys.executable, str(SCRIPT), "nowhere.thing"],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert run.returncode == 2
    assert "is not one of the domains" in run.stderr


# --- --bound: a model that reads data -------------------------------------------


def test_bound_adds_one_binding_on_a_catalog_concept_and_a_bound_example(
    tmp_path: Path,
) -> None:
    nm.write(nm.plan(ID, tmp_path, year=2026, bound=True))
    module = (tmp_path / "src/pyeconomics/models/fixed_income/convexity.py").read_text(
        encoding="utf-8"
    )
    test = (tmp_path / "tests/models/fixed_income/test_convexity.py").read_text(
        encoding="utf-8"
    )
    ast.parse(module)
    ast.parse(test)
    assert "    Binding,\n" in module
    assert 'bindings=(Binding("value", "us.unemployment.rate"),)' in module
    assert "value: Rate = Field(ge=-0.99, le=10.0" in module
    assert 'inputs={"value": 0.04}' in module
    assert "def test_bound_example() -> None:" in test
    assert "bind_model(convexity" in test
    assert test.count("NotImplementedError") == 2  # both skeletons fail until done


def test_without_bound_the_skeleton_is_what_it_was(tmp_path: Path) -> None:
    plain = nm.plan(ID, tmp_path, year=2026)
    module = next(t for p, t in plain.files.items() if p.name == "convexity.py")
    test = next(t for p, t in plain.files.items() if p.name == "test_convexity.py")
    assert "Binding" not in module
    assert "bindings=" not in module
    assert "value: Ratio = Field(ge=-1e6, le=1e6" in module
    assert "test_bound_example" not in test


def test_the_bound_skeleton_is_a_valid_bound_model_whose_binding_validates(
    tmp_path: Path,
) -> None:
    nm.write(nm.plan(ID, tmp_path, year=2026, bound=True))
    path = tmp_path / "src/pyeconomics/models/fixed_income/convexity.py"
    spec = importlib.util.spec_from_file_location("scaffolded_bound_module", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # pydantic resolves the module's postponed annotations through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    model = module.convexity
    assert [b.concept for b in model.spec.bindings] == ["us.unemployment.rate"]
    registry = Registry.from_models(model)
    rules = {problem.rule for problem in registry.problems(released={})}
    assert "bindings" not in rules  # the TODO prose fails; the binding does not
    assert "formula" in rules
    from pyeconomics import data  # noqa: PLC0415 - only this test needs the data layer

    data.validate_bindings(registry)


def test_main_takes_bound_and_says_how_to_check_the_binding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert nm.main(["new_model.py", ID, "--bound"], tmp_path) == 0
    out = capsys.readouterr().out
    assert "validate_bindings()" in out
    module = (tmp_path / "src/pyeconomics/models/fixed_income/convexity.py").read_text(
        encoding="utf-8"
    )
    assert "Binding(" in module
    plain = tmp_path / "plain"
    assert nm.main(["new_model.py", ID], plain) == 0
    assert "validate_bindings" not in capsys.readouterr().out
