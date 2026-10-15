# tests/docs/test_provider_pages.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Exercise the provider page generator without importing Sphinx."""

from __future__ import annotations

import importlib.util
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from stubs import Stub
from toys import ToyJson, ToyVintage

from pyeconomics.data import Authentication, ProviderInfo
from pyeconomics.data.registry import ProviderRegistry

if TYPE_CHECKING:
    from types import ModuleType


@pytest.fixture
def generator() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "docs" / "_ext" / "provider_pages.py"
    spec = importlib.util.spec_from_file_location("provider_pages_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_page_states_the_class_terms_notice_key_limits_and_hosts(
    generator: ModuleType,
) -> None:
    page = generator.render(ToyJson.info)
    assert page.startswith("# Toy JSON Agency\n")
    for expected in (
        "Provider id: `toy_json`",
        "`hosted-safe`",
        "[terms page](https://www.toyjson.example.org/terms), read on 2026-10-15",
        "`allowed`",
        "`fetch`, `search`, `describe`",
        "> Source: Toy JSON Agency (a test fixture with invented numbers).",
        "This product uses the Toy JSON API",
        "`TOY_JSON_API_KEY`",
        "- 5 requests per second",
        "- 120 requests per minute",
        "- `api.toyjson.example.org`",
        "None (the default install).",
    ):
        assert expected in page, expected


def test_a_library_only_source_without_a_key_or_notice(generator: ModuleType) -> None:
    page = generator.render(ToyVintage.info)
    assert "`library-only`" in page
    assert "`forbidden`" in page
    assert "No key is needed." in page
    assert "None required." in page


def test_an_extra_a_contact_and_an_optional_key_are_described(
    generator: ModuleType,
) -> None:
    extra = generator.render(replace(Stub.info, extra="sdmx"))
    assert 'pip install "pyeconomics[sdmx]"' in extra
    contact = generator.render(replace(Stub.info, auth=Authentication.contact()))
    assert "PYECONOMICS_SEC_CONTACT" in contact
    optional = generator.render(
        replace(ToyJson.info, auth=replace(ToyJson.info.auth, required=False))
    )
    assert "optional and raises the limits" in optional
    session = generator.render(replace(Stub.info, hosts=()))
    assert "a local session" in session


def test_markdown_in_a_providers_text_is_escaped(generator: ModuleType) -> None:
    terms = replace(Stub.info.terms, attribution="Source: *a* [b](c) `d` <e> | f")
    page = generator.render(replace(Stub.info, name="A_B *star*", terms=terms))
    assert r"# A\_B \*star\*" in page
    assert r"\*a\* \[b\](c) \`d\` \<e\> \| f" in page


def test_pages_and_the_index_are_written_and_stale_ones_removed(
    generator: ModuleType, tmp_path: Path
) -> None:
    catalog = ProviderRegistry.from_providers(ToyJson, ToyVintage)
    (tmp_path / "old_provider.md").write_text("# stale")
    pages = generator.write_pages(tmp_path, catalog)
    assert sorted(p.name for p in pages) == ["toy_json.md", "toy_vintage.md"]
    assert not (tmp_path / "old_provider.md").exists()
    index = (tmp_path / "index.md").read_text(encoding="utf-8")
    assert (
        "| [Toy JSON Agency](toy_json.md) | `toy_json` | `hosted-safe` | `key` |"
        in index
    )
    assert "toy_vintage\n" in index
    assert (tmp_path / "toy_json.md").read_text(encoding="utf-8") == generator.render(
        ToyJson.info
    )


def test_the_index_of_an_empty_registry_says_so_and_builds_no_toctree(
    generator: ModuleType, tmp_path: Path
) -> None:
    assert generator.write_pages(tmp_path, ProviderRegistry([])) == ()
    index = (tmp_path / "index.md").read_text(encoding="utf-8")
    assert "No data provider is registered" in index
    assert "toctree" not in index


@pytest.mark.parametrize("defect", ["missing", "extra", "misplaced"])
def test_a_page_mismatch_fails(
    generator: ModuleType, tmp_path: Path, defect: str
) -> None:
    catalog = ProviderRegistry.from_providers(ToyJson)
    (page,) = generator.write_pages(tmp_path, catalog)
    if defect in {"missing", "misplaced"}:
        page.unlink()
    if defect in {"extra", "misplaced"}:
        (tmp_path / "extra.md").write_bytes(b"# Extra\n")
    with pytest.raises(ValueError, match="Provider page count mismatch"):
        generator.check_pages(tmp_path, catalog.ids())


@pytest.mark.parametrize("bad_id", ["../escape", "Bad-Id", "index", "a/b"])
def test_a_malformed_id_cannot_escape_the_directory(
    generator: ModuleType, tmp_path: Path, bad_id: str
) -> None:
    class Fake:
        def infos(self) -> tuple[ProviderInfo, ...]:
            return (replace(ToyJson.info, id=bad_id),)

    with pytest.raises(ValueError, match="Invalid or duplicate"):
        generator.write_pages(tmp_path / "pages", Fake())
    assert not (tmp_path / "pages").exists()


def test_a_duplicate_id_is_refused(generator: ModuleType, tmp_path: Path) -> None:
    class Fake:
        def infos(self) -> tuple[ProviderInfo, ...]:
            return (ToyJson.info, ToyJson.info)

    with pytest.raises(ValueError, match="Invalid or duplicate"):
        generator.write_pages(tmp_path, Fake())
