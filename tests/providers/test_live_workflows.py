# tests/providers/test_live_workflows.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The live provider workflows keep their shape (ADR-0011 decision 18).

``providers-live.yml`` and ``providers-heartbeat.yml`` run only on a schedule
and on dispatch, never on a pull request; they hold nothing at the top level
(``permissions: {}``); the live job's egress allowlist names every registered
provider's hosts whose terms allow automated collection; and the provider keys
reach the pytest step alone. The files are read as text, so the test needs no
YAML parser: a top-level key starts its line, and the allowlist is the block
under ``allowed-endpoints``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import pytest

from pyeconomics.data import registry

WORKFLOWS: Final = Path(__file__).resolve().parents[2] / ".github" / "workflows"
LIVE: Final = WORKFLOWS / "providers-live.yml"
HEARTBEAT: Final = WORKFLOWS / "providers-heartbeat.yml"
KEYS: Final = ("FRED_API_KEY", "BLS_API_KEY", "BEA_API_KEY", "CENSUS_API_KEY")


def top_level(text: str, key: str) -> list[str]:
    """Return the lines of a top-level YAML key's block, without the key."""
    lines = text.splitlines()
    start = lines.index(f"{key}:")
    block = []
    for line in lines[start + 1 :]:
        if line and not line.startswith((" ", "#")):
            break
        block.append(line)
    return block


def triggers(text: str) -> set[str]:
    """Return the events an ``on:`` block names."""
    return {
        match.group(1)
        for line in top_level(text, "on")
        if (match := re.fullmatch(r"  ([a-z_]+):.*", line))
    }


def allowed_endpoints(text: str, job: str) -> set[str]:
    """Return the hosts a job's harden-runner step lets out."""
    lines = top_level(text, "jobs")
    start = lines.index(f"  {job}:")
    found: set[str] = set()
    inside = False
    for line in lines[start + 1 :]:
        if re.fullmatch(r"  [a-z_]+:", line):
            break
        if line.strip() == "allowed-endpoints: >":
            inside = True
            continue
        if inside:
            match = re.fullmatch(r" +([*a-z0-9.-]+):443", line)
            if match is None:
                inside = False
                continue
            found.add(match.group(1))
    return found


@pytest.mark.parametrize("path", [LIVE, HEARTBEAT], ids=lambda path: path.name)
def test_a_live_workflow_runs_only_on_schedule_and_dispatch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert triggers(text) == {"schedule", "workflow_dispatch"}
    assert "pull_request" not in "\n".join(top_level(text, "on"))


@pytest.mark.parametrize("path", [LIVE, HEARTBEAT], ids=lambda path: path.name)
def test_a_live_workflow_grants_nothing_at_the_top_level(path: Path) -> None:
    assert "\npermissions: {}\n" in path.read_text(encoding="utf-8")


def test_every_collectable_providers_hosts_are_in_the_live_egress_allowlist() -> None:
    allowed = allowed_endpoints(LIVE.read_text(encoding="utf-8"), "live")
    providers = [registry.get(provider_id).info for provider_id in registry.ids()]
    wanted = {
        host for info in providers if info.automated_collection for host in info.hosts
    }
    assert wanted, "no registered provider declares a host"
    assert wanted <= allowed, f"not in the allowlist: {sorted(wanted - allowed)}"


def test_the_keys_reach_only_the_pytest_step_of_the_live_job() -> None:
    text = LIVE.read_text(encoding="utf-8")
    for key in KEYS:
        assert text.count(f"secrets.{key}") == 1, key
    step = text[text.index("- name: Run the live suite") :]
    step = step[: step.index("- name:", 1)]
    assert all(f"secrets.{key}" in step for key in KEYS)
    assert "pytest -m live" in step


def test_only_the_report_job_may_write_issues_in_the_live_workflow() -> None:
    jobs = "\n".join(top_level(LIVE.read_text(encoding="utf-8"), "jobs"))
    live = jobs[: jobs.index("  report:")]
    report = jobs[jobs.index("  report:") :]
    assert "issues: write" not in live
    assert "contents: read" in live
    assert "environment: providers-live" in live
    assert "issues: write" in report
    assert "secrets." not in report


def test_the_heartbeat_holds_no_secret_and_reads_only_actions() -> None:
    text = HEARTBEAT.read_text(encoding="utf-8")
    assert "secrets." not in text
    assert "actions: read" in text
    assert "issues: write" in text


def test_the_parsers_read_what_they_should() -> None:
    sample = (
        "name: x\non:\n  schedule:\n    - cron: '1 1 * * 1'\n  pull_request:\n"
        "permissions: {}\njobs:\n  live:\n    steps:\n      - with:\n"
        "          allowed-endpoints: >\n            a.example.org:443\n"
        "            b.example.org:443\n      - run: x\n  other:\n"
        "    steps:\n      - with:\n          allowed-endpoints: >\n"
        "            c.example.org:443\n"
    )
    assert triggers(sample) == {"schedule", "pull_request"}
    assert allowed_endpoints(sample, "live") == {"a.example.org", "b.example.org"}
