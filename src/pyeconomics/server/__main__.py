# src/pyeconomics/server/__main__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Entry point for ``python -m pyeconomics.server`` (ADR-0012 decision 19).

Reads ``PORT`` (default ``8080``), ``PYECONOMICS_MODE`` (``hosted`` in the
container, ``local`` by default) and ``PYECONOMICS_WORKERS``
(:func:`~pyeconomics.server.settings.worker_count`), binds ``0.0.0.0`` only when
the mode is ``hosted`` (local mode keeps ``serve``'s loopback guard unless
``allow_remote`` is set), configures single-line scrubbed logs on standard
error, and runs :mod:`uvicorn` programmatically without trusting forwarded
headers (the client address comes from :mod:`pyeconomics.server.edge`).
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core._optional import import_optional
from pyeconomics.core.errors import PyeconomicsError
from pyeconomics.data.errors import ConfigError
from pyeconomics.server import logs
from pyeconomics.server.app import create_app
from pyeconomics.server.settings import (
    MODES,
    ServerMode,
    ServerSettings,
    worker_count,
)
from pyeconomics.surfaces.problems import report
from pyeconomics.surfaces.service import is_loopback

if TYPE_CHECKING:
    from collections.abc import Mapping

    from _typeshed import SupportsWrite

__all__ = [
    "DEFAULT_PORT",
    "HOSTED_HOST",
    "LOCAL_HOST",
    "MODE_VARIABLE",
    "PORT_VARIABLE",
    "main",
    "resolve_host",
    "resolve_mode",
    "resolve_port",
    "run",
    "run_uvicorn",
]

#: Cloud Run's default container port (ADR-0012 decision 19).
DEFAULT_PORT: Final = 8080
#: Loopback address bound in local mode.
LOCAL_HOST: Final = "127.0.0.1"
#: All-interfaces address bound only in hosted mode inside the container.
HOSTED_HOST: Final = "0.0.0.0"  # noqa: S104 # nosec B104: hosted mode only; local mode enforces loopback
#: Environment variable that sets the TCP port.
PORT_VARIABLE: Final = "PORT"
#: Environment variable that selects ``local`` or ``hosted`` mode.
MODE_VARIABLE: Final = "PYECONOMICS_MODE"
_HIGHEST_PORT: Final = 65_535
_LOGGER: Final = logging.getLogger(logs.LOGGER)


def resolve_mode(
    mode: ServerMode | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> ServerMode:
    """Return the server mode from ``mode`` or ``PYECONOMICS_MODE``."""
    if mode is not None:
        if mode not in MODES:
            msg = f"mode is one of {', '.join(MODES)}, not {mode!r}"
            raise ConfigError(msg)
        return mode
    env = os.environ if environ is None else environ
    raw = env.get(MODE_VARIABLE, "").strip()
    if not raw:
        return "local"
    if raw not in MODES:
        msg = f"{MODE_VARIABLE} is one of {', '.join(MODES)}, not {raw!r}"
        raise ConfigError(msg)
    return raw


def resolve_port(
    port: int | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    """Return the validated TCP port from ``port`` or ``PORT`` (default 8080)."""
    if port is None:
        env = os.environ if environ is None else environ
        raw = env.get(PORT_VARIABLE, "").strip()
        if not raw:
            return DEFAULT_PORT
        if not raw.isdigit():
            msg = f"{PORT_VARIABLE} is an integer from 1 to {_HIGHEST_PORT}"
            raise ConfigError(msg)
        parsed = int(raw, 10)
    else:
        if isinstance(port, bool):
            msg = f"port is an integer from 1 to {_HIGHEST_PORT}"
            raise ConfigError(msg)
        parsed = port
    if not 0 < parsed <= _HIGHEST_PORT:
        msg = f"port is from 1 to {_HIGHEST_PORT}, not {parsed}"
        raise ConfigError(msg)
    return parsed


def resolve_host(
    host: str | None = None,
    *,
    mode: ServerMode,
    allow_remote: bool = False,
) -> str:
    """Return the bind address for ``mode``, enforcing loopback in local mode."""
    target = (HOSTED_HOST if mode == "hosted" else LOCAL_HOST) if host is None else host
    if mode == "local" and not allow_remote and not is_loopback(target):
        msg = (
            f"{target} is not a loopback address; local mode binds only to a "
            "loopback interface (127.0.0.1, ::1 or localhost)"
        )
        raise ConfigError(msg)
    return target


def run_uvicorn(app: Any, *, host: str, port: int) -> None:  # noqa: ANN401 - ASGI app
    """Run ``app`` under Uvicorn with proxy headers and access logging disabled."""
    import_optional("uvicorn", extra="server")
    import uvicorn  # noqa: PLC0415 - optional dependency in the server extra

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
        pass
    except SystemExit as stop:
        stopped = stop.code
    if stopped not in {None, 0}:
        msg = "the server could not start; the line above says why"
        raise PyeconomicsError(msg)


def run(  # noqa: PLR0913 - keyword configuration entry point
    *,
    mode: ServerMode | None = None,
    host: str | None = None,
    port: int | None = None,
    workers: int | None = None,
    settings: ServerSettings | None = None,
    environ: Mapping[str, str] | None = None,
    stream: SupportsWrite[str] | None = None,
) -> None:
    """Build the FastAPI application and run Uvicorn."""
    import_optional("fastapi", extra="server")
    import_optional("uvicorn", extra="server")
    handler = logs.configure(stream or sys.stderr)
    uvicorn_logger = logging.getLogger("uvicorn")
    previous_level = uvicorn_logger.level
    uvicorn_logger.addHandler(handler)
    uvicorn_logger.setLevel(logging.INFO)
    uvicorn_logger.propagate = False
    try:
        resolved_mode = resolve_mode(mode, environ=environ)
        base_settings = settings or ServerSettings()
        effective_settings = (
            base_settings
            if workers is None
            else replace(base_settings, workers=workers)
        )
        resolved_workers = worker_count(effective_settings)
        effective_settings = replace(effective_settings, workers=resolved_workers)
        resolved_host = resolve_host(
            host,
            mode=resolved_mode,
            allow_remote=effective_settings.allow_remote,
        )
        resolved_port = resolve_port(port, environ=environ)
        app = create_app(mode=resolved_mode, settings=effective_settings)
        _LOGGER.info(
            "starting server mode=%s host=%s port=%d workers=%d",
            resolved_mode,
            resolved_host,
            resolved_port,
            resolved_workers,
        )
        run_uvicorn(app, host=resolved_host, port=resolved_port)
    finally:
        uvicorn_logger.removeHandler(handler)
        uvicorn_logger.setLevel(previous_level)
        uvicorn_logger.propagate = True
        logs.release(handler)


def main(  # noqa: PLR0913 - module entry point with testable overrides
    *,
    mode: ServerMode | None = None,
    host: str | None = None,
    port: int | None = None,
    workers: int | None = None,
    settings: ServerSettings | None = None,
    environ: Mapping[str, str] | None = None,
    stream: SupportsWrite[str] | None = None,
) -> int:
    """Run ``python -m pyeconomics.server`` and return an exit code."""
    target_stream = stream or sys.stderr
    try:
        run(
            mode=mode,
            host=host,
            port=port,
            workers=workers,
            settings=settings,
            environ=environ,
            stream=target_stream,
        )
    except Exception as error:  # noqa: BLE001 - surface boundary converts to problem
        handler = logs.configure(target_stream)
        try:
            problem = report(error, logger=_LOGGER)
        finally:
            logs.release(handler)
        return problem.exit_code
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
