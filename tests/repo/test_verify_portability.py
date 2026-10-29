# tests/repo/test_verify_portability.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The phase verifiers fail closed wherever they run.

Every ``scripts/verify-phaseNN.sh`` refuses a bash older than 4 instead of
stopping at its first check and exiting 0, and keeps a crash's status through
its ``EXIT`` trap (issue #217). Phase 1's check 16 reads ``gh``'s CRLF output
on Windows (issue #213). The scripts run under a real bash on every operating
system of the CI matrix: Git Bash on Windows.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess  # nosec B404: runs bash and git, fixed executables, with fixed arguments
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = sorted(path.name for path in (REPO / "scripts").glob("verify-phase*.sh"))
GUARD_MESSAGE = "verify needs bash >= 4 (brew install bash)"
TRAP = "trap 'rc=$?; rm -rf \"$TMP\"; exit $rc' EXIT"


def _run(
    argv: list[str], *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # nosec B603: fixed executables, no shell
        argv,
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )


@pytest.fixture(scope="module")
def bash() -> str:
    """Git Bash on Windows (System32's bash.exe launches WSL), else PATH's bash."""
    if os.name == "nt":
        git = shutil.which("git")
        if git is None:
            pytest.skip("git is not on PATH")
        # <Git>/mingw64/libexec/git-core -> <Git>/bin/bash.exe
        exec_path = _run([git, "--exec-path"]).stdout.strip()
        candidate = Path(exec_path).parents[2] / "bin" / "bash.exe"
        if not candidate.is_file():
            pytest.skip("Git Bash is not installed")
        return str(candidate)
    found = shutil.which("bash")
    if found is None:
        pytest.skip("bash is not on PATH")
    return found


def _major(bash: str) -> int:
    return int(_run([bash, "-c", 'echo "${BASH_VERSINFO[0]}"']).stdout.strip())


@pytest.fixture(scope="module")
def modern_bash(bash: str) -> str:
    """A bash the verifiers accept: on macOS PATH's bash may be /bin/bash 3.2."""
    for candidate in (bash, "/opt/homebrew/bin/bash", "/usr/local/bin/bash"):
        if Path(candidate).is_file() and _major(candidate) >= 4:
            return candidate
    pytest.skip("no bash 4 or later is installed")


def test_every_phase_has_a_verifier() -> None:
    expected = [f"verify-phase{n:02d}.sh" for n in range(1, len(SCRIPTS) + 1)]
    assert expected == SCRIPTS
    assert len(SCRIPTS) >= 4


@pytest.mark.parametrize("script", SCRIPTS)
def test_an_old_bash_is_refused(script: str, bash: str, tmp_path: Path) -> None:
    # BASH_VERSINFO is read-only in a real bash, so the stand-in runs the
    # script's own text with it renamed to a plain array that reports 3.2.
    text = (REPO / "scripts" / script).read_bytes().decode("utf-8")
    assert text.count("BASH_VERSINFO") == 1
    stand_in = tmp_path / script
    stand_in.write_bytes(
        b"FAKE_VERSINFO=(3 2 57 1 release x86_64-apple-darwin)\n"
        + text.replace("BASH_VERSINFO", "FAKE_VERSINFO").encode("utf-8")
    )
    result = _run([bash, stand_in.as_posix(), "--fast"])
    assert result.returncode == 2
    assert GUARD_MESSAGE in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("script", SCRIPTS)
def test_macos_system_bash_is_refused(script: str) -> None:
    system_bash = Path("/bin/bash")
    if platform.system() != "Darwin" or not system_bash.is_file():
        pytest.skip("macOS's /bin/bash only")
    if _major(str(system_bash)) >= 4:
        pytest.skip("this /bin/bash is 4 or later")
    result = _run([str(system_bash), f"scripts/{script}", "--fast"])
    assert result.returncode == 2
    assert GUARD_MESSAGE in result.stderr


@pytest.mark.parametrize("script", SCRIPTS)
def test_the_exit_trap_keeps_the_status(script: str) -> None:
    lines = (REPO / "scripts" / script).read_bytes().decode("utf-8").splitlines()
    traps = [line for line in lines if line.startswith("trap ")]
    assert traps == [TRAP]


@pytest.mark.parametrize("script", SCRIPTS)
def test_a_crash_is_never_a_pass(script: str, modern_bash: str, tmp_path: Path) -> None:
    # bash reads BASH_ENV before the script. Its declare() shadows the
    # builtin, so the first declaration after the EXIT trap dies on an
    # unbound variable under set -u, mid-run.
    crash = tmp_path / "crash.sh"
    crash.write_bytes(b'declare() { : "${VERIFY_PORTABILITY_UNSET}"; }\n')
    scratch = tmp_path / "tmp"
    scratch.mkdir()
    env = {**os.environ, "BASH_ENV": crash.as_posix(), "TMPDIR": scratch.as_posix()}
    env.pop("VERIFY_PORTABILITY_UNSET", None)
    result = _run([modern_bash, f"scripts/{script}", "--fast"], env=env)
    assert "VERIFY_PORTABILITY_UNSET: unbound variable" in result.stderr
    assert result.returncode != 0
    # The trap still ran: the script's temporary directory is gone.
    assert list(scratch.iterdir()) == []


def _function(text: str, name: str) -> str:
    match = re.search(
        rf"^{re.escape(name)}\(\) \{{.*?^\}}$", text, re.MULTILINE | re.DOTALL
    )
    assert match is not None, name
    return match.group(0)


@pytest.mark.parametrize(
    ("remote", "returncode", "output"),
    [
        (["main", "legacy/0.2.x", "feature/open-pr"], 0, ""),
        (["main", "feature/open-pr", "feature/stale"], 1, "feature/stale"),
    ],
)
def test_check_16_reads_crlf_from_gh(
    remote: list[str], returncode: int, output: str, bash: str, tmp_path: Path
) -> None:
    # Phase 1's check 16 with git and gh stood in: gh answers one open pull
    # request's branch with a Windows line ending. Git for Windows' bash drops
    # the carriage return in $(...) by itself; bash on Linux and macOS keeps
    # it, so there the first case fails without the fix.
    text = (REPO / "scripts" / "verify-phase01.sh").read_bytes().decode("utf-8")
    heads = " ".join(f"0123 {branch}" for branch in remote)
    harness = "\n".join(
        [
            "set -uo pipefail",
            "REPO=pyeconomics-dev/pyeconomics",
            "git() {",
            '  case "$1" in',
            f"    ls-remote) printf '%s\\trefs/heads/%s\\n' {heads} ;;",
            "  esac",
            "}",
            "gh() { printf 'feature/open-pr\\r\\n'; }",
            _function(text, "fail"),
            _function(text, "open_pr_heads"),
            _function(text, "c16"),
            "(c16)",
            "",
        ]
    )
    script = tmp_path / "check16.sh"
    script.write_bytes(harness.encode("utf-8"))
    result = _run([bash, script.as_posix()])
    assert result.returncode == returncode, result.stdout + result.stderr
    if output:
        assert result.stdout.strip() == f"unexpected branches: {output}"
    else:
        assert result.stdout == ""
