# src/pyeconomics/server/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The REST API (ADR-0012 decisions 9 to 12 and 20), in the ``server`` extra.

``pip install "pyeconomics[server]"`` adds FastAPI and uvicorn, and
``pyeconomics serve`` serves the local API on 127.0.0.1. :func:`create_app`
builds the app for either mode, its routes generated from the registry:

- :mod:`~pyeconomics.server.app`: the factory, the routes, the problems;
- :mod:`~pyeconomics.server.settings`: the modes and :class:`ServerSettings`;
- :mod:`~pyeconomics.server.pool`: the worker pool and its budgets;
- :mod:`~pyeconomics.server.work`: one task, and the messages to a worker;
- :mod:`~pyeconomics.server.formats`: the ``?format=`` downloads;
- :mod:`~pyeconomics.server.openapi`: the OpenAPI 3.1 document;
- :mod:`~pyeconomics.server.logs`: what the server logs;
- :mod:`~pyeconomics.server.edge`: hosted mode's trust in its edge;
- :mod:`~pyeconomics.server.limits`: each client's rate limits;
- :mod:`~pyeconomics.server.run_cache`: the GET run cache and its headers.

The names here are imported on first use, so a worker process, which imports
:mod:`~pyeconomics.server.pool`, loads no web framework.

Examples
--------
>>> from pyeconomics.server import ServerSettings, create_app
>>> create_app(settings=ServerSettings(workers=0)).title
'pyeconomics'
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyeconomics.server.app import create_app
    from pyeconomics.server.settings import ServerSettings

__all__ = ["ServerSettings", "create_app"]


def __getattr__(name: str) -> Any:  # noqa: ANN401 - the exported names
    """Import ``create_app`` and ``ServerSettings`` when first asked for."""
    if name == "create_app":
        from pyeconomics.server.app import create_app  # noqa: PLC0415

        return create_app
    if name == "ServerSettings":
        from pyeconomics.server.settings import ServerSettings  # noqa: PLC0415

        return ServerSettings
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
