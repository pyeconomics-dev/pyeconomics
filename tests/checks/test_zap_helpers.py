# tests/checks/test_zap_helpers.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for scripts/zap/ (ZAP header rules, High check) and .zap/rules.tsv."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

REPO = Path(__file__).resolve().parents[2]
RULES = REPO / ".zap" / "rules.tsv"
# Placeholders, not credentials: the shapes of a service token's two values.
ID = "client-id.access"
SECRET = "placeholder" + "\\" + "value"


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name, REPO / "scripts" / "zap" / f"{name}.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


access_props = load("access_props")
no_high = load("no_high")


def test_two_header_rules_scoped_to_the_scanned_host() -> None:
    text = access_props.rules(
        "pyeconomics.dev",
        {"CF_ACCESS_CLIENT_ID": ID, "CF_ACCESS_CLIENT_SECRET": SECRET},
    )
    lines = dict(line.split("=", 1) for line in text.splitlines())
    assert lines["replacer.full_list(0).matchstr"] == "CF-Access-Client-Id"
    assert lines["replacer.full_list(1).matchstr"] == "CF-Access-Client-Secret"
    assert lines["replacer.full_list(0).replacement"] == ID
    assert (
        lines["replacer.full_list(1).replacement"] == "placeholder" + "\\" * 2 + "value"
    )
    assert lines["replacer.full_list(0).matchtype"] == "REQ_HEADER"
    # Java properties read "\\." as "\.": the regex matches the host's dots literally.
    assert lines["replacer.full_list(0).url"] == "https://pyeconomics\\\\.dev/.*"
    assert re.fullmatch(
        lines["replacer.full_list(0).url"].replace("\\\\", "\\"),
        "https://pyeconomics.dev/models/",
    )
    assert not re.fullmatch(
        lines["replacer.full_list(0).url"].replace("\\\\", "\\"),
        "https://gateway.umami.is/api/send",
    )


def test_no_rules_without_the_token_and_refusals() -> None:
    assert access_props.rules("pyeconomics.dev", {}) == ""
    with pytest.raises(SystemExit, match="both"):
        access_props.rules("pyeconomics.dev", {"CF_ACCESS_CLIENT_ID": ID})
    with pytest.raises(SystemExit, match="host name"):
        access_props.rules("https://pyeconomics.dev/", {})
    with pytest.raises(SystemExit, match="line break"):
        access_props.rules(
            "pyeconomics.dev",
            {"CF_ACCESS_CLIENT_ID": "a\nb", "CF_ACCESS_CLIENT_SECRET": SECRET},
        )


def test_main_writes_the_file_and_prints_no_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SCAN_HOST", "staging.pyeconomics.dev")
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", ID)
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", SECRET)
    out = tmp_path / "access.props"
    assert access_props.main(["access_props.py", str(out)]) == 0
    assert b"staging\\\\.pyeconomics\\\\.dev" in out.read_bytes()
    printed = capsys.readouterr()
    assert ID not in printed.out + printed.err
    assert "placeholder" not in printed.out + printed.err
    assert access_props.main(["access_props.py"]) == 2


def report(*risks: str) -> dict[str, object]:
    alerts = [
        {
            "pluginid": str(10000 + n),
            "riskcode": risk,
            "riskdesc": f"risk {risk}",
            "count": "1",
        }
        for n, risk in enumerate(risks)
    ]
    return {"site": [{"@name": "https://pyeconomics.dev", "alerts": alerts}]}


@pytest.mark.parametrize(
    ("risks", "status"), [((), 0), (("0", "1", "2"), 0), (("2", "3"), 1)]
)
def test_a_high_alert_fails(
    tmp_path: Path, risks: tuple[str, ...], status: int
) -> None:
    path = tmp_path / "report_json.json"
    path.write_text(json.dumps(report(*risks)), encoding="utf-8")
    assert no_high.main(["no_high.py", str(path)]) == status


def test_a_missing_report_fails(tmp_path: Path) -> None:
    assert no_high.main(["no_high.py", str(tmp_path / "absent.json")]) == 1
    assert no_high.main(["no_high.py"]) == 2


def test_the_rules_file_parses_as_zap_reads_it() -> None:
    """Each line as zap_common.load_config reads it, with a reason on every IGNORE."""
    levels = {"IGNORE", "INFO", "WARN", "FAIL", "OUTOFSCOPE"}
    seen: set[str] = set()
    for line in RULES.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        rule, level, rest = line.split("\t", 2)
        assert rule.isdigit()
        assert rule not in seen
        seen.add(rule)
        assert level in levels
        if level == "OUTOFSCOPE":
            re.compile(rest)
        else:
            name, reason = rest.split("\t")
            assert name.startswith("(")
            assert name.endswith(")")
            assert len(reason) > 20
    assert seen
