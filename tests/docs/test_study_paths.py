# tests/docs/test_study_paths.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Exercise the study paths generator without importing Sphinx.

Each page lists our own model pages under the issuing body's topic names, with
the mark as an adjective and the notice, and no wording of a syllabus (ADR-0013
decision 12; ROADMAP section 5 "CFA Institute marks and content").
"""

from __future__ import annotations

import importlib
import re
import sys
import types
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import pytest

from pyeconomics import registry

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType

ROOT: Final = Path(__file__).resolve().parents[2]
EXTENSIONS: Final = ROOT / "docs" / "_ext"
#: Words that belong to curriculum content, which no page may hold.
CURRICULUM: Final = re.compile(
    r"learning (outcome|objective|module)|\bLOS\b|\breading\b|\bexam\b|curriculum",
    re.IGNORECASE,
)


@pytest.fixture
def generator(monkeypatch: pytest.MonkeyPatch) -> Iterator[ModuleType]:
    monkeypatch.syspath_prepend(str(EXTENSIONS))
    yield importlib.import_module("study_paths")
    sys.modules.pop("study_paths", None)
    sys.modules.pop("model_pages", None)


@pytest.fixture
def titles() -> dict[str, str]:
    return {model_id: registry.get(model_id).spec.title for model_id in registry.ids()}


def _load(generator: ModuleType) -> tuple[Any, ...]:
    syllabi: tuple[Any, ...] = sys.modules["model_pages"].syllabus_loader().load()
    assert generator.NOTICES
    return syllabi


def test_one_page_per_level_and_an_index(
    generator: ModuleType, titles: dict[str, str], tmp_path: Path
) -> None:
    syllabi = _load(generator)
    written = generator.write_pages(tmp_path, syllabi, titles)
    levels = sum(len(syllabus.levels) for syllabus in syllabi)
    assert len(written) == levels + 1
    assert (tmp_path / "index.md").is_file()
    for syllabus in syllabi:
        for level in syllabus.levels:
            page = tmp_path / syllabus.id / f"level-{level.level}.md"
            assert page.is_file()
            assert f"{level.title} <{syllabus.id}/level-{level.level}>" in (
                (tmp_path / "index.md").read_text("utf-8")
            )


def test_a_level_lists_every_topic_and_the_models_mapped_to_it(
    generator: ModuleType, titles: dict[str, str]
) -> None:
    for syllabus in _load(generator):
        for level in syllabus.levels:
            page = generator.render_level(syllabus, level, titles)
            topics = [t for t in syllabus.topics if t.level == level.level]
            assert [
                line[3:] for line in page.splitlines() if line.startswith("## ")
            ] == [t.title for t in topics]
            for topic in topics:
                section = page.split(f"## {topic.title}\n", 1)[1].split("\n## ", 1)[0]
                assert topic.url in section
                mapped = [
                    model_id
                    for model_id in syllabus.models
                    if topic in syllabus.topics_of(model_id)
                ]
                rows = re.findall(r"^\| .+ \| \{doc\}`([^ ]+) ", section, re.MULTILINE)
                assert rows == sorted(mapped)
                for model_id in mapped:
                    path = model_id.replace(".", "/")
                    assert f"</reference/models/{path}>" in section
                    domain, name = model_id.replace("_", "-").split(".")
                    url = f"https://pyeconomics.dev/models/{domain}/{name}/"
                    assert f"[Calculator]({url})" in section
                if not mapped:
                    assert "https://pyeconomics.dev/coverage/" in section


def test_a_level_names_the_mark_as_an_adjective_with_the_notice(
    generator: ModuleType, titles: dict[str, str]
) -> None:
    for syllabus in _load(generator):
        for level in syllabus.levels:
            page = generator.render_level(syllabus, level, titles)
            assert page.startswith(f"# 2027 CFA® Program: {level.title}\n")
            assert "CFA Program" not in page
            assert re.search(r"\bCFA\b(?!®| Institute)", page) is None
            assert generator.NOTICES["CFA Institute"] in page
            assert "not affiliated with" in page


def test_the_notice_is_the_one_the_notices_page_and_the_site_carry(
    generator: ModuleType,
) -> None:
    text = generator.NOTICES["CFA Institute"]
    assert text in (ROOT / "docs" / "notices.md").read_text("utf-8")
    links = (ROOT / "web" / "src" / "lib" / "links.ts").read_text("utf-8")
    joined = "".join(re.findall(r'^  "(.*?)"[ +;]*$', links, re.MULTILINE))
    assert text in joined


def test_no_page_holds_curriculum_wording(
    generator: ModuleType, titles: dict[str, str], tmp_path: Path
) -> None:
    syllabi = _load(generator)
    for path in generator.write_pages(tmp_path, syllabi, titles):
        text = path.read_text("utf-8")
        for syllabus in syllabi:
            text = text.replace(syllabus.url, "")
        assert CURRICULUM.search(re.sub(r"\(https?://[^)]+\)", "", text)) is None, path


def test_no_page_path_carries_a_mark(
    generator: ModuleType, titles: dict[str, str], tmp_path: Path
) -> None:
    for path in generator.write_pages(tmp_path, _load(generator), titles):
        assert "cfa" not in path.relative_to(tmp_path).as_posix().lower()


def test_another_issuer_gets_a_plain_notice(generator: ModuleType) -> None:
    other = types.SimpleNamespace(issuer="Another Body")
    assert generator.notice(other) == "pyeconomics is not affiliated with Another Body."


def test_a_rebuild_removes_only_stale_markdown(
    generator: ModuleType, titles: dict[str, str], tmp_path: Path
) -> None:
    (tmp_path / "old").mkdir()
    (tmp_path / "old" / "level-9.md").write_bytes(b"# Old\n")
    (tmp_path / "keep.txt").write_bytes(b"untouched")
    generator.write_pages(tmp_path, _load(generator), titles)
    assert not (tmp_path / "old" / "level-9.md").exists()
    assert (tmp_path / "keep.txt").read_bytes() == b"untouched"


def test_an_id_that_is_not_a_slug_cannot_write(
    generator: ModuleType, tmp_path: Path
) -> None:
    other = types.SimpleNamespace(id="../escape", levels=(), topics=(), models={})
    with pytest.raises(ValueError, match="neutral slug"):
        generator.write_pages(tmp_path / "root", (other,), {})
    assert not (tmp_path / "root").exists()


def test_setup_hook(generator: ModuleType, tmp_path: Path) -> None:
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
    assert (tmp_path / "study-paths" / "index.md").is_file()
    assert (tmp_path / "study-paths" / "analyst-program-2027" / "level-1.md").is_file()
