# src/pyeconomics/cli/serve_command.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``pyeconomics serve``: the local REST API (ADR-0012 decision 11).

It serves :func:`pyeconomics.server.create_app` in local mode with uvicorn, on
127.0.0.1 port 8000 by default, until Ctrl+C. Local mode reads every source the
user can access, with the user's keys, so:

- a host that is not a loopback address is refused (exit code 2) unless
  ``--allow-remote`` is passed, and then the server logs a warning that every
  such source is exposed to whoever can reach it;
- bound to a loopback address, the server answers only requests addressed to a
  loopback name, so a web page cannot rebind its own name to 127.0.0.1 and read
  them.

The command needs the ``server`` extra (exit code 8 without it). It never starts
hosted mode: the container runs uvicorn itself (Phase 4 Step 12). The server
logs pyeconomics' and uvicorn's records to standard error as single lines, never
a traceback, and no request line (:mod:`pyeconomics.server.logs`).
"""

import logging
from typing import Annotated, Any, Final

from cyclopts import Parameter

from pyeconomics.cli.context import ContextParameter, UsageError
from pyeconomics.cli.output import Utf8Text
from pyeconomics.core._optional import import_optional
from pyeconomics.core.errors import PyeconomicsError
from pyeconomics.surfaces.service import is_loopback

__all__ = ["DEFAULT_HOST", "DEFAULT_PORT", "run_server", "serve"]

#: The address ``serve`` listens on by default.
DEFAULT_HOST: Final = "127.0.0.1"
#: The port ``serve`` listens on by default.
DEFAULT_PORT: Final = 8000
_HIGHEST_PORT: Final = 65_535


def run_server(app: Any, host: str, port: int) -> None:  # noqa: ANN401 - an ASGI app
    """Run uvicorn until it stops, trusting no forwarded header.

    Raises
    ------
    PyeconomicsError
        If uvicorn could not start (the line it logged says why, such as a port
        already in use).
    """
    import uvicorn  # noqa: PLC0415 - the server extra

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_config=None,
        access_log=False,
        proxy_headers=False,
        server_header=False,
    )
    stopped: int | str | None = None
    try:
        uvicorn.Server(config).run()
    except KeyboardInterrupt:
        pass  # uvicorn shut down gracefully, then raised Ctrl+C's signal again
    except SystemExit as stop:
        stopped = stop.code
    if stopped not in {None, 0}:
        msg = "the server could not start; the line above says why"
        raise PyeconomicsError(msg)


def serve(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    workers: int | None = None,
    allow_remote: Annotated[bool, Parameter(negative="")] = False,
    context: ContextParameter,
) -> None:
    """Serve the REST API on this machine, until Ctrl+C.

    Its routes are under /v1; the interactive documentation is at /docs.

    Parameters
    ----------
    host
        The address to listen on: a loopback address unless --allow-remote.
    port
        The port to listen on.
    workers
        The worker processes that run models; PYECONOMICS_WORKERS, else the
        number of CPUs, by default.
    allow_remote
        Listen on an address other machines can reach. Every source this
        machine can access, with its keys, is then served to them.
    """
    if not 0 < port <= _HIGHEST_PORT:
        msg = f"--port is from 1 to {_HIGHEST_PORT}"
        raise UsageError(msg)
    if workers is not None and workers < 0:
        msg = "--workers is a whole number from 0"
        raise UsageError(msg)
    local = is_loopback(host)
    if not local and not allow_remote:
        msg = (
            f"{host} is not a loopback address, so other machines could reach "
            "every source this one can access; pass --allow-remote to serve it"
        )
        raise UsageError(msg)
    import_optional("fastapi", extra="server")
    import_optional("uvicorn", extra="server")
    from pyeconomics.server import ServerSettings, create_app, logs  # noqa: PLC0415

    handler = logs.configure(Utf8Text(context.streams.stderr))
    server_logger = logging.getLogger("uvicorn")
    level = server_logger.level
    server_logger.addHandler(handler)
    server_logger.setLevel(logging.INFO)
    server_logger.propagate = False
    try:
        if not local:
            logging.getLogger(logs.LOGGER).warning(
                "serving on %s, which is not a loopback address: every source "
                "this machine can access, with its keys, is exposed to whoever "
                "can reach it",
                host,
            )
        settings = ServerSettings(workers=workers, allow_remote=not local)
        run_server(create_app(mode="local", settings=settings), host, port)
    finally:
        server_logger.removeHandler(handler)
        server_logger.setLevel(level)
        server_logger.propagate = True
        logs.release(handler)
