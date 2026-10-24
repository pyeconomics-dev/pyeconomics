# tests/cli/test_cli_keys.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``pyeconomics keys`` and the Credential rule (Phase 4 Step 4).

Every test runs with the isolated fixture's in-memory keyring and no real key in
the environment. Keys are random canaries (tests/data/leakcheck.py); a stored key
is compared as a boolean, never asserted in a way pytest could print. The last
tests plant a canary everywhere a careless path could pick it up and search every
sink: standard output and error, log records, warnings, exceptions, problems and
the completion scripts.
"""

from __future__ import annotations

import json
import secrets
import sys
from typing import TYPE_CHECKING

import pytest
from cli_support import cli
from leakcheck import LeakCheck, canary

from pyeconomics.cli import app as cli_app
from pyeconomics.data import KeySource, has_key
from pyeconomics.data.credentials import KEYRING_SERVICE, key_source
from pyeconomics.surfaces import problems

if TYPE_CHECKING:
    import logging

    from config_isolation import Home, Isolation

    from pyeconomics.surfaces.problems import Problem

SHELLS = ("bash", "zsh", "fish", "powershell")


def stored(isolation: Isolation, provider: str, value: str) -> bool:
    """Whether the keyring holds exactly ``value`` for the provider."""
    held = isolation.keyring.passwords.get((KEYRING_SERVICE, provider))
    return held is not None and secrets.compare_digest(held, value)


def test_keys_set_reads_standard_input_and_stores_in_the_keyring(
    isolated: Isolation,
) -> None:
    key = canary("fred")
    outcome = cli("keys", "set", "fred", "--stdin", stdin=f"{key.value}\n".encode())
    assert (outcome.code, outcome.stderr) == (0, "")
    assert (
        outcome.text
        == "Stored the fred key in the OS keyring (service 'pyeconomics').\n"
    )
    assert stored(isolated, "fred", key.value)
    assert has_key("fred")
    assert key_source("fred") is KeySource.KEYRING


def test_keys_set_asks_with_a_hidden_prompt(isolated: Isolation) -> None:
    key = canary("bea")
    prompts: list[str] = []

    def ask(prompt: str) -> str:
        prompts.append(prompt)
        return key.value

    outcome = cli("keys", "set", "bea", interactive=True, ask=ask)
    assert outcome.code == 0
    assert prompts == ["bea key (input hidden): "]
    assert stored(isolated, "bea", key.value)


def test_without_a_terminal_the_key_must_come_from_stdin() -> None:
    outcome = cli("keys", "set", "fred")
    assert outcome.code == 2
    assert outcome.stderr.startswith("usage-error: standard input is not a terminal")


def test_a_key_is_never_an_argument() -> None:
    outcome = cli("keys", "set", "fred", secrets.token_hex(16))
    assert outcome.code == 2
    assert outcome.stderr.startswith("usage-error:")


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"short\n", "a fred key is shorter than 8 characters"),
        (b"", "a fred key is empty"),
        (b"two words here\n", "holds a space"),
        (b"\xff\xfe\xfd\xfc\xfb\xfa\xf9\xf8\n", "not UTF-8 text"),
    ],
    ids=["short", "empty", "space", "bytes"],
)
def test_an_unusable_key_is_invalid_input_and_is_not_stored(
    isolated: Isolation, data: bytes, message: str
) -> None:
    outcome = cli("keys", "set", "fred", "--stdin", stdin=data)
    assert outcome.code == 3
    assert outcome.stderr.startswith("invalid-input: ")
    assert message in outcome.stderr
    assert isolated.keyring.passwords == {}


def test_keys_name_a_provider_that_uses_one() -> None:
    unknown = cli("keys", "set", "freddy", "--stdin", stdin=b"x" * 20)
    assert unknown.code == 5
    assert unknown.stderr.startswith("provider-not-found: ")
    keyless = cli("keys", "delete", "treasury")
    assert keyless.code == 3
    assert keyless.stderr == "invalid-input: treasury takes no key\n"


def test_storing_and_deleting_need_the_keyring_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "keyring", None)
    for outcome in (
        cli("keys", "set", "fred", "--stdin", stdin=secrets.token_hex(16).encode()),
        cli("keys", "delete", "fred"),
    ):
        assert outcome.code == 8
        assert outcome.stderr.startswith("missing-extra: ")
        assert "pyeconomics[keyring]" in outcome.stderr


def test_a_key_in_the_environment_still_takes_precedence(
    isolated: Isolation, monkeypatch: pytest.MonkeyPatch, home: Home
) -> None:
    monkeypatch.setenv("FRED_API_KEY", canary("fred").value)
    outcome = cli("keys", "set", "fred", "--stdin", stdin=canary("fred").value.encode())
    assert outcome.code == 0
    assert outcome.text.endswith(
        "the environment variable FRED_API_KEY still takes precedence.\n"
    )
    monkeypatch.delenv("FRED_API_KEY")
    home.write_dotenv(f"FRED_API_KEY={canary('fred').value}\n")
    again = cli("keys", "set", "fred", "--stdin", stdin=canary("fred").value.encode())
    assert again.text.endswith(
        "FRED_API_KEY in the .env file still takes precedence.\n"
    )
    assert isolated.keyring.passwords


def test_keys_list_names_each_source_and_no_value(
    isolated: Isolation, monkeypatch: pytest.MonkeyPatch, home: Home
) -> None:
    monkeypatch.setenv("FRED_API_KEY", canary("fred").value)
    home.write_dotenv(f"BEA_API_KEY={canary('bea').value}\n")
    isolated.keyring.set_password(KEYRING_SERVICE, "census", canary("census").value)
    outcome = cli("keys", "list", "--format", "json")
    assert outcome.code == 0
    sources = {
        entry["provider"]: entry["source"] for entry in json.loads(outcome.stdout)
    }
    assert {
        "fred": "environment",
        "bea": "dotenv",
        "census": "keyring",
    }.items() <= sources.items()
    assert sources["bls"] == "none"
    entry = next(e for e in json.loads(outcome.stdout) if e["provider"] == "fred")
    assert entry == {
        "provider": "fred",
        "variable": "FRED_API_KEY",
        "required": True,
        "source": "environment",
    }
    table = cli("keys", "list")
    assert any(
        line.split() == ["fred", "FRED_API_KEY", "yes", "environment"]
        for line in table.text.splitlines()
    )


def test_keys_delete_removes_the_keyrings_copy(isolated: Isolation) -> None:
    isolated.keyring.set_password(KEYRING_SERVICE, "fred", canary("fred").value)
    first = cli("keys", "delete", "fred")
    assert (first.code, first.text) == (
        0,
        "Deleted the fred key from the OS keyring.\n",
    )
    assert isolated.keyring.passwords == {}
    second = cli("keys", "delete", "fred")
    assert (second.code, second.text) == (0, "The OS keyring held no fred key.\n")


def test_data_sources_says_whether_a_key_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plain = cli("data", "sources", "--format", "json")
    assert {entry["key_configured"] for entry in json.loads(plain.stdout)} == {None}
    monkeypatch.setenv("FRED_API_KEY", canary("fred").value)
    checked = cli("data", "sources", "--check-keys", "--format", "json")
    configured = {e["id"]: e["key_configured"] for e in json.loads(checked.stdout)}
    assert configured["fred"] is True
    assert configured["bea"] is False
    table = cli("data", "sources", "--check-keys")
    assert any(
        line.split()[:1] == ["fred"]
        and "FRED_API_KEY (required)" in line
        and "yes" in line.split()
        for line in table.text.splitlines()
    )


# --- the canaries -------------------------------------------------------------


def test_no_key_reaches_any_sink(
    isolated: Isolation, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = canary("fred")
    check = LeakCheck(key)
    seen: list[Problem] = []

    def recording_report(
        error: BaseException, *, logger: logging.Logger | None = None
    ) -> Problem:
        check.exception(error)
        problem = problems.report(error, logger=logger)
        seen.append(problem)
        return problem

    def failing_backend(_service: str, _username: str, password: str) -> None:
        msg = f"the backend refused {password}"
        raise RuntimeError(msg)

    monkeypatch.setattr(cli_app, "report", recording_report)
    runs = {}
    with check.logs(), check.warnings():
        runs["set-stdin"] = cli(
            "--debug", "keys", "set", "fred", "--stdin", stdin=f"{key.value}\n".encode()
        )
        runs["set-prompt"] = cli(
            "keys", "set", "fred", interactive=True, ask=lambda _: key.value
        )
        runs["list"] = cli("--debug", "keys", "list")
        runs["list-json"] = cli("keys", "list", "--format", "json")
        runs["sources"] = cli("data", "sources", "--check-keys", "--format", "json")
        runs["invalid"] = cli(
            "--debug",
            "keys",
            "set",
            "fred",
            "--stdin",
            stdin=f"{key.value} tail\n".encode(),
        )
        for shell in SHELLS:
            runs[f"completion-{shell}"] = cli("completion", shell)
        runs["delete"] = cli("--debug", "keys", "delete", "fred")
        monkeypatch.setattr(isolated.keyring, "set_password", failing_backend)
        runs["backend"] = cli(
            "--debug", "keys", "set", "fred", "--stdin", stdin=key.value.encode()
        )
        monkeypatch.setenv("FRED_API_KEY", key.value)
        monkeypatch.setenv("PYECONOMICS_OFFLINE", "1")
        runs["offline-get"] = cli("--debug", "data", "get", "fred:UNRATE")
    for name, outcome in runs.items():
        check.add(f"stdout:{name}", outcome.stdout)
        check.add(f"stderr:{name}", outcome.stderr)
    for problem in seen:
        check.add(f"problem:{problem.slug}", problem.to_json())
    assert runs["set-stdin"].code == 0
    assert runs["invalid"].code == 3
    assert runs["backend"].code == 7
    backend_lines = runs["backend"].stderr.splitlines()
    assert any(line.startswith("credential-unavailable: ") for line in backend_lines)
    assert "(RuntimeError)" in runs["backend"].stderr
    assert runs["offline-get"].code == 7
    assert "Traceback" in runs["offline-get"].stderr
    assert {problem.slug for problem in seen} >= {
        "invalid-input",
        "credential-unavailable",
    }
    assert any(name.startswith("log:") for name in check.sinks)
    check.assert_clean()


def test_the_canary_harness_sees_a_key_on_stdout_or_stderr() -> None:
    key = canary("fred")
    check = LeakCheck(key)
    check.add("stdout:probe", f"value {key.value}\n".encode())
    check.add("stderr:probe", f"value {key.value}")
    assert check.leaks() == ["stderr:probe", "stdout:probe"]
