# docs/conftest.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Run only authored site examples, with pytest's socket isolation.

Each example also runs with isolated settings and keys
(tests/config_isolation.py), so no example reads the reader's real
configuration, environment keys or OS keyring.

The tutorials, the how-to guides and the migration guide (:data:`GUIDES`) are
followed step by step, so a page runs as the one session a reader has
(:func:`guide_page`) and more of it runs. Beside its Python blocks:

- a ``console`` block is a shell session. Each ``$ pyeconomics`` line runs the
  command line in-process and each ``$ curl`` line asks the real app. Every line
  under a command must appear in what it printed (``...`` stands for text left
  out), and ``$ echo $?`` gives its exit code, 0 unless shown;
- a ``shell`` block holds commands that read live data. Each runs offline, where
  it must stop at the data with exit code 7, which proves its command line
  without the network;
- a ``text`` block is an illustration and does not run.

Their data examples read recorded responses (tests/providers/cassettes), and a
socket reaches loopback hosts only, for the event loop of a server or an MCP
client: no example touches the network, and none needs a key.
"""

from __future__ import annotations

import itertools
import re
import shlex
import sys
import types
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest
from cli_support import Outcome, cli
from config_isolation import Isolation, isolated_configuration
from server_support import client
from sybil import Sybil
from sybil.parsers.myst import CodeBlockParser, PythonCodeBlockParser
from sybil.sybil import SybilCollection

from pyeconomics.data import configure, transport
from pyeconomics.data.transport.replay import ReplayTransport

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sybil import Example

# The documentation build runs docs/examples/, and marimo docs/wasm/ in a browser.
collect_ignore = ["conf.py", "_ext", "examples", "wasm"]

_EXAMPLE_NUMBERS = itertools.count()

#: The recordings a page's data examples read: a keyless, hosted-safe source.
_RECORDINGS: Final = Path(__file__).resolve().parents[1] / "tests/providers/cassettes"

#: A session's commands: its ``$`` lines, each with the lines it printed.
_COMMAND: Final = re.compile(r"^\$ (.+)\n((?:(?!\$ ).*\n)*)", re.MULTILINE)
_EXIT_CODE: Final = "echo $?"
#: The exit code of a command stopped at its data (surfaces/problems.py).
_DATA_UNAVAILABLE: Final = 7


def _commands(source: str) -> Iterator[tuple[str, list[str], int]]:
    """Yield a session's commands: the line, what it prints and its exit code."""
    found = _COMMAND.findall(source.replace("\\\n", " "))
    for index, (line, printed) in enumerate(found):
        if line == _EXIT_CODE:
            continue
        following = found[index + 1] if index + 1 < len(found) else ("", "0")
        code = int(following[1]) if following[0] == _EXIT_CODE else 0
        yield line, printed.splitlines(), code


def _curl(arguments: list[str]) -> Outcome:
    """Send what a ``curl`` line asks for to the real app, in this process.

    Like ``curl`` itself it exits 0 on an error status, so what a line printed
    is what proves it.
    """
    method, body, url = "GET", None, ""
    words = iter(arguments)
    for word in words:
        if word == "-X":
            method = next(words)
        elif word == "-d":
            method, body = "POST", next(words)
        else:
            url = word
    with client() as api:
        response = api.request(method, url, content=body)
    return Outcome(0, response.content, "")


def _run(line: str) -> Outcome:
    """Run one command of a session; a page shows no other programs running."""
    program, *arguments = shlex.split(line)
    if program == "pyeconomics":
        return cli(*arguments)
    if program == "curl":
        return _curl(arguments)
    message = f"a session runs pyeconomics or curl, not {program}: use a text block"
    raise ValueError(message)


def _printed(expected: str, output: str) -> bool:
    """Whether a shown line is in the output, ``...`` standing for omitted text."""
    return all(part.strip() in output for part in expected.split("..."))


class ConsoleParser(CodeBlockParser):
    """Run a ``console`` block as the session it shows."""

    language = "console"

    def evaluate(self, example: Example) -> str | None:
        """Run each command; return what differs from the page, if anything."""
        for line, printed, code in _commands(example.parsed):
            outcome = _run(line)
            output = outcome.text + outcome.stderr
            if outcome.code != code:
                return f"`{line}` exited {outcome.code}, not {code}: {output}"
            missing = [text for text in printed if not _printed(text, output)]
            if missing:
                return f"`{line}` did not print {missing}; it printed:\n{output}"
        return None


class ShellParser(CodeBlockParser):
    """Prove a ``shell`` block's live commands offline."""

    language = "shell"

    def evaluate(self, example: Example) -> str | None:
        """Run each command offline, where it must stop at the data."""
        configure(offline=True)
        try:
            for line, _, _ in _commands(example.parsed):
                outcome = _run(line)
                if outcome.code != _DATA_UNAVAILABLE:
                    return f"`{line}` exited {outcome.code}: {outcome.stderr}"
        finally:
            configure(offline=False)
        return None


@pytest.fixture
def isolated(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Isolation]:
    """Isolate one example's settings, keys and keyring."""
    root: Path = tmp_path_factory.getbasetemp() / f"docs-{next(_EXAMPLE_NUMBERS)}"
    with isolated_configuration(monkeypatch, root) as isolation:
        yield isolation


@pytest.fixture(scope="module")
def guide_page(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Isolation]:
    """Give a guide the one session a reader follows it in.

    Its examples share isolated settings, keys and a cache, a working directory
    and the recorded responses, so a later step sees what an earlier one did.
    xlwings, which runs only inside its Excel add-in, gets a stand-in.
    """
    root = tmp_path_factory.mktemp("guide")
    stand_in = types.ModuleType("xlwings")
    vars(stand_in).update(func=lambda f: f, script=lambda f: f, Book=object)
    replay = ReplayTransport.from_directory(_RECORDINGS / "treasury")
    with (
        pytest.MonkeyPatch.context() as patch,
        isolated_configuration(patch, root / "settings") as isolation,
    ):
        patch.chdir(root)
        patch.setitem(sys.modules, "xlwings", stand_in)
        patch.setitem(transport._DEFAULT, "http", replay)  # noqa: SLF001
        yield isolation


# MyST-NB cells execute in Sphinx; generated model pages contain JSON examples.
PAGES: Final = Sybil(
    parsers=[PythonCodeBlockParser()],
    filenames=[
        "index.md",
        "installation.md",
        "quickstart.md",
        "conventions.md",
        "results.md",
        "errata.md",
        "notices.md",
        "changelog.md",
        "bindings.md",
        "keys.md",
        "cache.md",
        "writing-a-provider.md",
        "registry.md",
        "exports.md",
        "api.md",
        "ai.md",
    ],
    excludes=[
        "roadmap/*",
        "adr/*",
        "releases/*",
        "operations/*",
        "reference/*",
        "study-paths/*",
        "tutorials/*",
        "how-to/*",
        "_build/*",
    ],
    fixtures=["isolated"],
    name="pages",
)

GUIDES: Final = Sybil(
    parsers=[PythonCodeBlockParser(), ConsoleParser(), ShellParser()],
    patterns=["tutorials/*.md", "how-to/*.md", "migration.md"],
    fixtures=["guide_page"],
    name="guides",
)

pytest_collect_file = SybilCollection((PAGES, GUIDES)).pytest()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Let a guide's server or MCP client make loopback sockets, and only those.

    asyncio's event loop needs a socket pair, which ``--disable-socket`` refuses.
    """
    for item in items:
        if GUIDES.should_parse(Path(item.path)):
            item.add_marker(pytest.mark.allow_hosts(["127.0.0.1", "::1"]))
