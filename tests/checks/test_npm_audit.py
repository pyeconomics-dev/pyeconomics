# tests/checks/test_npm_audit.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for scripts/checks/npm_audit.py, the Node audit and its exceptions.

No test runs npm: each hands the check an answer in `npm audit --json`'s shape.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from types import ModuleType

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "checks" / "npm_audit.py"
GLOB = "GHSA-fc5q-39xc-vjpf"
OTHER = "GHSA-2345-6789-cfgh"
TODAY = dt.date(2026, 11, 20)


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("npm_audit_check", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # A dataclass with slots looks its module up by name while it is built.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


npm_audit = load_script()


def via(identifier: str, package: str, severity: str = "high") -> dict[str, Any]:
    return {
        "source": 1,
        "name": package,
        "title": f"{package} is vulnerable",
        "url": f"https://github.com/advisories/{identifier}",
        "severity": severity,
        "range": "<=4.0.7",
    }


def answer(*advisories: dict[str, Any], dependents: int = 2) -> dict[str, Any]:
    """An `npm audit --json` answer: each advisory, and packages that reach it."""
    packages: dict[str, Any] = {}
    counts = {"info": 0, "low": 0, "moderate": 0, "high": 0, "critical": 0}
    for advisory in advisories:
        packages[advisory["name"]] = {
            "severity": advisory["severity"],
            "via": [advisory],
        }
        counts[advisory["severity"]] += 1
        for number in range(dependents):
            name = f"{advisory['name']}-user-{number}"
            packages[name] = {
                "severity": advisory["severity"],
                "via": [advisory["name"]],
            }
            counts[advisory["severity"]] += 1
    return {"vulnerabilities": packages, "metadata": {"vulnerabilities": counts}}


def entry(**changes: object) -> str:
    values: dict[str, object] = {
        "advisory": f'"{GLOB}"',
        "package": '"picomatch"',
        "projects": '["tools/node", "web"]',
        "added": "2026-11-17",
        "expires": "2026-12-17",
        "issue": "360",
        "reason": '"No patched release; build tools only."',
    }
    values.update(changes)
    lines = [f"{key} = {value}" for key, value in values.items() if value is not None]
    return "[[exception]]\n" + "\n".join(lines) + "\n"


def exceptions(text: str | None = None) -> list[Any]:
    return list(npm_audit.read_exceptions(entry() if text is None else text))


def found(document: dict[str, Any]) -> dict[str, Any]:
    return dict(npm_audit.advisories(document))


def test_an_answer_names_each_advisory_of_high_or_above_once() -> None:
    document = answer(
        via(GLOB, "picomatch"),
        via(OTHER, "other", "critical"),
        via("GHSA-3456-789c-fghj", "mild", "moderate"),
    )
    advisories = found(document)
    assert sorted(advisories) == [OTHER, GLOB]
    assert advisories[GLOB].package == "picomatch"
    assert advisories[OTHER].severity == "critical"


def test_a_clean_answer_names_nothing() -> None:
    assert found(answer()) == {}


@pytest.mark.parametrize(
    "document",
    [{}, {"vulnerabilities": {}}, {"vulnerabilities": [], "metadata": {}}],
)
def test_an_answer_that_cannot_be_read_fails(document: dict[str, Any]) -> None:
    with pytest.raises(npm_audit.AuditError, match="holds no"):
        npm_audit.advisories(document)


def test_findings_with_no_advisory_to_name_fail() -> None:
    document = answer(via(GLOB, "picomatch"))
    document["vulnerabilities"] = {"picomatch-user": {"via": ["picomatch"]}}
    with pytest.raises(npm_audit.AuditError, match="no advisory to name"):
        npm_audit.advisories(document)


def test_the_exceptions_file_in_the_repository_reads() -> None:
    text = npm_audit.EXCEPTIONS.read_text(encoding="utf-8")
    for item in npm_audit.read_exceptions(text):
        assert set(item.projects) <= set(npm_audit.PROJECTS)
        assert len(item.reason) > 80, "a reason says why, and what it reaches"


def test_an_entry_reads_as_written() -> None:
    (item,) = exceptions()
    assert (item.advisory, item.package, item.issue) == (GLOB, "picomatch", 360)
    assert item.projects == ("tools/node", "web")
    assert item.expires == dt.date(2026, 12, 17)


@pytest.mark.parametrize(
    ("changes", "rule"),
    [
        ({"advisory": '"CVE-2026-112366"'}, "advisory"),
        ({"advisory": "7"}, "advisory"),
        ({"package": '""'}, "package"),
        ({"projects": '["docs"]'}, "projects"),
        ({"projects": "[]"}, "projects"),
        ({"projects": '"web"'}, "projects"),
        ({"added": '"2026-11-17"'}, "added"),
        ({"expires": "2026-12-17T00:00:00"}, "expires"),
        ({"issue": "0"}, "issue"),
        ({"issue": "true"}, "issue"),
        ({"reason": '"  "'}, "reason"),
        ({"reason": None}, "the keys are"),
        ({"note": '"extra"'}, "the keys are"),
        ({"expires": "2026-11-17"}, "1 to 45 days"),
        ({"expires": "2027-01-02"}, "1 to 45 days"),
        ({"expires": "2026-11-01"}, "1 to 45 days"),
    ],
)
def test_a_bad_entry_fails(changes: dict[str, object], rule: str) -> None:
    with pytest.raises(npm_audit.AuditError, match=rule):
        exceptions(entry(**changes))


def test_an_exception_runs_45_days_at_most() -> None:
    (item,) = exceptions(entry(expires="2027-01-01"))
    assert (item.expires - item.added).days == npm_audit.MAX_DAYS


def test_an_advisory_named_twice_for_a_project_fails() -> None:
    with pytest.raises(npm_audit.AuditError, match="twice"):
        exceptions(entry() + entry(projects='["web"]'))


def test_a_file_that_does_not_parse_fails() -> None:
    with pytest.raises(npm_audit.AuditError, match="does not parse"):
        exceptions("[[exception]\n")


def test_an_empty_file_excepts_nothing() -> None:
    assert exceptions("# nothing\n") == []


def run(
    full: dict[str, Any],
    production: dict[str, Any] | None = None,
    *,
    project: str = "web",
    listed: list[Any] | None = None,
    today: dt.date = TODAY,
) -> tuple[list[str], list[str]]:
    problems, applied = npm_audit.check(
        project,
        found(full),
        found(answer() if production is None else production),
        exceptions() if listed is None else listed,
        today,
    )
    return list(problems), list(applied)


def test_an_excepted_advisory_in_the_tools_passes_and_is_reported() -> None:
    problems, applied = run(answer(via(GLOB, "picomatch")))
    assert problems == []
    assert applied == [f"{GLOB} (picomatch) until 2026-12-17, issue #360"]


def test_an_advisory_no_exception_names_fails() -> None:
    problems, applied = run(answer(via(GLOB, "picomatch"), via(OTHER, "other")))
    assert len(problems) == 1
    assert OTHER in problems[0]
    assert "No exception names it" in problems[0]
    assert len(applied) == 1


def test_an_exception_never_covers_what_ships() -> None:
    document = answer(via(GLOB, "picomatch"))
    problems, applied = run(document, document)
    assert applied == []
    assert len(problems) == 1
    assert "what ships" in problems[0]


def test_an_exception_fails_the_day_after_it_expires() -> None:
    document = answer(via(GLOB, "picomatch"))
    last_day = dt.date(2026, 12, 17)
    assert run(document, today=last_day)[0] == []
    problems, applied = run(document, today=last_day + dt.timedelta(days=1))
    assert applied == []
    assert len(problems) == 1
    assert "expired on 2026-12-17" in problems[0]
    assert "#360" in problems[0]


def test_an_exception_that_matches_nothing_fails() -> None:
    problems, applied = run(answer())
    assert applied == []
    expected = (
        f"the exception for {GLOB} matches nothing in web: remove it from "
        "scripts/checks/audit_exceptions.toml"
    )
    assert problems == [expected]


def test_an_exception_holds_only_for_the_projects_it_names() -> None:
    listed = exceptions(entry(projects='["tools/node"]'))
    document = answer(via(GLOB, "picomatch"))
    assert run(document, project="tools/node", listed=listed)[0] == []
    problems, _ = run(document, project="web", listed=listed)
    assert len(problems) == 1
    assert "No exception names it" in problems[0]


def test_an_exception_for_another_package_does_not_apply() -> None:
    problems, applied = run(answer(via(GLOB, "micromatch")))
    assert applied == []
    assert len(problems) == 1
    assert "names the package 'picomatch'" in problems[0]


def test_audits_that_disagree_fail() -> None:
    problems, _ = run(answer(), answer(via(OTHER, "other")), listed=[])
    assert len(problems) == 1
    assert "the two audits disagree" in problems[0]


def scripted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    full: dict[str, Any],
    production: dict[str, Any],
) -> list[tuple[str, bool]]:
    """Answer the two audits from documents, with an empty exceptions file."""
    calls: list[tuple[str, bool]] = []
    listed = tmp_path / "audit_exceptions.toml"
    listed.write_bytes(b"# none\n")
    monkeypatch.setattr(npm_audit, "EXCEPTIONS", listed)

    def audit(npm: str, project: str, *, production_only: bool) -> dict[str, Any]:
        assert npm == "npm-on-path"
        calls.append((project, production_only))
        return production if production_only else full

    monkeypatch.setattr(npm_audit.shutil, "which", lambda _name: "npm-on-path")
    monkeypatch.setattr(
        npm_audit,
        "audit",
        lambda npm, project, *, production: audit(
            npm, project, production_only=production
        ),
    )
    return calls


def test_a_run_audits_the_whole_tree_and_what_ships(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = scripted(monkeypatch, tmp_path, answer(), answer())
    assert npm_audit.main(["tools/node"]) == 0
    assert calls == [("tools/node", False), ("tools/node", True)]
    assert "no advisory of High or above" in capsys.readouterr().out


def test_a_run_fails_on_an_advisory_and_names_it(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    scripted(monkeypatch, tmp_path, answer(via(OTHER, "other", "critical")), answer())
    assert npm_audit.main(["web"]) == 1
    error = capsys.readouterr().err
    assert OTHER in error
    assert "critical" in error


def test_a_run_fails_when_the_audit_cannot_be_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    scripted(monkeypatch, tmp_path, {"error": {"code": "ENOAUDIT"}}, answer())
    assert npm_audit.main(["web"]) == 1
    assert "holds no" in capsys.readouterr().err


def test_a_run_without_npm_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(npm_audit.shutil, "which", lambda _name: None)
    assert npm_audit.main(["web"]) == 1
    assert "npm is not on PATH" in capsys.readouterr().err


@pytest.mark.parametrize("arguments", [[], ["docs"], ["web", "tools/node"]])
def test_a_run_takes_one_known_project(
    arguments: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert npm_audit.main(arguments) == 2
    assert "usage" in capsys.readouterr().err


class Completed:
    def __init__(self, stdout: str, returncode: int = 1) -> None:
        self.stdout = stdout
        self.returncode = returncode


def test_the_audit_command_is_fixed_and_reads_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], **options: object) -> Completed:
        commands.append(command)
        assert options["check"] is False
        assert "shell" not in options
        return Completed('{"vulnerabilities": {}, "metadata": {"vulnerabilities": {}}}')

    monkeypatch.setattr(npm_audit.subprocess, "run", fake_run)
    document = npm_audit.audit("npm", "web", production=True)
    assert document["vulnerabilities"] == {}
    npm_audit.audit("npm", "tools/node", production=False)
    assert commands == [
        ["npm", "audit", "--prefix", "web", "--json", "--omit=dev"],
        ["npm", "audit", "--prefix", "tools/node", "--json"],
    ]


@pytest.mark.parametrize(
    ("stdout", "message"),
    [
        ("npm error network", "printed no JSON"),
        ('{"error": {"code": "ENOLOCK"}}', "ENOLOCK"),
        ("[]", "answered an error"),
    ],
)
def test_an_audit_that_did_not_run_fails(
    monkeypatch: pytest.MonkeyPatch, stdout: str, message: str
) -> None:
    monkeypatch.setattr(
        npm_audit.subprocess, "run", lambda *_a, **_k: Completed(stdout)
    )
    with pytest.raises(npm_audit.AuditError, match=message):
        npm_audit.audit("npm", "web", production=False)


def test_the_gate_and_the_verifier_audit_through_the_check() -> None:
    """Neither runs a bare `npm audit`, which knows no exception and no date."""
    hooks = (REPO / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    for project in npm_audit.PROJECTS:
        entry_line = (
            f"entry: uv run --locked python scripts/checks/npm_audit.py {project}"
        )
        assert hooks.count(entry_line) == 1, project
    verifier = (REPO / "scripts" / "verify-phase04.sh").read_text(encoding="utf-8")
    for text in (hooks, verifier):
        assert "npm audit --audit-level" not in text.replace(
            '"npm ci and npm audit --audit-level=high in tools/node"', ""
        )
    assert verifier.count("scripts/checks/npm_audit.py tools/node") == 2
