# tests/mcp/test_mcp_registry_entry.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The MCP Registry entry: server.json and the README's marker (ADR-0012 16).

``server.json`` at the repository root is what ``mcp-publisher publish``
(.github/workflows/mcp-registry.yml) sends to the registry. It validates against
``tests/mcp/registry/server.schema.json``, a vendored copy of
https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json
read on 2026-10-26 (SHA-256 below), and it names the PyPI package at the project
version, run with ``uvx --from "pyeconomics[mcp]==<version>" pyeconomics mcp``.
The registry verifies the package by the ``mcp-name:`` marker in its PyPI
description, which is README.md.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any, Final

import jsonschema

from pyeconomics.mcp.server import SERVER_NAME

ROOT: Final = Path(__file__).resolve().parents[2]
SCHEMA: Final = Path(__file__).with_name("registry") / "server.schema.json"
SCHEMA_URL: Final = (
    "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json"
)
SCHEMA_SHA256: Final = (
    "3fba09590c99f61735d234822279f4223fab9e300c0a81e81c91ab62a4114de0"
)
NAME: Final = "io.github.pyeconomics-dev/pyeconomics"


def _entry() -> dict[str, Any]:
    entry: dict[str, Any] = json.loads((ROOT / "server.json").read_bytes())
    return entry


def _project_version() -> str:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version: str = project["project"]["version"]
    return version


def test_the_vendored_schema_is_the_one_read() -> None:
    assert hashlib.sha256(SCHEMA.read_bytes()).hexdigest() == SCHEMA_SHA256
    schema = json.loads(SCHEMA.read_bytes())
    assert schema["$id"] == SCHEMA_URL


def test_server_json_validates_against_the_schema() -> None:
    schema = json.loads(SCHEMA.read_bytes())
    validator = jsonschema.Draft7Validator(
        schema, format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER
    )
    errors = sorted(validator.iter_errors(_entry()), key=lambda e: list(e.path))
    assert not errors, [f"{list(e.path)}: {e.message}" for e in errors]


def test_server_json_names_the_server_and_the_package_at_the_project_version() -> None:
    entry = _entry()
    version = _project_version()
    assert entry["$schema"] == SCHEMA_URL
    assert entry["name"] == NAME
    assert entry["name"].rsplit("/", 1)[1] == SERVER_NAME
    assert entry["version"] == version
    (package,) = entry["packages"]
    assert package["registryType"] == "pypi"
    assert package["identifier"] == "pyeconomics"
    assert package["version"] == version
    assert package["transport"] == {"type": "stdio"}
    assert package["runtimeHint"] == "uvx"
    runtime = [(a["name"], a["value"]) for a in package["runtimeArguments"]]
    assert runtime == [("--from", f"pyeconomics[mcp]=={version}")]
    assert [a["value"] for a in package["packageArguments"]] == ["mcp"]


def test_the_readme_carries_the_mcp_name_marker_on_its_own_line() -> None:
    lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    marker = f"<!-- mcp-name: {NAME} -->"
    assert marker in lines
    found = re.findall(r"mcp-name:\s*(\S+)", "\n".join(lines))
    assert found == [NAME]
