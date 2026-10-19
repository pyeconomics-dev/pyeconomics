# tests/docs/test_model_pages.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Exercise generation without importing Sphinx or the docs dependency group."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import TYPE_CHECKING, Any

import bound_support as bound
import pytest
from toy_models import mean_return, variant, zero_coupon

from pyeconomics import registry
from pyeconomics.core import Registry
from pyeconomics.core.cards import ModelCard

if TYPE_CHECKING:
    from types import ModuleType


@pytest.fixture
def generator() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "docs" / "_ext" / "model_pages.py"
    spec = importlib.util.spec_from_file_location("model_pages_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cards_and_domain_indexes(generator: ModuleType, tmp_path: Path) -> None:
    catalog = Registry.from_models(zero_coupon, mean_return)
    pages = generator.write_pages(tmp_path, catalog)
    assert len(pages) == len(catalog.ids())
    page = tmp_path / "fixed_income" / "toy_zero_coupon.md"
    assert (
        page.read_text(encoding="utf-8")
        == ModelCard.from_model(zero_coupon).to_markdown()
    )
    assert "toy_zero_coupon" in (page.parent / "index.md").read_text()
    assert "foundations/index" in (tmp_path / "index.md").read_text()


def test_a_bound_models_page_lists_the_sources_of_its_concepts(
    generator: ModuleType, tmp_path: Path
) -> None:
    catalog = Registry.from_models(zero_coupon, bound.unemployment)
    generator.write_pages(tmp_path, catalog)
    page = (tmp_path / "macro" / "toy_unemployment.md").read_text(encoding="utf-8")
    assert "## Data" in page
    assert "### Sources" in page
    assert "- **bls** (hosted-safe)" in page
    assert "- **fred** (library-only)" in page
    plain = (tmp_path / "fixed_income" / "toy_zero_coupon.md").read_text(
        encoding="utf-8"
    )
    assert "## Data" not in plain
    assert plain == ModelCard.from_model(zero_coupon).to_markdown()


@pytest.mark.parametrize("defect", ["missing", "extra", "misplaced"])
def test_page_mismatch_fails(
    generator: ModuleType, tmp_path: Path, defect: str
) -> None:
    catalog = Registry.from_models(zero_coupon)
    (page,) = generator.write_pages(tmp_path, catalog)
    if defect in {"missing", "misplaced"}:
        page.unlink()
    if defect in {"extra", "misplaced"}:
        (tmp_path / "extra.md").write_bytes(b"# Extra\n")
    with pytest.raises(ValueError, match="Model page count mismatch"):
        generator.check_pages(tmp_path, catalog.ids())


def test_rebuild_removes_only_stale_markdown(
    generator: ModuleType, tmp_path: Path
) -> None:
    generator.write_pages(tmp_path, Registry.from_models(zero_coupon, mean_return))
    asset = tmp_path / "keep.txt"
    asset.write_bytes(b"untouched")
    generator.write_pages(tmp_path, Registry.from_models(mean_return))
    assert not (tmp_path / "fixed_income" / "toy_zero_coupon.md").exists()
    assert not (tmp_path / "fixed_income" / "index.md").exists()
    assert asset.read_bytes() == b"untouched"


def test_empty_registry(generator: ModuleType, tmp_path: Path) -> None:
    assert generator.write_pages(tmp_path, Registry.from_models()) == ()
    generator.check_pages(tmp_path, ())


def test_nested_model_id(generator: ModuleType, tmp_path: Path) -> None:
    model = variant(zero_coupon, id="fixed_income.family.example")
    generator.write_pages(tmp_path, Registry.from_models(model))
    assert (tmp_path / "fixed_income" / "family" / "example.md").is_file()


@pytest.mark.parametrize("model_id", ["../escape", "domain.index", "domain.a/b"])
def test_invalid_ids_cannot_write(
    generator: ModuleType, tmp_path: Path, model_id: str
) -> None:
    class InvalidCatalog:
        def ids(self) -> tuple[str, ...]:
            return (model_id,)

    with pytest.raises(ValueError, match="Invalid or duplicate"):
        generator.write_pages(tmp_path, InvalidCatalog())
    assert list(tmp_path.iterdir()) == []


def test_no_sphinx_import(
    generator: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A sentinel makes this meaningful even when the developer installed docs.
    monkeypatch.setitem(sys.modules, "sphinx", None)
    spec = importlib.util.spec_from_file_location("without_sphinx", generator.__file__)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(importlib.util.module_from_spec(spec))


def test_setup_hook(generator: ModuleType, tmp_path: Path) -> None:
    # Importing Sphinx is deliberately confined to setup(); ordinary test jobs
    # substitute its error type and still exercise the callback.
    fake = types.ModuleType("sphinx.errors")
    fake.ExtensionError = ValueError  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]

    class App:
        srcdir = tmp_path
        callback: Any = None

        def connect(self, event: str, callback: Any) -> None:  # noqa: ANN401
            assert event == "builder-inited"
            self.callback = callback

    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(sys.modules, "sphinx.errors", fake)
        app = App()
        assert generator.setup(app)["parallel_read_safe"]
        app.callback(app)
        generator.check_pages(tmp_path / "reference" / "models", registry.ids())
