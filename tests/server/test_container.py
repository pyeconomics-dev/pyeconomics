# tests/server/test_container.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Tests for Dockerfile, .dockerignore and ``pyeconomics.server.__main__``."""

from __future__ import annotations

import fnmatch
import io
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn

from pyeconomics.core.errors import InputError, PyeconomicsError
from pyeconomics.data.errors import ConfigError
from pyeconomics.server import __main__ as server_main
from pyeconomics.server.settings import ServerSettings
from pyeconomics.surfaces.problems import row_for

if TYPE_CHECKING:
    from fastapi import FastAPI

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "Dockerfile"
DOCKERIGNORE = ROOT / ".dockerignore"
GITIGNORE = ROOT / ".gitignore"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _parse_ignore_lines(path: Path) -> list[str]:
    """Return non-empty, non-comment patterns from an ignore file."""
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _matches_dockerignore_rule(rel_posix: str, rule: str) -> bool:
    """Evaluate a single ``.dockerignore`` pattern against a POSIX relative path."""
    cleaned = rule.lstrip("/").rstrip("/")
    if not cleaned:
        return False
    candidates = [rel_posix]
    parts = rel_posix.split("/")
    candidates.extend("/".join(parts[:idx]) for idx in range(1, len(parts)))
    for candidate in candidates:
        if fnmatch.fnmatchcase(candidate, cleaned):
            return True
        if cleaned.startswith("**/") and fnmatch.fnmatchcase(
            candidate, cleaned.removeprefix("**/")
        ):
            return True
        if "/" not in cleaned and fnmatch.fnmatchcase(
            candidate.rsplit("/", 1)[-1], cleaned
        ):
            if rule.startswith("**/"):
                return True
            if "/" not in candidate:
                return True
    return False


def _is_excluded_by_dockerignore(rel_posix: str, rules: list[str]) -> bool:
    """Return whether ``rel_posix`` is excluded by ``.dockerignore`` rules in order."""
    excluded = False
    for rule in rules:
        if rule.startswith("!"):
            if _matches_dockerignore_rule(rel_posix, rule[1:]):
                excluded = False
        elif _matches_dockerignore_rule(rel_posix, rule):
            excluded = True
    return excluded


def test_dockerignore_header_and_covers_gitignore() -> None:
    lines = DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# .dockerignore"
    docker_rules = set(_parse_ignore_lines(DOCKERIGNORE))
    git_rules = _parse_ignore_lines(GITIGNORE)
    missing = [rule for rule in git_rules if rule not in docker_rules]
    assert missing == []


@pytest.mark.parametrize(
    "forbidden_path",
    [
        ".git",
        ".git/config",
        ".git/HEAD",
        ".env",
        ".env.local",
        ".env.production",
        "src/pyeconomics/.env",
        "src/pyeconomics/.env.secret",
        "dev/scratch.py",
        ".roadmodel/context.json",
        ".roadmodel/memory/MEMORY.md",
        ".roadmodel/HANDOFF.md",
        ".roadmodel/WORKTREE.md",
        "CLAUDE.local.md",
        "AGENTS.override.md",
        ".agents/shared-context.md",
        ".claude/settings.local.json",
        ".venv/pyvenv.cfg",
        "venv/pyvenv.cfg",
        "cache/cache.sqlite3",
        ".ruff_cache/CACHEDIR.TAG",
        ".mypy_cache/CACHEDIR.TAG",
        ".pytest_cache/CACHEDIR.TAG",
        ".hypothesis/examples",
        "planning/user-context.md",
        "planning/prompts/roadmap-step.md",
        "secrets.py",
        "private.pem",
        "service.key",
        "tests/conftest.py",
        "docs/conf.py",
        "scripts/verify-phase01.sh",
        "tools/node/package.json",
    ],
)
def test_dockerignore_excludes_sensitive_and_non_runtime_paths(
    forbidden_path: str,
) -> None:
    rules = _parse_ignore_lines(DOCKERIGNORE)
    assert _is_excluded_by_dockerignore(forbidden_path, rules), forbidden_path


def test_docker_build_context_listing_excludes_secrets_and_keeps_package() -> None:
    rules = _parse_ignore_lines(DOCKERIGNORE)
    for must_exclude_dir in (
        ".git",
        ".venv",
        "venv",
        ".roadmodel",
        "dev",
        "planning",
        "tests",
        "docs",
        "scripts",
        "tools",
    ):
        assert _is_excluded_by_dockerignore(must_exclude_dir, rules)

    included: list[str] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = Path(dirpath).relative_to(ROOT).as_posix()
        prefix = "" if rel_dir == "." else f"{rel_dir}/"
        dirnames[:] = sorted(
            d
            for d in dirnames
            if not _is_excluded_by_dockerignore(f"{prefix}{d}", rules)
            or f"{prefix}{d}" in {"src", "src/pyeconomics", "src/pyeconomics/data"}
        )
        for filename in sorted(filenames):
            rel = f"{prefix}{filename}"
            if not _is_excluded_by_dockerignore(rel, rules):
                included.append(rel)

    assert "pyproject.toml" in included
    assert "uv.lock" in included
    assert "README.md" in included
    assert "LICENSE" in included
    assert "NOTICE" in included
    assert "src/pyeconomics/__init__.py" in included
    assert "src/pyeconomics/server/__main__.py" in included
    assert "src/pyeconomics/data/cache/__init__.py" in included

    forbidden_prefixes = (
        ".git/",
        ".env",
        "dev/",
        ".roadmodel/",
        ".agents/",
        ".claude/",
        ".venv/",
        "cache/",
        "planning/",
        "tests/",
        "docs/",
        "scripts/",
        "tools/",
    )
    leaked = [
        rel
        for rel in included
        if rel in {".git", ".env", "CLAUDE.local.md", "AGENTS.override.md"}
        or rel.startswith(forbidden_prefixes)
        or "/__pycache__/" in f"/{rel}"
        or rel.endswith((".pyc", ".pyo", ".pyd", ".pem", ".key"))
    ]
    assert leaked == []


def test_dockerfile_invariants() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == "# Dockerfile"

    from_lines = [
        line.strip() for line in lines if line.strip().upper().startswith("FROM ")
    ]
    assert len(from_lines) >= 2
    for from_line in from_lines:
        assert re.search(r"@sha256:[0-9a-f]{64}\b", from_line), from_line

    ci_text = CI_WORKFLOW.read_text(encoding="utf-8")
    uv_match = re.search(
        r'uses:\s*astral-sh/setup-uv@[^\n]+\n\s+with:\n\s+version:\s*"([^"]+)"',
        ci_text,
    )
    assert uv_match is not None
    assert f"ghcr.io/astral-sh/uv:{uv_match.group(1)}@sha256:" in text

    for required in (
        "python:3.14-slim",
        "uv export",
        "--no-config",
        "--frozen",
        "--no-dev",
        "--extra server",
        "--extra mcp",
        "--extra econometrics",
        "--extra plot",
        "--extra sdmx",
        "--no-emit-project",
        "--require-hashes",
        "--no-deps",
        "PYECONOMICS_MODE=hosted",
        "PYECONOMICS_CACHE_DIR=/tmp/",
        "PYTHONDONTWRITEBYTECODE=1",
        "PYTHONUNBUFFERED=1",
        "ARG GIT_SHA=",
        "PYECONOMICS_GIT_SHA=${GIT_SHA}",
        "useradd",
        "/usr/sbin/nologin",
        "USER pyeconomics:pyeconomics",
        'CMD ["python", "-m", "pyeconomics.server"]',
    ):
        assert required in text, required

    run_blocks = "\n".join(line for line in lines if not line.lstrip().startswith("#"))
    for forbidden in ("yfinance", "keyring", "blpapi"):
        assert forbidden not in run_blocks


def test_resolve_mode_and_port_defaults_and_validates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYECONOMICS_MODE", raising=False)
    monkeypatch.delenv("PORT", raising=False)

    assert server_main.resolve_mode() == "local"
    assert server_main.resolve_mode(environ={"PYECONOMICS_MODE": "  "}) == "local"
    assert server_main.resolve_mode(environ={"PYECONOMICS_MODE": "hosted"}) == "hosted"
    assert server_main.resolve_mode("hosted") == "hosted"

    with pytest.raises(ConfigError, match="PYECONOMICS_MODE"):
        server_main.resolve_mode(environ={"PYECONOMICS_MODE": "bogus"})
    bad_mode: Any = "bogus"
    with pytest.raises(ConfigError, match="mode"):
        server_main.resolve_mode(bad_mode)

    assert server_main.resolve_port() == 8080
    assert server_main.resolve_port(environ={"PORT": "   "}) == 8080
    assert server_main.resolve_port(environ={"PORT": "9090"}) == 9090
    assert server_main.resolve_port(8001, environ={"PORT": "9090"}) == 8001

    for bad_env in ("abc", "0", "-1", "65536", "8080.5"):
        with pytest.raises(ConfigError, match=r"PORT|port"):
            server_main.resolve_port(environ={"PORT": bad_env})

    for bad_arg in (0, -5, 70_000, True):
        with pytest.raises(ConfigError, match="port"):
            server_main.resolve_port(bad_arg)


def test_resolve_host_binds_all_interfaces_only_in_hosted_mode() -> None:
    assert server_main.resolve_host(mode="hosted") == server_main.HOSTED_HOST
    assert server_main.resolve_host(mode="local") == server_main.LOCAL_HOST
    assert server_main.resolve_host("localhost", mode="local") == "localhost"
    assert server_main.resolve_host("::1", mode="local") == "::1"
    assert server_main.resolve_host("127.0.0.1", mode="hosted") == "127.0.0.1"
    assert (
        server_main.resolve_host(
            server_main.HOSTED_HOST,
            mode="local",
            allow_remote=True,
        )
        == server_main.HOSTED_HOST
    )

    with pytest.raises(ConfigError, match="loopback"):
        server_main.resolve_host(server_main.HOSTED_HOST, mode="local")


def test_run_uvicorn_disables_proxy_headers_and_handles_signals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict[str, Any]] = []

    class FakeServer:
        def __init__(self, config: uvicorn.Config) -> None:
            captured.append(
                {
                    "app": config.app,
                    "host": config.host,
                    "port": config.port,
                    "access_log": config.access_log,
                    "log_config": config.log_config,
                    "proxy_headers": config.proxy_headers,
                    "server_header": config.server_header,
                }
            )

        def run(self) -> None:
            return None

    monkeypatch.setattr(uvicorn, "Server", FakeServer)
    sentinel_app: Any = object()
    server_main.run_uvicorn(sentinel_app, host="127.0.0.1", port=8080)
    assert captured == [
        {
            "app": sentinel_app,
            "host": "127.0.0.1",
            "port": 8080,
            "access_log": False,
            "log_config": None,
            "proxy_headers": False,
            "server_header": False,
        }
    ]

    class InterruptServer(FakeServer):
        def run(self) -> None:
            raise KeyboardInterrupt

    monkeypatch.setattr(uvicorn, "Server", InterruptServer)
    server_main.run_uvicorn(sentinel_app, host="127.0.0.1", port=8080)

    class FailingServer(FakeServer):
        def run(self) -> None:
            raise SystemExit(1)

    monkeypatch.setattr(uvicorn, "Server", FailingServer)
    with pytest.raises(PyeconomicsError, match="could not start"):
        server_main.run_uvicorn(sentinel_app, host="127.0.0.1", port=8080)


def test_main_hosted_and_local_modes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[dict[str, Any]] = []

    def fake_run_uvicorn(app: FastAPI, *, host: str, port: int) -> None:
        recorded.append({"app": app, "host": host, "port": port})

    monkeypatch.setattr(server_main, "run_uvicorn", fake_run_uvicorn)

    stream = io.StringIO()
    code = server_main.main(
        mode="hosted",
        environ={"PORT": "8181"},
        settings=ServerSettings(workers=2),
        stream=stream,
    )
    assert code == 0
    assert len(recorded) == 1
    assert recorded[0]["host"] == server_main.HOSTED_HOST
    assert recorded[0]["port"] == 8181
    assert "mode=hosted host=0.0.0.0 port=8181 workers=2" in stream.getvalue()

    recorded.clear()
    local_stream = io.StringIO()
    code_local = server_main.main(
        mode="local",
        environ={},
        workers=1,
        stream=local_stream,
    )
    assert code_local == 0
    assert len(recorded) == 1
    assert recorded[0]["host"] == "127.0.0.1"
    assert recorded[0]["port"] == 8080


def test_main_reports_configuration_errors_cleanly() -> None:
    stream = io.StringIO()
    exit_code = server_main.main(
        mode="local",
        host=server_main.HOSTED_HOST,
        stream=stream,
    )
    expected = row_for(ConfigError("bad")).exit_code
    assert exit_code == expected
    assert "invalid-configuration" in stream.getvalue()

    with pytest.raises(InputError, match="workers"):
        server_main.run(mode="local", workers=-1, stream=io.StringIO())
