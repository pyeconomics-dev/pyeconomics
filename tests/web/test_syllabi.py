# tests/web/test_syllabi.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/web/syllabi.py, the one loader of the syllabus crosswalks.

The seed in ``syllabi/`` must load, map every registered model and hold no
mark in an id; the loader must refuse an unknown model id, an unknown topic,
a link off the issuing body's site, a marked id and any text longer than a
topic name, wherever the schema would let it through (ADR-0013 decision 12).
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from pyeconomics import registry

if TYPE_CHECKING:
    from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "web" / "syllabi.py"
SEED = ROOT / "syllabi" / "analyst-program-2027.toml"


@pytest.fixture(scope="module")
def loader() -> ModuleType:
    spec = importlib.util.spec_from_file_location("syllabi_under_test", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["syllabi_under_test"] = module
    spec.loader.exec_module(module)
    return module


def seed() -> dict[str, Any]:
    return tomllib.loads(SEED.read_text(encoding="utf-8"))


def problems(loader: ModuleType, document: dict[str, Any]) -> list[str]:
    result: list[str] = loader.check(
        document, name="analyst-program-2027", model_ids=registry.ids()
    )
    return result


def test_the_seed_loads_and_maps_every_registered_model(loader: ModuleType) -> None:
    (syllabus,) = loader.load()
    assert syllabus.id == "analyst-program-2027"
    assert syllabus.title == "2027 CFA® Program"
    assert sorted(syllabus.models) == sorted(registry.ids())
    assert [level.title for level in syllabus.levels] == [
        "Level I",
        "Level II",
        "Level III",
    ]
    assert len(syllabus.topics) == 28
    assert all(topic.url.startswith(syllabus.site) for topic in syllabus.topics)
    assert [t.id for t in syllabus.topics_of("fixed_income.duration")] == [
        "l1-fixed-income",
        "l2-fixed-income",
    ]
    assert syllabus.level(3).title == "Level III"


def test_the_seed_holds_names_only_and_neutral_ids(loader: ModuleType) -> None:
    document = seed()

    def strings(value: object) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            return [*value, *(s for item in value.values() for s in strings(item))]
        if isinstance(value, list):
            return [s for item in value for s in strings(item)]
        return []

    for text in strings(document):
        assert text.startswith("https://") or len(text) <= loader.MAX_TEXT, text
    for identifier in [document["id"], *(t["id"] for t in document["topics"])]:
        assert "cfa" not in identifier.lower()


def test_the_json_shape_is_what_the_site_reads(loader: ModuleType) -> None:
    (syllabus,) = loader.load()
    document = syllabus.to_json()
    assert set(document) == {
        "id",
        "title",
        "issuer",
        "site",
        "url",
        "checked",
        "levels",
        "topics",
        "models",
    }
    assert document["topics"][0] == {
        "id": "l1-ethics",
        "level": 1,
        "title": "Ethical and Professional Standards",
        "url": syllabus.topics[0].url,
    }
    assert list(document["models"]) == sorted(document["models"])
    json.dumps(document)


def test_an_unknown_model_id_is_refused(loader: ModuleType) -> None:
    document = seed()
    document["models"]["fixed_income.no_such_model"] = ["l1-fixed-income"]
    assert problems(loader, document) == [
        "fixed_income.no_such_model is not a registered model's canonical id"
    ]


def test_an_unknown_topic_is_refused(loader: ModuleType) -> None:
    document = seed()
    document["models"]["fixed_income.duration"] = ["l1-no-such-topic"]
    assert problems(loader, document) == [
        "fixed_income.duration names topic 'l1-no-such-topic', not declared"
    ]


@pytest.mark.parametrize(
    "where",
    ["title", "issuer", "topic title", "level title"],
)
def test_text_longer_than_a_topic_name_is_refused(
    loader: ModuleType, where: str
) -> None:
    document = seed()
    wording = "Describe and evaluate the effect of a change in yield on price"
    if where == "title":
        document["title"] = wording
    elif where == "issuer":
        document["issuer"] = wording
    elif where == "topic title":
        document["topics"][0]["title"] = wording
    else:
        document["levels"][0]["title"] = wording
    found = problems(loader, document)
    assert any("longer than a topic name" in problem for problem in found), found


def test_long_text_is_refused_even_where_the_schema_would_allow_it(
    loader: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(loader, "_schema_problems", lambda _document: [])
    document = seed()
    document["topics"][0]["title"] = "x" * (loader.MAX_TEXT + 1)
    assert problems(loader, document) == [
        (
            f"/topics/0/title: {loader.MAX_TEXT + 1} characters, longer than a "
            f"topic name ({loader.MAX_TEXT}): syllabi/ stores names, never "
            "curriculum wording"
        )
    ]


def test_an_extra_field_is_refused(loader: ModuleType) -> None:
    document = seed()
    document["topics"][0]["outcome"] = "Explain"
    found = problems(loader, document)
    assert any("Additional properties" in problem for problem in found), found


def test_a_marked_id_is_refused(loader: ModuleType) -> None:
    document = seed()
    document["topics"][0]["id"] = "cfa-l1-ethics"
    found = problems(loader, document)
    assert any(problem.startswith("topics/0/id") for problem in found), found


def test_a_link_off_the_issuers_site_is_refused(loader: ModuleType) -> None:
    document = seed()
    document["topics"][1]["url"] = "https://example.org/level-i"
    assert problems(loader, document) == [
        (
            "/topics/1/url: https://example.org/level-i is not on the issuing body's "
            "site https://www.cfainstitute.org/"
        )
    ]


def test_structure_problems_are_each_named(loader: ModuleType) -> None:
    document = seed()
    document["levels"].append(copy.deepcopy(document["levels"][0]))
    document["topics"].append(copy.deepcopy(document["topics"][0]))
    document["topics"][1]["level"] = 9
    assert problems(loader, document) == [
        "a level is declared twice",
        "topic 'l1-quantitative-methods' names level 9, not declared",
        "topic 'l1-ethics' is declared twice",
    ]


def test_load_names_the_file_and_refuses_one_named_for_another_id(
    loader: ModuleType, tmp_path: Path
) -> None:
    (tmp_path / "renamed-2027.toml").write_bytes(SEED.read_bytes())
    (tmp_path / "broken.toml").write_bytes(b"format = [")
    with pytest.raises(loader.SyllabusError) as raised:
        loader.load(tmp_path)
    assert raised.value.problems[0].startswith("broken.toml: not TOML")
    assert raised.value.problems[1] == (
        "renamed-2027.toml: id 'analyst-program-2027' is not the file's name "
        "'renamed-2027'"
    )
    assert "2 problem(s) in syllabi/" in str(raised.value)


def test_load_takes_the_registry_by_default_and_given_ids_otherwise(
    loader: ModuleType,
) -> None:
    with pytest.raises(loader.SyllabusError, match="not a registered model"):
        loader.load(model_ids=["fixed_income.duration"])
    assert loader.load(model_ids=registry.ids())[0].id == "analyst-program-2027"
