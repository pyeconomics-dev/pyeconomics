# scripts/web/syllabi.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Load the syllabus crosswalks in ``syllabi/`` (ADR-0013 decision 12).

``syllabi/`` holds a JSON Schema (``schema.json``) and one TOML file per
syllabus version: its levels, one entry per level and topic area (a neutral id,
the displayed title, the level and a link to the issuing body's page), and per
model id the topic ids the model implements. The crosswalk is repository data,
never package structure (ROADMAP section 4 7.1), so the wheel does not carry it:
this one loader feeds both the site data export (``export_site_data.py``) and
the documentation's model pages (``docs/_ext/model_pages.py``).

:func:`load` validates every file against the schema and then checks what a
schema cannot: the file is named for its id; levels and topic ids are unique;
each topic names a declared level; every link starts with the issuing body's
site; every model id is a registered model's canonical id; and every topic a
model names exists. Whatever the schema says, no string that is not a link may
be longer than a topic name (:data:`MAX_TEXT`), so no learning-outcome wording,
reading title or exam content can be stored, and no id may carry the CFA mark
(ROADMAP section 5 "CFA Institute marks and content"). Any problem raises
:class:`SyllabusError`, which lists them all.
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator, Mapping, Sequence

ROOT: Final = Path(__file__).resolve().parents[2]
SYLLABI: Final = ROOT / "syllabi"
SCHEMA: Final = SYLLABI / "schema.json"

#: The longest text a syllabus file may hold outside a link: a topic name.
MAX_TEXT: Final = 40

_MARK: Final = re.compile("cfa", re.IGNORECASE)


class SyllabusError(ValueError):
    """A syllabus file breaks the format; ``problems`` lists every reason."""

    def __init__(self, problems: Sequence[str]) -> None:
        """Hold the problems and say how many there are."""
        self.problems = tuple(problems)
        super().__init__(
            f"{len(self.problems)} problem(s) in syllabi/:\n"
            + "\n".join(f"  {problem}" for problem in self.problems)
        )


@dataclass(frozen=True)
class Level:
    """One level of a syllabus."""

    level: int
    title: str
    url: str


@dataclass(frozen=True)
class Topic:
    """One topic area of one level."""

    id: str
    level: int
    title: str
    url: str


@dataclass(frozen=True)
class Syllabus:
    """One syllabus version and the models each of its topics covers."""

    id: str
    title: str
    issuer: str
    site: str
    url: str
    checked: str
    levels: tuple[Level, ...]
    topics: tuple[Topic, ...]
    models: Mapping[str, tuple[str, ...]]

    def level(self, number: int) -> Level:
        """Return the level numbered ``number``."""
        return next(level for level in self.levels if level.level == number)

    def topics_of(self, model_id: str) -> tuple[Topic, ...]:
        """Return the topics ``model_id`` implements, in the file's topic order."""
        named = set(self.models.get(model_id, ()))
        return tuple(topic for topic in self.topics if topic.id in named)

    def to_json(self) -> dict[str, Any]:
        """Describe the syllabus as the site data export writes it."""
        return {
            "id": self.id,
            "title": self.title,
            "issuer": self.issuer,
            "site": self.site,
            "url": self.url,
            "checked": self.checked,
            "levels": [vars(level) for level in self.levels],
            "topics": [vars(topic) for topic in self.topics],
            "models": {key: list(value) for key, value in sorted(self.models.items())},
        }


def _strings(value: object, path: str = "") -> Iterator[tuple[str, str]]:
    """Yield every string in a parsed document, keys included, with where it is."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield f"{path}/{key}", str(key)
            yield from _strings(item, f"{path}/{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _strings(item, f"{path}/{index}")


def _schema_problems(document: Mapping[str, Any]) -> list[str]:
    from jsonschema import Draft202012Validator  # noqa: PLC0415

    validator = Draft202012Validator(json.loads(SCHEMA.read_bytes()))
    return [
        f"{'/'.join(str(part) for part in error.absolute_path) or '(root)'}: "
        f"{error.message}"
        for error in sorted(validator.iter_errors(document), key=str)
    ]


def _text_problems(document: Mapping[str, Any]) -> list[str]:
    """Return every string that is not a link but is longer than a topic name."""
    return [
        f"{where or '(root)'}: {len(text)} characters, longer than a topic name "
        f"({MAX_TEXT}): syllabi/ stores names, never curriculum wording"
        for where, text in _strings(document)
        if not text.startswith("https://") and len(text) > MAX_TEXT
    ]


def _structure_problems(document: Mapping[str, Any], name: str) -> list[str]:
    """Check the file's name and its ids, levels, topics and links."""
    problems: list[str] = []
    if document["id"] != name:
        problems.append(f"id {document['id']!r} is not the file's name {name!r}")
    ids = [document["id"], *(topic["id"] for topic in document["topics"])]
    problems += [
        f"id {i!r} carries a mark; ids stay neutral" for i in ids if _MARK.search(i)
    ]
    numbers = [level["level"] for level in document["levels"]]
    if len(set(numbers)) != len(numbers):
        problems.append("a level is declared twice")
    seen: set[str] = set()
    for topic in document["topics"]:
        if topic["id"] in seen:
            problems.append(f"topic {topic['id']!r} is declared twice")
        seen.add(topic["id"])
        if topic["level"] not in numbers:
            problems.append(
                f"topic {topic['id']!r} names level {topic['level']}, not declared"
            )
    site = document["site"]
    problems += [
        f"{where}: {text} is not on the issuing body's site {site}"
        for where, text in _strings(document)
        if text.startswith("https://") and not text.startswith(site)
    ]
    return problems


def _model_problems(document: Mapping[str, Any], known: Collection[str]) -> list[str]:
    """Check each model id is registered and each topic it names declared."""
    topics = {topic["id"] for topic in document["topics"]}
    problems: list[str] = []
    for model_id, named in document["models"].items():
        if model_id not in known:
            problems.append(f"{model_id} is not a registered model's canonical id")
        problems += [
            f"{model_id} names topic {t!r}, not declared"
            for t in named
            if t not in topics
        ]
    return problems


def check(
    document: Mapping[str, Any], *, name: str, model_ids: Collection[str]
) -> list[str]:
    """Return every problem with one parsed syllabus file named ``name``."""
    problems = _schema_problems(document) + _text_problems(document)
    if problems:
        return problems
    return _structure_problems(document, name) + _model_problems(
        document, set(model_ids)
    )


def _registered() -> tuple[str, ...]:
    from pyeconomics import registry  # noqa: PLC0415

    return registry.ids()


def load(
    directory: Path = SYLLABI, *, model_ids: Collection[str] | None = None
) -> tuple[Syllabus, ...]:
    """Load and check every syllabus file in ``directory``, sorted by id.

    Raises
    ------
    SyllabusError
        If any file breaks the format, listing every problem of every file.
    """
    known = _registered() if model_ids is None else model_ids
    problems: list[str] = []
    found: list[Syllabus] = []
    for path in sorted(directory.glob("*.toml")):
        try:
            document = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            problems.append(f"{path.name}: not TOML: {error}")
            continue
        file_problems = check(document, name=path.stem, model_ids=known)
        problems += [f"{path.name}: {problem}" for problem in file_problems]
        if file_problems:
            continue
        found.append(
            Syllabus(
                id=document["id"],
                title=document["title"],
                issuer=document["issuer"],
                site=document["site"],
                url=document["url"],
                checked=document["checked"],
                levels=tuple(Level(**level) for level in document["levels"]),
                topics=tuple(Topic(**topic) for topic in document["topics"]),
                models={key: tuple(value) for key, value in document["models"].items()},
            )
        )
    if problems:
        raise SyllabusError(problems)
    return tuple(found)
