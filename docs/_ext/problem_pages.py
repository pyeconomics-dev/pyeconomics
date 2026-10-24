# docs/_ext/problem_pages.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Generate the problem types page from the error table, offline, at build time.

Every surface reports a failure as an RFC 9457 problem whose ``type`` is
``https://pyeconomics.dev/problems/<slug>`` (ADR-0012 decision 4). Until Phase 5
makes those addresses resolve, this page lists each one: its title, HTTP status,
exit code and error class, under a heading whose anchor is the slug. The page
comes from :data:`pyeconomics.surfaces.problems.ROWS`, so it cannot drift from the
table; it is written to ``problems.md`` in the source directory, which git
ignores, and the build blocks the network.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.surfaces.problems import Row

_SLUG = re.compile(r"[a-z][a-z0-9-]{0,63}")
_EXIT_CODES = (
    (0, "success"),
    (1, "internal error"),
    (2, "usage"),
    (3, "invalid input"),
    (4, "no defined result"),
    (5, "not found"),
    (6, "not permitted (a licence refusal)"),
    (7, "data unavailable"),
    (8, "missing extra"),
)


def _class(row: Row) -> str:
    if row.error == "builtins.Exception":
        return "any other exception"
    return f"`{row.error}`"


def render(rows: Sequence[Row]) -> str:
    """Return the Markdown page for the error table."""
    table = "\n".join(
        f"| `{row.slug}` | {row.title} | {row.status} | {row.exit_code} |"
        for row in rows
    )
    codes = "\n".join(f"- `{code}`: {meaning}" for code, meaning in _EXIT_CODES)
    sections = "\n".join(
        f"## {row.slug}\n\n"
        f"**{row.title}.** HTTP {row.status}; exit code {row.exit_code}; "
        f"raised as {_class(row)}.\n\n"
        f"Type: `{row.type_uri}`\n"
        for row in rows
    )
    return (
        "# Problem types\n\n"
        "Every pyeconomics surface reports a failure as a problem in the form of "
        "RFC 9457: a `type`, a `title`, an HTTP `status` and a `detail`, plus the "
        "exit code the command line returns. A problem's `type` is "
        "`https://pyeconomics.dev/problems/<slug>`; until the 1.0 site makes those "
        "addresses resolve, this page lists each one under a heading named after "
        "its slug. A problem never holds a key, a file path, a host or an upstream "
        "URL (ADR-0012 decision 4).\n\n"
        "| Slug | Title | HTTP status | Exit code |\n"
        "|------|-------|-------------|-----------|\n"
        f"{table}\n\n"
        "The command line's exit codes:\n\n"
        f"{codes}\n\n"
        f"{sections}"
    )


def write_page(path: Path, rows: Sequence[Row]) -> Path:
    """Write the page, after checking every slug can name an anchor.

    Raises
    ------
    ValueError
        For an invalid or repeated slug.
    """
    slugs = [row.slug for row in rows]
    if len(set(slugs)) != len(slugs) or not all(_SLUG.fullmatch(s) for s in slugs):
        message = "Invalid or duplicate problem slugs"
        raise ValueError(message)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render(rows).encode("utf-8"))
    return path


def setup(app: Any) -> dict[str, object]:  # noqa: ANN401
    """Install the builder hook; pure functions do not require Sphinx."""
    from sphinx.errors import ExtensionError  # noqa: PLC0415

    from pyeconomics.surfaces.problems import ROWS  # noqa: PLC0415

    def generate(application: Any) -> None:  # noqa: ANN401
        try:
            write_page(Path(application.srcdir) / "problems.md", ROWS)
        except ValueError as error:
            raise ExtensionError(str(error)) from error

    app.connect("builder-inited", generate)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}
