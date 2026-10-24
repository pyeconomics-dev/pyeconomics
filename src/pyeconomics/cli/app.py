# src/pyeconomics/cli/app.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The command tree, the launcher and the exit codes of ``pyeconomics``.

:func:`build` assembles the Cyclopts application: ``models``, ``data``,
``keys``, ``cache``, ``registry``, ``bundle`` and ``completion``, with ``--version``,
``--debug`` and ``--help`` everywhere. :func:`launch` runs one command line and
returns its exit code (ADR-0012 decision 5):

- 0 when the command succeeded, and 2 for a command line that does not parse
  (an unknown command or option, a missing argument);
- every other failure is turned into its problem by
  :func:`~pyeconomics.surfaces.problems.report`, the only logging of a failure;
  the problem's ``cli_message`` (its slug and scrubbed detail) goes to standard
  error and its exit code is returned. ``--debug`` adds a traceback that passes
  through the same redaction, with each file named only by its place in its
  package.

A model's run options are generated when ``models run ID`` is parsed, so
``pyeconomics --help`` never discovers the registry.
"""

import logging
import sys
import traceback
import warnings
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Final, Literal

from cyclopts import App, CycloptsError, Group, Parameter
from rich.text import Text

from pyeconomics import __version__
from pyeconomics.cli import (
    cache_commands,
    data_commands,
    exporting,
    key_commands,
    model_commands,
)
from pyeconomics.cli.context import Context, ContextParameter, UsageError
from pyeconomics.cli.output import Streams, Utf8Text, plain_console
from pyeconomics.surfaces.problems import report, scrub

__all__ = ["USAGE_EXIT_CODE", "build", "launch"]

#: The exit code of a command line that does not parse.
USAGE_EXIT_CODE: Final = 2

_LOGGER_NAME: Final = "pyeconomics"
#: The flags every command takes, wherever they stand before ``--``.
_GLOBAL_FLAGS: Final = frozenset({"--debug", "--help", "-h", "--version"})
_PACKAGE_ROOT: Final = Path(__file__).resolve().parents[1]

Shell = Literal["bash", "zsh", "fish", "powershell"]


def _usage_message(error: CycloptsError) -> Text:
    return Text(f"usage-error: {error}")


def _console(terminal: object, binary: object) -> object:
    from rich.console import Console  # noqa: PLC0415 - imported with the app

    if terminal is not None:
        return Console(file=terminal, highlight=False)  # type: ignore[arg-type] # ty: ignore[invalid-argument-type] - a text stream
    return plain_console(Utf8Text(binary))  # type: ignore[arg-type] # ty: ignore[invalid-argument-type] - a binary stream


def completion(shell: Shell, /, *, context: ContextParameter) -> None:
    """Print the completion script for a shell.

    Load it in the shell's startup file, or let ``pyeconomics
    --install-completion`` write it where the shell looks.

    Parameters
    ----------
    shell
        The shell: bash, zsh, fish or powershell.
    """
    if context.app is None:  # pragma: no cover - the launcher always sets it
        msg = "the completion script needs the application"
        raise UsageError(msg)
    # Cyclopts' shell= names the script's shell; it starts no process.
    script = context.app.generate_completion(prog_name="pyeconomics", shell=shell)  # nosec B604
    context.streams.write(script.encode("utf-8"))


def build(context: Context) -> App:
    """Assemble the application for one run, writing through its streams."""
    streams = context.streams
    app = App(
        name="pyeconomics",
        help=(
            "Open economics and finance models and data from the command line. "
            "Every model runs through the same path as the Python API, and "
            "--format json prints its canonical result."
        ),
        version=f"pyeconomics {__version__}",
        console=_console(streams.terminal, streams.stdout),  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]
        error_console=_console(streams.error_terminal, streams.stderr),  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]
        error_formatter=_usage_message,
    )
    app.meta.group_parameters = Group("Global options", sort_key=10)

    models = App(
        name="models", help="List, search, describe and run the registered models."
    )
    models.command(model_commands.list_models, name="list")
    models.command(model_commands.search_models, name="search")
    models.command(model_commands.describe_model, name="describe")
    models.command(model_commands.run_app())
    app.command(models)

    data = App(
        name="data",
        help="Search, get and describe data from the catalog and its providers.",
    )
    data.command(data_commands.search_data, name="search")
    data.command(data_commands.get_data, name="get")
    data.command(data_commands.describe_data, name="describe")
    data.command(data_commands.list_vintages, name="vintages")
    data.command(data_commands.list_sources, name="sources")
    app.command(data)

    keys = App(name="keys", help="Store, list and delete providers' keys.")
    keys.command(key_commands.set_key, name="set")
    keys.command(key_commands.list_keys, name="list")
    keys.command(key_commands.delete_key, name="delete")
    app.command(keys)

    cache = App(name="cache", help="Inspect and clear the local data cache.")
    cache.command(cache_commands.list_entries, name="ls")
    cache.command(cache_commands.cache_info, name="info")
    cache.command(cache_commands.clear_cache, name="clear")
    cache.command(cache_commands.cache_path, name="path")
    app.command(cache)

    registry = App(name="registry", help="Export the model registry.")
    registry.command(model_commands.export_registry, name="export")
    app.command(registry)

    bundle = App(name="bundle", help="Verify reproducibility bundles.")
    bundle.command(exporting.check_bundle, name="check")
    app.command(bundle)

    app.command(completion, name="completion")
    app.register_install_completion_command(
        help="Install the shell's completion script."
    )

    @app.meta.default
    def launcher(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        debug: Annotated[bool, Parameter(negative="")] = False,
    ) -> object:
        """Run one command.

        Parameters
        ----------
        debug
            On a failure, also print a scrubbed traceback, and log at DEBUG.
        """
        context.debug = context.debug or debug
        command, bound, ignored = app.parse_args(
            tokens, exit_on_error=False, print_error=True
        )
        extra = {"context": context} if "context" in ignored else {}
        return command(*bound.args, **bound.kwargs, **extra)

    context.app = app
    return app


def _flags(tokens: Sequence[str]) -> list[str]:
    """Return the tokens before ``--`` with the global flags left out."""
    before = list(tokens[: tokens.index("--")] if "--" in tokens else tokens)
    return [token for token in before if token not in _GLOBAL_FLAGS]


def _debug_requested(tokens: Sequence[str]) -> bool:
    before = tokens[: tokens.index("--")] if "--" in tokens else tokens
    return "--debug" in before


def _display_name(filename: str) -> str:
    """Name a traceback's file by its place in its package, never its full path."""
    path = Path(filename)
    try:
        return path.resolve().relative_to(_PACKAGE_ROOT.parent).as_posix()
    except (OSError, ValueError):
        pass
    parts = path.parts
    lowered = [part.lower() for part in parts]
    for marker in ("site-packages", "dist-packages", "lib"):
        if marker in lowered:
            index = len(lowered) - 1 - lowered[::-1].index(marker)
            return "/".join(parts[index + 1 :]) or path.name
    return path.name


def _rename_frames(trace: traceback.TracebackException) -> None:
    seen: set[int] = set()
    pending = [trace]
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        for frame in current.stack:
            frame.filename = _display_name(frame.filename)
        pending.extend(
            item
            for item in (current.__cause__, current.__context__)
            if item is not None
        )
        pending.extend(getattr(current, "exceptions", None) or ())


def debug_traceback(error: BaseException) -> list[str]:
    """Return an error's traceback as lines that hold no key, path, host or URL.

    Each file is named by its place in its package; each line then passes
    through :func:`~pyeconomics.surfaces.problems.scrub`, keeping its
    indentation.
    """
    trace = traceback.TracebackException.from_exception(error)
    _rename_frames(trace)
    lines: list[str] = []
    for chunk in trace.format():
        for line in chunk.rstrip("\n").splitlines():
            stripped = line.lstrip()
            indent = line[: len(line) - len(stripped)]
            lines.append(f"{indent}{scrub(stripped)}" if stripped else "")
    return lines


@contextmanager
def _logging(context: Context) -> Generator[None]:
    """Route pyeconomics' log records for the run: to stderr with ``--debug``.

    Without it the records go nowhere, so the one record a failure logs does not
    repeat the message the command line prints.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    handler: logging.Handler
    if context.debug:
        handler = logging.StreamHandler(Utf8Text(context.streams.stderr))
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    else:
        handler = logging.NullHandler()
    level = logger.level
    logger.addHandler(handler)
    if context.debug:
        logger.setLevel(logging.DEBUG)
    try:
        yield
    finally:
        logger.removeHandler(handler)
        logger.setLevel(level)


@contextmanager
def _warnings(streams: Streams) -> Generator[None]:
    """Show each warning as one scrubbed line on standard error, not its source."""

    def show(  # noqa: PLR0913, PLR0917 - warnings.showwarning's signature
        message: Warning | str,
        category: type[Warning],
        filename: str,
        lineno: int,
        file: object = None,
        line: str | None = None,
    ) -> None:
        del filename, lineno, file, line
        streams.error(f"{category.__name__}: {scrub(str(message))}")

    with warnings.catch_warnings():
        warnings.showwarning = show  # ty: ignore[invalid-assignment]
        yield


def _fail(context: Context, error: Exception) -> int:
    problem = report(error)
    context.streams.error(problem.cli_message)
    if context.debug:
        for line in debug_traceback(error):
            context.streams.error(line)
    return problem.exit_code


def launch(argv: Sequence[str] | None = None, *, streams: Streams | None = None) -> int:
    """Run one command line and return its exit code.

    Parameters
    ----------
    argv
        The arguments, without the program's name; ``sys.argv[1:]`` by default.
    streams
        Where to read and write; the process's own streams by default.
    """
    tokens = list(sys.argv[1:] if argv is None else argv)
    context = Context(
        streams=streams or Streams.system(), debug=_debug_requested(tokens)
    )
    with _logging(context), _warnings(context.streams):
        try:
            app = build(context)
            model_commands.prepare_run(app, _flags(tokens))
            app.meta(
                tokens,
                exit_on_error=False,
                print_error=True,
                result_action="return_value",
            )
        except CycloptsError:
            return USAGE_EXIT_CODE
        except UsageError as error:
            context.streams.error(f"usage-error: {error}")
            return USAGE_EXIT_CODE
        except Exception as error:  # noqa: BLE001 - every failure becomes a problem
            return _fail(context, error)
    return 0
