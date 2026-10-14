# tests/repo/test_phase02.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Phase 2's verification deliverables exist in the repository.

The pytest twin of ``scripts/verify-phase02.sh``'s Step 15 self-checks
(static checks 62-65), so the CI test matrix catches a missing deliverable on
every operating system.
"""

from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404: runs git, a fixed executable, with fixed arguments
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = "scripts/verify-phase02.sh"


def test_roadmap_doc_exists() -> None:
    assert (REPO / "docs" / "roadmap" / "phase02-roadmap.md").is_file()


def test_qa_findings_doc_exists() -> None:
    assert (REPO / "docs" / "phase02-qa-findings.md").is_file()


def test_verify_script_exists_and_executable() -> None:
    assert (REPO / SCRIPT).is_file()
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not on PATH")
    # Windows has no executable bit, so the git index mode is the proof.
    staged = subprocess.run(  # noqa: S603  # nosec B603: git, fixed arguments, no shell
        [git, "ls-files", "--stage", "--", SCRIPT],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert staged.split(" ", 1)[0] == "100755"


def test_phase_verify_matrix_includes_02() -> None:
    workflow = (REPO / ".github" / "workflows" / "phase-verify.yml").read_text(
        encoding="utf-8"
    )
    matrices = re.findall(r"^\s+phase:\s*\[(.*)\]\s*$", workflow, re.MULTILINE)
    assert matrices
    assert all('"02"' in matrix for matrix in matrices)
